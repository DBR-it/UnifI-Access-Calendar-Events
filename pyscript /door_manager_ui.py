# door_manager_ui.py
# MASTER VERSION: v1.1.0
# INCLUDES: Conflict Alerts + Memory Compression + UniFi-Only Lockdown + DYNAMIC MASTER KEY + AUTO-UPDATE CHECKER

import json
import os
from datetime import datetime, timedelta

# --- VERSION CONTROL ---
CURRENT_VERSION = "1.1.0"
GITHUB_VERSION_URL = "https://github.com/DBR-it/UnifI-Access-Calendar-Events/blob/main/version.txt"
# -----------------------

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

# ... [KEEP YOUR EXISTING parse_time FUNCTION] ...
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

# ... [KEEP YOUR EXISTING SERVICE FUNCTION START] ...
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
    LOCKDOWN_SWITCH = settings.get("lockdown_switch", None) 
    MEMORY_ENTITY = settings.get("memory_entity", "input_text.door_manager_memory")
    UPDATE_SENSOR = "sensor.door_manager_update_status" # Virtual Sensor
    
    # NEW: DYNAMIC GLOBAL MASTER KEYWORD HELPER
    global_helper = settings.get("global_keyword_helper", None)
    GLOBAL_KEYWORD = None
    if global_helper:
        try:
            val = state.get(global_helper)
            if val and val not in ["unknown", "unavailable", ""]:
                GLOBAL_KEYWORD = val.lower()
        except: pass

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

    # --- UPDATE CHECKER LOGIC ---
    # Runs once a day (or if memory is empty) to check GitHub
    last_check = memory_data.get("last_update_check")
    if last_check != today_str:
        try:
            # We use task.executor to run the web request without blocking HA
            def fetch_version():
                import requests
                return requests.get(GITHUB_VERSION_URL).text.strip()
            
            remote_ver = task.executor(fetch_version)
            
            if remote_ver and remote_ver != CURRENT_VERSION:
                # Update Available!
                state.set(UPDATE_SENSOR, value="Update Available", attributes={"latest": remote_ver, "current": CURRENT_VERSION})
                if DEBUG: log.info(f"🚀 Update Available: {remote_ver}")
            else:
                state.set(UPDATE_SENSOR, value="Up to Date", attributes={"latest": CURRENT_VERSION, "current": CURRENT_VERSION})
            
            memory_data["last_update_check"] = today_str
            memory_changed = True
        except Exception as e:
            if DEBUG: log.warning(f"Update Check Failed: {e}")
    # ----------------------------

    def save_memory():
        try:
            clean_data = {k: v for k, v in memory_data.items() if v == today_str}
            json_str = json.dumps(clean_data)
            if len(json_str) > 240:
                if DEBUG: log.warning("Memory near limit. Purging old warnings.")
                clean_data = {k: v for k, v in clean_data.items() if not k.startswith("c_")}
                json_str = json.dumps(clean_data)
            service.call("input_text", "set_value", entity_id=MEMORY_ENTITY, value=json_str)
        except Exception as e:
            if DEBUG: log.warning(f"Failed to save memory: {e}")

    # ... [THE REST OF YOUR EXISTING LOGIC GOES HERE - NO CHANGES NEEDED BELOW] ...
    # (Checking Lockdown, Pause, Night Mode, and Doors...)
