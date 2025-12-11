# door_manager_ui.py
# MASTER VERSION: v1.13.0
# FEATURES: Nightly Report Restored + Phone-Only Alerts + Timezone Fix

import json
import os
import sys
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
    except Exception:
        return None

def parse_time(value):
    try:
        if isinstance(value, int): return value
        from datetime import datetime
        val_str = str(value).strip()
        if "." in val_str and state.get(val_str) not in ["unknown", "unavailable", None]:
            val_str = state.get(val_str)
        if ":" in val_str:
            try: return datetime.strptime(val_str, "%H:%M:%S").hour
            except: pass
            try: return datetime.strptime(val_str, "%I:%M %p").hour
            except: pass
            try: return datetime.strptime(val_str, "%H:%M").hour
            except: pass
        if "AM" in val_str.upper() or "PM" in val_str.upper():
             return datetime.strptime(val_str.upper(), "%I %p").hour
        return int(float(val_str))
    except: return 0 

def get_config_value(val, default_val=0):
    if val is None: return float(default_val)
    if isinstance(val, (int, float)): return float(val)
    val_str = str(val).strip()
    if "." in val_str and state.get(val_str) not in ["unknown", "unavailable", None]:
        try: return float(state.get(val_str))
        except: return float(default_val)
    try: return float(val_str)
    except: return float(default_val)

def get_string_value(val):
    if not val: return ""
    val_str = str(val).strip()
    if "." in val_str:
        s = state.get(val_str)
        if s and s not in ["unknown", "unavailable", None]:
            return str(s).lower()
    return val_str.lower()

@service
def check_door_schedule():
    CONFIG_FILE = "/config/pyscript/doors.yaml"
    data = task.executor(read_config_file, CONFIG_FILE)
    if data is None:
        log.error(f"Door Manager: Could not read {CONFIG_FILE}.")
        return

    settings = data.pop("Settings", {})
    if not settings: settings = data.pop("settings", {})
    defaults = data.pop("Defaults", {})
    if not defaults: defaults = data.pop("defaults", {})

    PAUSE_ENTITY = settings.get("pause_entity", "input_boolean.pause_door_schedule")
    LOCKDOWN_SWITCH = settings.get("lockdown_switch", None) 
    MEMORY_ENTITY = settings.get("memory_entity", "input_text.door_manager_memory")
    
    DEF_PRE = defaults.get("pre_buffer", 15)
    DEF_POST = defaults.get("post_buffer", 15)
    DEF_NOTIFY = defaults.get("notification_service", None)
    
    global_helper = settings.get("global_keyword_helper", None)
    GLOBAL_KEYWORD = None
    if global_helper:
        try:
            val = state.get(global_helper)
            if val and val not in ["unknown", "unavailable", ""]:
                GLOBAL_KEYWORD = val.lower()
        except: pass

    DEBUG = settings.get("debug_logging", False)
    
    nm_start_raw = settings.get("night_mode_start", "11:59 PM")
    nm_end_raw = settings.get("night_mode_end", "6 AM")
    SAFE_HOUR_END = parse_time(nm_start_raw)
    SAFE_HOUR_START = parse_time(nm_end_raw)

    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    memory_data = {}
    memory_changed = False 
    
    try:
        raw_mem = state.get(MEMORY_ENTITY)
        if raw_mem and raw_mem not in ["unknown", "unavailable", ""]:
            memory_data = json.loads(raw_mem)
    except Exception as e:
        memory_data = {}

    def save_memory():
        try:
            clean_data = {k: v for k, v in memory_data.items() if v == today_str}
            json_str = json.dumps(clean_data)
            service.call("input_text", "set_value", entity_id=MEMORY_ENTITY, value=json_str)
        except: pass
    
    # -------------------------------------------------------------
    # NEW: NIGHTLY REPORT (The "Shift End" Check)
    # -------------------------------------------------------------
    # Runs exactly at the start of Night Mode (Safe Hour End)
    if now.hour == SAFE_HOUR_END and now.minute == 0:
        if last_nightly_report.get("date") != today_str:
            unlocked_doors = []
            
            # Check physical state of all configured doors
            for door_name, config in data.items():
                if door_name.lower() == "settings": continue
                entity_id = config.get('entity')
                if state.get(entity_id) == 'unlocked':
                    unlocked_doors.append(door_name)
            
            # Send Report
            if DEF_NOTIFY:
                try:
                    domain, service_name = DEF_NOTIFY.split('.', 1)
                    if unlocked_doors:
                        msg = f"Night Mode Active. ⚠️ WARNING: These doors are still unlocked: {', '.join(unlocked_doors)}"
                    else:
                        msg = "Night Mode Active. 🔒 All doors verified locked."
                    
                    service.call(domain, service_name, message=msg)
                    last_nightly_report["date"] = today_str
                except: pass
    # -------------------------------------------------------------

    if LOCKDOWN_SWITCH and state.get(LOCKDOWN_SWITCH) == "on": return
    if state.get(PAUSE_ENTITY) == "on": return

    for door_name, config in data.items():
        if door_name.lower() == "settings": continue

        try:
            calendar_entity = config.get('calendar')
            if not calendar_entity: continue

            events = calendar.get_events(
                entity_id=calendar_entity, 
                start_date_time=now - timedelta(hours=4),
                end_date_time=now + timedelta(hours=4)
            )
            event_list = events.get(calendar_entity, {}).get("events", [])
            
            should_be_open = False
            matched_title = ""
            
            notify_service = config.get('notification_service', DEF_NOTIFY)
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
                
                raw_key = config.get('keyword_helper')
                if not raw_key: raw_key = config.get('keyword')
                keyword = get_string_value(raw_key)

                is_global_match = (GLOBAL_KEYWORD and GLOBAL_KEYWORD in title)
                is_local_match = (keyword != "" and keyword in title)

                if not is_global_match and not is_local_match: continue 

                start_time = datetime.fromisoformat(event["start"])
                end_time = datetime.fromisoformat(event["end"])
                
                # --- CONFLICT CHECK ---
                if end_time > now.astimezone(end_time.tzinfo):
                    conflict_msg = None
                    s_hour = start_time.hour
                    e_hour = end_time.hour
                    
                    if s_hour < SAFE_HOUR_START:
                        conflict_msg = f"⚠️ CONFLICT: '{event['summary']}' starts at {start_time.strftime('%I:%M %p')} (Night Mode)."
                    elif e_hour > SAFE_HOUR_END:
                        conflict_msg = f"⚠️ CONFLICT: '{event['summary']}' ends at {end_time.strftime('%I:%M %p')} (Night Mode)."
                    elif e_hour < SAFE_HOUR_START:
                        conflict_msg = f"⚠️ CONFLICT: '{event['summary']}' ends at {end_time.strftime('%I:%M %p')} (Night Mode)."

                    if conflict_msg:
                        short_title = title[:5].replace(" ", "")
                        c_id = f"c_{start_time.strftime('%d%H')}_{short_title}"
                        if memory_data.get(c_id) != today_str:
                            send_alert(f"{door_name}: {conflict_msg}", force=True)
                            memory_data[c_id] = today_str
                            memory_changed = True
                
                pre_min = get_config_value(config.get('pre_buffer'), DEF_PRE)
                post_min = get_config_value(config.get('post_buffer'), DEF_POST)

                effective_start = start_time - timedelta(minutes=pre_min)
                effective_end = end_time + timedelta(minutes=post_min)
                
                if effective_start <= now.astimezone(start_time.tzinfo) <= effective_end:
                    should_be_open = True
                    matched_title = title
                    break 

            lock_entity = config['entity']
            reset_entity = config.get('reset_entity')
            current_lock_state = state.get(lock_entity)
            current_rule_state = state.get(reset_entity) if reset_entity else None

            if now.hour < SAFE_HOUR_START or now.hour > SAFE_HOUR_END:
                should_be_open = False 

            if should_be_open:
                is_first_unlock = False
                if memory_data.get(door_name) != today_str:
                    is_first_unlock = True
                    memory_data[door_name] = today_str 
                    memory_changed = True

                if reset_entity:
                    if current_rule_state != "keep_unlock":
                        select.select_option(entity_id=reset_entity, option="keep_unlock")
                        if notify_type == 'all' or (notify_type == 'summary' and is_first_unlock):
                            send_alert(f"{door_name}: Unlocked for '{matched_title}'", force=True)
                        log.info(f"🔓 SET KEEP UNLOCKED {door_name}")
                else:
                    if current_lock_state == "locked":
                        lock.unlock(entity_id=lock_entity)
                        if notify_type == 'all' or (notify_type == 'summary' and is_first_unlock):
                            send_alert(f"{door_name}: Unlocked for '{matched_title}'", force=True)
                        log.info(f"🔓 UNLOCKED {door_name}")

            else:
                if reset_entity:
                    if current_rule_state == "keep_unlock":
                        select.select_option(entity_id=reset_entity, option="reset")
                        if notify_type == 'all': send_alert(f"{door_name} Locked", force=True)
                        log.info(f"🔒 RESET RULE {door_name}")
                else:
                    if current_lock_state == "unlocked":
                        lock.lock(entity_id=lock_entity)
                        if notify_type == 'all': send_alert(f"{door_name} Locked", force=True)
                        log.info(f"🔒 LOCKED {door_name}")
                    
        except Exception as e:
            log.error(f"Error processing {door_name}: {e}")
            
    if memory_changed:
        save_memory()

@time_trigger("cron(* * * * *)")
def run_every_minute():
    check_door_schedule()
