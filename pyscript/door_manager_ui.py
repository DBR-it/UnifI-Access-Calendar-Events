# door_manager_ui.py
# MASTER VERSION: v2.0.1
# FEATURES: File-Based Memory + Auto-Cleanup + DEBUG LOGGING

import json
import os
from datetime import datetime, timedelta

# MEMORY FILE LOCATION
MEMORY_FILE = "/config/pyscript/door_memory.json"

@pyscript_compile
def read_config_file(path):
    import yaml
    try:
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    except Exception:
        return None

@pyscript_compile
def load_memory_from_file():
    """Load memory from persistent JSON file"""
    import json
    try:
        with open(MEMORY_FILE, 'r') as f:
            data = json.load(f)
            return {"status": "success", "data": data, "count": len(data)}
    except FileNotFoundError:
        return {"status": "new_file", "data": {}, "count": 0}
    except Exception as e:
        return {"status": "error", "data": {}, "error": str(e)}

@pyscript_compile
def save_memory_to_file(data):
    """Save memory to persistent JSON file"""
    import json
    try:
        with open(MEMORY_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        return {"status": "success", "count": len(data)}
    except Exception as e:
        return {"status": "error", "error": str(e)}

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
    log.info("=" * 60)
    log.info("🚀 DOOR MANAGER: Starting check_door_schedule")

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
    now_date = now.date()

    log.info(f"🔍 DEBUG: Current time: {now}, hour: {now.hour}, minute: {now.minute}")
    log.info(f"🔍 DEBUG: Night mode hours: {SAFE_HOUR_END}:00 PM - {SAFE_HOUR_START}:00 AM")
    log.info(f"🔍 DEBUG: Default buffers: Pre={DEF_PRE}, Post={DEF_POST}")

    # =================================================================
    # LOAD MEMORY FROM FILE
    # =================================================================
    load_result = task.executor(load_memory_from_file)
    memory_data = load_result.get("data", {})
    memory_changed = False

    if load_result["status"] == "success":
        log.info(f"✅ Loaded memory: {load_result['count']} entries")
    elif load_result["status"] == "new_file":
        log.info("📝 Creating new memory file (first run)")
        memory_changed = True
    else:
        log.error(f"Failed to load memory: {load_result.get('error', 'Unknown error')}")

    # =================================================================
    # AUTO-CLEANUP: Remove old/expired entries
    # =================================================================
    clean_data = {}
    cleaned_count = 0

    for k, v in memory_data.items():
        keep_entry = False

        if v == "alerted" and k.startswith("conflict_"):
            try:
                parts = k.split('_')
                if len(parts) >= 4:
                    date_str = parts[2]
                    event_date = datetime.strptime(date_str, '%Y%m%d').date()
                    # Keep if event is today OR yesterday (might still be active overnight)
                    if event_date >= (now_date - timedelta(days=1)):
                        keep_entry = True
                    else:
                        cleaned_count += 1
            except:
                keep_entry = True
        elif v == today_str:
            keep_entry = True
        elif v not in ["alerted", today_str]:
            keep_entry = True

        if keep_entry:
            clean_data[k] = v

    if cleaned_count > 0:
        log.info(f"🧹 Cleaned up {cleaned_count} old memory entries")
        memory_changed = True

    memory_data = clean_data

    # Night mode verification code...
    if now.hour == SAFE_HOUR_END and now.minute == 0:
        verify_id = f"night_verify_{today_str}"
        if memory_data.get(verify_id) != today_str:
            doors_forced_locked = []
            active_events_running = []

            for door_name, config in data.items():
                if door_name.lower() == "settings": continue

                lock_entity = config.get('entity')
                reset_entity = config.get('reset_entity')
                current_state = state.get(lock_entity)

                if current_state == 'unlocked':
                    if reset_entity:
                        select.select_option(entity_id=reset_entity, option="reset")
                        log.info(f"🌙 NIGHT MODE: Reset rule {door_name}")
                    else:
                        lock.lock(entity_id=lock_entity)
                        log.info(f"🌙 NIGHT MODE: Locked {door_name}")

                    doors_forced_locked.append(door_name)

                    calendar_entity = config.get('calendar')
                    if calendar_entity:
                        try:
                            events = calendar.get_events(
                                entity_id=calendar_entity,
                                start_date_time=now - timedelta(hours=1),
                                end_date_time=now + timedelta(hours=1)
                            )
                            event_list = events.get(calendar_entity, {}).get("events", [])

                            for event in event_list:
                                title = event.get("summary", "")
                                if "canceled" in title.lower() or "cancelled" in title.lower():
                                    continue

                                start_time = datetime.fromisoformat(event["start"])
                                end_time = datetime.fromisoformat(event["end"])

                                pre_min = get_config_value(config.get('pre_buffer'), DEF_PRE)
                                post_min = get_config_value(config.get('post_buffer'), DEF_POST)
                                effective_start = start_time - timedelta(minutes=pre_min)
                                effective_end = end_time + timedelta(minutes=post_min)

                                if effective_start <= now.astimezone(start_time.tzinfo) <= effective_end:
                                    active_events_running.append(f"{door_name}: '{title}' (ends {end_time.strftime('%I:%M %p')})")
                                    break
                        except:
                            pass

            if DEF_NOTIFY:
                try:
                    domain, service_name = DEF_NOTIFY.split('.', 1)

                    if doors_forced_locked:
                        msg = f"🌙 Night Mode Active ({SAFE_HOUR_END}:00 PM)\n"
                        msg += f"🔒 Locked {len(doors_forced_locked)} door(s): {', '.join(doors_forced_locked)}\n"

                        if active_events_running:
                            msg += f"\n⚠️ NOTE: These doors had active events that were overridden:\n"
                            msg += "\n".join(active_events_running)
                        else:
                            msg += "\n✅ No conflicts - all events had ended."
                    else:
                        msg = f"🌙 Night Mode Active ({SAFE_HOUR_END}:00 PM)\n"
                        msg += f"✅ All doors already secured."

                    service.call(domain, service_name, message=msg)
                    memory_data[verify_id] = today_str
                    memory_changed = True
                    log.info(f"✅ Night verification: {len(doors_forced_locked)} locked, {len(active_events_running)} conflicts")
                except Exception as e:
                    log.error(f"Night verification failed: {e}")

    if LOCKDOWN_SWITCH and state.get(LOCKDOWN_SWITCH) == "on":
        log.info("🔒 LOCKDOWN MODE ACTIVE - Exiting")
        if memory_changed:
            task.executor(save_memory_to_file, memory_data)
        return

    if state.get(PAUSE_ENTITY) == "on":
        log.info("⏸️ PAUSE SWITCH ON - Exiting")
        if memory_changed:
            task.executor(save_memory_to_file, memory_data)
        return

    log.info(f"🚪 Processing {len([k for k in data.keys() if k.lower() != 'settings'])} doors...")

    for door_name, config in data.items():
        if door_name.lower() == "settings": continue

        try:
            log.info(f"\n--- Processing door: {door_name} ---")

            calendar_entity = config.get('calendar')
            if not calendar_entity:
                log.warning(f"No calendar configured for {door_name}")
                continue

            log.info(f"📅 Fetching events from {calendar_entity}")

            # Calculate time range
            start_dt = now - timedelta(hours=4)
            end_dt = now + timedelta(days=7)

            try:
                events_result = calendar.get_events(
                    entity_id=calendar_entity,
                    start_date_time=start_dt,
                    end_date_time=end_dt
                )
                event_list = events_result.get(calendar_entity, {}).get("events", [])
                log.info(f"📅 Found {len(event_list)} total events")
            except Exception as e:
                log.error(f"📅 Failed to get events: {e}")
                event_list = []

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
                    if DEBUG: log.info(f"📱 Notification sent: {msg[:50]}...")
                except Exception as e:
                    log.error(f"Notification failed: {e}")

            for event in event_list:
                title = event.get("summary", "").lower()
                if "canceled" in title or "cancelled" in title: continue

                raw_key = config.get('keyword_helper')
                if not raw_key: raw_key = config.get('keyword')
                keyword = get_string_value(raw_key)

                log.info(f"🔑 Checking event '{event.get('summary')}' with keyword '{keyword}'")

                is_global_match = (GLOBAL_KEYWORD and GLOBAL_KEYWORD in title)
                is_local_match = (keyword != "" and keyword in title)

                if not is_global_match and not is_local_match:
                    log.info(f"   ❌ Keyword mismatch (looking for '{keyword}' or global '{GLOBAL_KEYWORD}')")
                    continue

                log.info(f"   ✅ Keyword matched!")

                start_time = datetime.fromisoformat(event["start"])
                end_time = datetime.fromisoformat(event["end"])
                event_date_str = start_time.strftime('%Y-%m-%d')

                # Conflict detection (simplified for now - skip detailed logging)
                event_date = start_time.date()

                if start_time.hour < SAFE_HOUR_START:
                    night_start = datetime.combine(event_date - timedelta(days=1), datetime.min.time().replace(hour=SAFE_HOUR_END, minute=0))
                    night_end = datetime.combine(event_date, datetime.min.time().replace(hour=SAFE_HOUR_START, minute=0))
                else:
                    night_start = datetime.combine(event_date, datetime.min.time().replace(hour=SAFE_HOUR_END, minute=0))
                    night_end = datetime.combine(event_date + timedelta(days=1), datetime.min.time().replace(hour=SAFE_HOUR_START, minute=0))

                night_start = night_start.replace(tzinfo=start_time.tzinfo)
                night_end = night_end.replace(tzinfo=start_time.tzinfo)

                conflict_type = None
                if night_start <= start_time < night_end:
                    conflict_type = "starts"
                elif night_start < end_time <= night_end:
                    conflict_type = "ends"
                elif start_time < night_start and end_time > night_end:
                    conflict_type = "spans"

                if conflict_type:
                    short_title = title[:8].replace(" ", "")
                    start_hour = start_time.strftime('%H')
                    conflict_id = f"conflict_{door_name}_{event_date_str.replace('-', '')}_{start_hour}_{short_title}"

                    if conflict_id not in memory_data:
                        conflict_msg = f"⚠️ SCHEDULE CONFLICT DETECTED\n"
                        conflict_msg += f"Door: {door_name}\n"
                        conflict_msg += f"Event: '{event['summary']}'\n"
                        conflict_msg += f"{conflict_type.capitalize()} at {start_time.strftime('%I:%M %p on %b %d')}\n"
                        conflict_msg += f"Overlaps Night Mode ({SAFE_HOUR_END}:00 PM - {SAFE_HOUR_START}:00 AM)\n"
                        conflict_msg += f"Doors will remain locked during night mode."

                        send_alert(conflict_msg, force=True)
                        memory_data[conflict_id] = "alerted"
                        memory_changed = True
                        log.info(f"🚨 CONFLICT ALERT: {conflict_id}")

                # =================================================================
                # NORMAL SCHEDULE PROCESSING - WITH DEBUG
                # =================================================================
                pre_min = get_config_value(config.get('pre_buffer'), DEF_PRE)
                post_min = get_config_value(config.get('post_buffer'), DEF_POST)

                log.info(f"   📊 Buffers: pre={pre_min}min, post={post_min}min")

                effective_start = start_time - timedelta(minutes=pre_min)
                effective_end = end_time + timedelta(minutes=post_min)

                log.info(f"   ⏰ Event time: {start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')}")
                log.info(f"   ⏰ Effective window: {effective_start.strftime('%I:%M %p')} - {effective_end.strftime('%I:%M %p')}")

                try:
                    now_tz = now.astimezone(start_time.tzinfo)
                    log.info(f"   ⏰ Current time (TZ adjusted): {now_tz.strftime('%I:%M %p')}")
                    log.info(f"   ⏰ Checking: {effective_start} <= {now_tz} <= {effective_end}")

                    if effective_start <= now_tz <= effective_end:
                        should_be_open = True
                        matched_title = title
                        log.info(f"   ✅ MATCH! Door should be UNLOCKED for this event")
                        break
                    else:
                        log.info(f"   ❌ Outside time window")
                except Exception as e:
                    log.error(f"   ❌ Timezone conversion error: {e}")

            lock_entity = config['entity']
            reset_entity = config.get('reset_entity')
            current_lock_state = state.get(lock_entity)
            current_rule_state = state.get(reset_entity) if reset_entity else None

            log.info(f"🔐 Current door state: {current_lock_state}")
            log.info(f"🔐 Should be open: {should_be_open}")

            # Override: Force lock during night mode hours
            if now.hour < SAFE_HOUR_START or now.hour >= SAFE_HOUR_END:
                log.info(f"🌙 Night mode override: Forcing door locked")
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
                            send_alert(f"🔓 {door_name}: Unlocked for '{matched_title}'", force=is_first_unlock)
                        log.info(f"🔓 SET KEEP UNLOCKED {door_name}")
                else:
                    if current_lock_state == "locked":
                        lock.unlock(entity_id=lock_entity)
                        if notify_type == 'all' or (notify_type == 'summary' and is_first_unlock):
                            send_alert(f"🔓 {door_name}: Unlocked for '{matched_title}'", force=is_first_unlock)
                        log.info(f"🔓 UNLOCKED {door_name}")

            else:
                if reset_entity:
                    if current_rule_state == "keep_unlock":
                        select.select_option(entity_id=reset_entity, option="reset")
                        if notify_type == 'all':
                            send_alert(f"🔒 {door_name}: Locked")
                        log.info(f"🔒 RESET RULE {door_name}")
                else:
                    if current_lock_state == "unlocked":
                        lock.lock(entity_id=lock_entity)
                        if notify_type == 'all':
                            send_alert(f"🔒 {door_name}: Locked")
                        log.info(f"🔒 LOCKED {door_name}")

        except Exception as e:
            log.error(f"Error processing {door_name}: {e}")

    if memory_changed:
        save_result = task.executor(save_memory_to_file, memory_data)
        if save_result["status"] == "success":
            log.info(f"💾 Saved memory: {save_result['count']} entries")
        else:
            log.error(f"Failed to save memory: {save_result.get('error', 'Unknown error')}")

    log.info("🏁 DOOR MANAGER: Finished")
    log.info("=" * 60)

@time_trigger("cron(* * * * *)")
def run_every_minute():
    check_door_schedule()
