# door_manager_ui.py
# MASTER VERSION: Conflict Alerts + Memory Compression + UniFi-Only Lockdown (Physical Switch + Individual Rules)

import json
import os
from datetime import datetime, timedelta

# GLOBAL MEMORY
if "last_unlock_tracker" not in locals():
    last_unlock_tracker = {}
if "last_nightly_report" not in locals():
    last_nightly_report = {}

@pyscript_compile
def read_config_file(path):
    import yaml
    try:
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        return None

def parse_time(value):
    try:
        if isinstance(value, int): return value
        from datetime import datetime
        value = str(value).upper().strip()
        if "AM" in value or "PM" in value:
            if ":" in value: dt = datetime.strptime(value, "%I:%M %p")
            else: dt = datetime.strptime(value, "%I %p")
            return dt.hour
        return int(value)
    except: return 0 

@service
def check_door_schedule():
    CONFIG_FILE = "/config/pyscript/doors.yaml"

    # 1. READ CONFIG
    data = task.executor(read_config_file, CONFIG_FILE)
    if data is None:
        log.error(f"Door Manager: Could not read {CONFIG_FILE}.")
        return

    # 2. EXTRACT SETTINGS
    settings = data.pop("Settings", {})
    if not settings: settings = data.pop("settings", {})

    PAUSE_ENTITY = settings.get("pause_entity", "input_boolean.pause_door_schedule")
    # This is the 'Watcher' for the global UniFi switch
    LOCKDOWN_SWITCH = settings.get("lockdown_switch", None) 
    MEMORY_ENTITY = settings.get("memory_entity", "input_text.door_manager_memory")
    DEBUG = settings.get("debug_logging", False)
    
    start_raw = settings.get("safe_hour_start", "6 AM")
    end_raw = settings.get("safe_hour_end", "11:59 PM")
    SAFE_HOUR_START = parse_time(start_raw)
    SAFE_HOUR_END = parse_time(end_raw)

    # LOAD MEMORY
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    memory_data = {}
    memory_changed = False 
    
    try:
        raw_mem = state.get(MEMORY_ENTITY)
        if raw_mem and raw_mem not in ["unknown", "unavailable", ""]:
            memory_data = json.loads(raw_mem)
    except Exception as e:
        if DEBUG: log.warning(f"Memory Load Error: {e}")
        memory_data = {}

    def save_memory():
        try:
            clean_data = {k: v for k, v in memory_data.items() if v == today_str}
            
            # --- COMPRESSION CHECK ---
            json_str = json.dumps(clean_data)
            if len(json_str) > 240:
                if DEBUG: log.warning("Memory near limit. Purging old warnings.")
                clean_data = {k: v for k, v in clean_data.items() if not k.startswith("c_")}
                json_str = json.dumps(clean_data)
            
            service.call("input_text", "set_value", entity_id=MEMORY_ENTITY, value=json_str)
        except Exception as e:
            if DEBUG: log.warning(f"Failed to save memory: {e}")

    # Helper to collect notification services
    unique_notify_services = set()
    for d, c in data.items():
        if d == "Settings": continue
        s = c.get("notification_service")
        if s: unique_notify_services.add(s)

    # 3. CHECK GLOBAL LOCKDOWN (Physical Switch Only)
    is_physical_lockdown = (LOCKDOWN_SWITCH and state.get(LOCKDOWN_SWITCH) == "on")

    if is_physical_lockdown:
        if DEBUG: log.info(f"⛔ DEBUG: PHYSICAL LOCKDOWN ACTIVE (Master Switch).")
        
        # Action: Force Locks Only (No Notifications - UniFi handles that)
        for door_name, config in data.items():
            if door_name.lower() == "settings": continue
            reset_entity = config.get('reset_entity')
            lock_entity = config.get('entity')
            
            # We enforce the lock, but we don't change the rule permanently unless needed
            if reset_entity: 
                select.select_option(entity_id=reset_entity, option="keep_lock")
            if lock_entity and state.get(lock_entity) == "unlocked":
                lock.lock(entity_id=lock_entity)
        return

    # 4. CHECK PAUSE
    if state.get(PAUSE_ENTITY) == "on":
        if DEBUG: log.info("⏸️ DEBUG: System PAUSED.")
        return

    # 5. CHECK NIGHT MODE
    if now.hour < SAFE_HOUR_START or now.hour > SAFE_HOUR_END:
        if DEBUG: log.info(f"🌙 Night Mode Active (Hour: {now.hour}). Enforcing Locks.")
        
        for door_name, config in data.items():
            if door_name.lower() == "settings": continue
            
            reset_entity = config.get('reset_entity')
            lock_entity = config.get('entity')
            
            if reset_entity and state.get(reset_entity) == "keep_unlock":
                if DEBUG: log.info(f"   Night Mode: Resetting rule for {door_name}")
                select.select_option(entity_id=reset_entity, option="reset")
            
            if lock_entity and state.get(lock_entity) == "unlocked":
                if DEBUG: log.info(f"   Night Mode: Force Locking {door_name}")
                lock.lock(entity_id=lock_entity)

        # SEND NIGHTLY SUMMARY
        if memory_data.get("nightly_report") != today_str:
            for service_str in unique_notify_services:
                try:
                    domain, service_name = service_str.split('.', 1)
                    service.call(domain, service_name, message=f"🌙 Night Mode Active: All Doors Confirmed Locked.")
                except: pass
            
            memory_data["nightly_report"] = today_str
            memory_changed = True
            log.info("🌙 Nightly Summary Notification Sent.")
            
        if memory_changed: save_memory()
        return 

    # 6. CHECK DOORS
    for door_name, config in data.items():
        if door_name.lower() == "settings": continue

        try:
            # --- INDIVIDUAL LOCKDOWN CHECK ---
            # If THIS specific door is manually set to "keep_lock", we skip it.
            reset_entity = config.get('reset_entity')
            if reset_entity:
                current_rule = state.get(reset_entity)
                if current_rule == "keep_lock" or current_rule == "keep_locked":
                    if DEBUG: log.info(f"⛔ Skipping {door_name} (Manual Override Active)")
                    continue 

            try:
                keyword = state.get(config['keyword_helper']).lower()
                pre_min = float(state.get(config['pre_helper']))
                post_min = float(state.get(config['post_helper']))
            except:
                keyword = ""
                pre_min = 15
                post_min = 30

            calendar_entity = config.get('calendar')
            if not calendar_entity: continue

            # Fetch Events
            events = calendar.get_events(
                entity_id=calendar_entity, 
                start_date_time=now - timedelta(hours=2),
                end_date_time=now + timedelta(hours=2)
            )
            event_list = events.get(calendar_entity, {}).get("events", [])
            
            should_be_open = False
            matched_title = ""
            
            notify_service = config.get('notification_service')
            notify_type = config.get('notify_type', 'all') 
            
            def send_alert(msg, force=False):
                if not notify_service: return
                if notify_type == 'summary' and not force: return
                try:
                    domain, service_name = notify_service.split('.', 1)
                    service.call(domain, service_name, message=msg)
                except: pass

            for event in event_list:
                title = event.get("summary", "").lower()
                if "canceled" in title or "cancelled" in title: continue
                if keyword != "" and keyword not in title: continue 

                start_time = datetime.fromisoformat(event["start"])
                end_time = datetime.fromisoformat(event["end"])
                
                # --- CONFLICT DETECTOR ---
                conflict_msg = None
                s_hour = start_time.hour
                e_hour = end_time.hour
                
                if s_hour < SAFE_HOUR_START:
                    conflict_msg = f"⚠️ Schedule Conflict: '{event['summary']}' starts at {start_time.strftime('%I:%M %p')}. Night Mode ends at {start_raw}."
                elif e_hour > SAFE_HOUR_END:
                    conflict_msg = f"⚠️ Schedule Conflict: '{event['summary']}' ends at {end_time.strftime('%I:%M %p')}. Night Mode locks doors at {end_raw}."

                if conflict_msg:
                    # COMPRESSED KEY: c_DAYHOUR_First5CharsOfTitle
                    short_title = title[:5].replace(" ", "")
                    c_id = f"c_{start_time.strftime('%d%H')}_{short_title}"
                    
                    if memory_data.get(c_id) != today_str:
                        send_alert(f"{door_name}: {conflict_msg}", force=True)
                        memory_data[c_id] = today_str
                        memory_changed = True
                        log.warning(f"Conflict Detected: {conflict_msg}")
                # -----------------------------

                effective_start = start_time - timedelta(minutes=pre_min)
                effective_end = end_time + timedelta(minutes=post_min)
                
                if effective_start <= now.astimezone(start_time.tzinfo) <= effective_end:
                    should_be_open = True
                    matched_title = title
                    break 

            # ==========================================================
            #  EXECUTION LOGIC
            # ==========================================================
            lock_entity = config['entity']
            
            current_lock_state = state.get(lock_entity)
            current_rule_state = state.get(reset_entity) if reset_entity else None

            if should_be_open:
                # Persistence Check
                is_first_unlock = False
                if memory_data.get(door_name) != today_str:
                    is_first_unlock = True
                    memory_data[door_name] = today_str 
                    memory_changed = True

                if reset_entity:
                    if current_rule_state != "keep_unlock":
                        select.select_option(entity_id=reset_entity, option="keep_unlock")
                        
                        if notify_type == 'summary':
                            if is_first_unlock:
                                send_alert(f"{door_name}: Schedule Started (First Event: {matched_title}) 🔓", force=True)
                        else:
                            send_alert(f"{door_name} Set to Keep Unlocked (Event: {matched_title})", force=True)
                        log.info(f"🔓 SET KEEP UNLOCKED {door_name}")
                else:
                    if current_lock_state == "locked":
                        lock.unlock(entity_id=lock_entity)
                        if notify_type == 'summary':
                            if is_first_unlock:
                                send_alert(f"{door_name}: Schedule Started (First Event: {matched_title}) 🔓", force=True)
                        else:
                            send_alert(f"{door_name} Unlocked (Event: {matched_title})", force=True)
                        log.info(f"🔓 UNLOCKED {door_name}")

            else:
                # CLOSE LOGIC
                if reset_entity:
                    if current_rule_state == "keep_unlock":
                        select.select_option(entity_id=reset_entity, option="reset")
                        if notify_type == 'all':
                            send_alert(f"{door_name} Schedule Ended (Locked)", force=True)
                        log.info(f"🔒 RESET RULE {door_name}")
                else:
                    if current_lock_state == "unlocked":
                        lock.lock(entity_id=lock_entity)
                        if notify_type == 'all':
                            send_alert(f"{door_name} Locked (Schedule Clear)", force=True)
                        log.info(f"🔒 LOCKED {door_name}")
                    
        except Exception as e:
            log.error(f"Error processing {door_name}: {e}")
            
    if memory_changed:
        save_memory()

@time_trigger("cron(* * * * *)")
def run_every_minute():
    check_door_schedule()
