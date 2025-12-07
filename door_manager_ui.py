# door_manager_ui.py
# MASTER VERSION: Fixed Keep Unlocked + Manual Override + Smart Summary Notifications

# GLOBAL MEMORY: Tracks the last date we sent alerts to avoid spam
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
    import os
    from datetime import datetime, timedelta

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
    LOCKDOWN_ENTITY = settings.get("lockdown_entity", "input_boolean.lockdown_mode")
    DEBUG = settings.get("debug_logging", False)
    
    start_raw = settings.get("safe_hour_start", "6 AM")
    end_raw = settings.get("safe_hour_end", "10 PM")
    SAFE_HOUR_START = parse_time(start_raw)
    SAFE_HOUR_END = parse_time(end_raw)

    # 3. CHECK LOCKDOWN
    if state.get(LOCKDOWN_ENTITY) == "on":
        if DEBUG: log.info("⛔ DEBUG: LOCKDOWN ACTIVE.")
        for door_name, config in data.items():
            if door_name.lower() == "settings": continue
            reset_entity = config.get('reset_entity')
            lock_entity = config.get('entity')
            if reset_entity: select.select_option(entity_id=reset_entity, option="reset")
            if lock_entity and state.get(lock_entity) == "unlocked":
                lock.lock(entity_id=lock_entity)
        return

    # 4. CHECK PAUSE
    if state.get(PAUSE_ENTITY) == "on":
        if DEBUG: log.info("⏸️ DEBUG: System PAUSED.")
        return

    # 5. CHECK NIGHT MODE (The Bouncer & Nightly Report)
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    
    if now.hour < SAFE_HOUR_START or now.hour > SAFE_HOUR_END:
        if DEBUG: log.info(f"🌙 Night Mode Active (Hour: {now.hour}). Enforcing Locks.")
        
        # We collect services to send the "All Clear" message to
        unique_notify_services = set()
        
        for door_name, config in data.items():
            if door_name.lower() == "settings": continue

            reset_entity = config.get('reset_entity')
            lock_entity = config.get('entity')
            notify_service = config.get('notification_service')
            
            if notify_service:
                unique_notify_services.add(notify_service)

            # Reset the "Morning Tracker" so it's ready for tomorrow
            if door_name in last_unlock_tracker and last_unlock_tracker[door_name] != today_str:
                pass 

            # Force Lock Logic
            if reset_entity and state.get(reset_entity) == "keep_unlock":
                if DEBUG: log.info(f"   Night Mode: Resetting rule for {door_name}")
                select.select_option(entity_id=reset_entity, option="reset")
            
            if lock_entity and state.get(lock_entity) == "unlocked":
                if DEBUG: log.info(f"   Night Mode: Force Locking {door_name}")
                lock.lock(entity_id=lock_entity)

        # SEND NIGHTLY SUMMARY (Only once per night)
        # We check a global key "summary_sent" to ensure we only send it once per date
        if "summary_sent" not in last_nightly_report or last_nightly_report["summary_sent"] != today_str:
            for service_str in unique_notify_services:
                try:
                    domain, service_name = service_str.split('.', 1)
                    service.call(domain, service_name, message=f"🌙 Night Mode Active: All Doors Confirmed Locked.")
                except:
                    pass
            # Mark as sent for today
            last_nightly_report["summary_sent"] = today_str
            log.info("🌙 Nightly Summary Notification Sent.")
            
        return 

    # 6. CHECK DOORS (Daytime Logic)
    for door_name, config in data.items():
        if door_name.lower() == "settings": continue

        try:
            # Manual Override Check
            reset_entity = config.get('reset_entity')
            if reset_entity:
                current_rule = state.get(reset_entity)
                if current_rule == "keep_lock" or current_rule == "keep_locked":
                    if DEBUG: log.info(f"⛔ {door_name} is manually set to 'Keep Locked'. Skipping.")
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

            if DEBUG: log.info(f"🔍 Checking {door_name}: Found {len(event_list)} events")

            for event in event_list:
                title = event.get("summary", "").lower()
                if "canceled" in title or "cancelled" in title: continue
                if keyword != "" and keyword not in title: continue 

                start_time = datetime.fromisoformat(event["start"])
                end_time = datetime.fromisoformat(event["end"])
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
            notify_service = config.get('notification_service')
            notify_type = config.get('notify_type', 'all') 
            
            current_lock_state = state.get(lock_entity)
            current_rule_state = state.get(reset_entity) if reset_entity else None

            def send_alert(msg, force=False):
                if not notify_service: return
                if notify_type == 'summary' and not force: return
                try:
                    domain, service_name = notify_service.split('.', 1)
                    service.call(domain, service_name, message=msg)
                except: pass

            if should_be_open:
                # Logic: Is this the FIRST unlock of the day?
                is_first_unlock = False
                if door_name not in last_unlock_tracker or last_unlock_tracker[door_name] != today_str:
                    is_first_unlock = True
                    last_unlock_tracker[door_name] = today_str 

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

@time_trigger("cron(* * * * *)")
def run_every_minute():
    check_door_schedule()