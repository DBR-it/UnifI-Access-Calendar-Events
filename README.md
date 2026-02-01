<p align="center">
  <img src="Banner.png" alt="UniFi Access Door Manager Banner" style="width: 100%; height: auto;">
</p>

# 🔐 UniFi Access Door Manager (for Home Assistant)

**Automate your commercial or residential locks using Google/Outlook Calendars.**

This Pyscript automation links your calendar events to your smart locks (UniFi Access, August, Schlage, etc.) with professional features like "Night Mode" security, pre-meeting buffers, and a live dashboard interface.

---

## ⚠️ Disclaimer & Liability
**USE AT YOUR OWN RISK.**

This software controls physical access to your building. While every effort has been made to ensure safety and reliability (including "Night Mode" fail-safes), the authors are not liable for:
* **Integration Failures:** If Home Assistant, UniFi Access, Pyscript, or Google Calendar pushes an update that breaks compatibility, this script may stop working immediately.
* **Lockouts:** Doors failing to unlock due to power outages, network loss, or configuration errors.
* **Security:** Unauthorized access or doors remaining unlocked due to user error.

**CRITICAL:** You must **thoroughly test your own configuration** before deploying this in a live environment.
**ALWAYS carry a physical key or have a backup entry method.**

---

## ✨ Features
* **📅 Calendar Sync:** Unlocks doors automatically based on calendar events.
* **🛡️ Night Mode ("The Bouncer"):** Strictly forces doors locked during specific hours (e.g., 11 PM - 6 AM), even if a calendar event is scheduled.
* **🚦 Conflict Alerts:** Detects and warns you if a scheduled event violates Night Mode rules (sends Phone Notification + Dashboard Alert).
* **⏳ Smart Buffers:** Open doors *before* the event starts (Pre-Buffer) and keep them open *after* (Post-Buffer).
* **📱 Dashboard Control:** Adjust buffers, change Night Mode hours, and view lock status directly from the Lovelace dashboard.
* **🔑 Keywords:** Securely link specific doors to specific events using keywords (e.g., "Meeting **D1**").
* **🚨 Emergency Lockdown:** One switch to immediately lock all doors and ignore the schedule.
* **💾 File-Based Memory:** Persistent memory storage that survives Home Assistant reboots (no more duplicate notifications!).
* **🧹 Auto-Cleanup:** Automatically removes old conflict alerts and memory entries to prevent bloat.

---

## 🛠️ Prerequisites
You need these installed in Home Assistant before you begin:

1.  **UniFi Access Integration** (via HACS)
    * *Required to expose your UniFi Readers/Locks to Home Assistant.*
2.  **Pyscript** (via HACS > Integrations)
    * *Runs the Python logic engine.*
3.  **Google Calendar** or **Local Calendar** (Home Assistant Core)
    * *Source of your schedule events.*
4.  **Mushroom Cards** (via HACS > Frontend)
    * *Required for the beautiful dashboard cards.*
5.  **Card Mod** (via HACS > Frontend)
    * *(Optional)* *Used to highlight the "Selected Door" in Blue on the dashboard.*

---

## ⚙️ Installation

### 1. Install Integrations
Go to **HACS**, install the prerequisites listed above, and **Restart Home Assistant**.

### 2. Create Required Helpers
You must create these manually in **Settings > Devices & Services > Helpers**.
*Note: The script will not run without these.*

| Name | Entity ID | Type | Max Length | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **Door Alerts** | `input_text.door_alerts` | Text | **255** | Displays conflict warnings on the dashboard. Set max to 255 characters. |
| **Selected Door** | `input_select.selected_door` | Dropdown | N/A | Selects which door to edit on the dashboard. **Add your door names as options** (e.g., "Front Door"). |
| **Pause Schedule** | `input_boolean.pause_door_schedule` | Toggle | N/A | Master switch to pause all automation. |
| **Show Door List**| `input_boolean.show_door_list` | Toggle | N/A | Used for the collapsible list on the dashboard. |
| **Global Keyword**| `input_text.global_door_keyword` | Text | **255** | Master keyword to unlock ALL doors (e.g., "ALL"). Set max to 255 characters. |
| **Night Mode Start**| `input_datetime.night_mode_start` | Time | N/A | When the building closes (Lockdown starts). |
| **Night Mode End** | `input_datetime.night_mode_end` | Time | N/A | When the building opens (Lockdown ends). |

**REMOVED:** ~~`input_text.door_manager_memory`~~ - Now uses file-based storage automatically!

### 3. Install the Script
1.  Navigate to your `/config/` folder using File Editor or VS Code.
2.  Create a folder named `pyscript` if it doesn't exist.
3.  Upload `door_manager_ui.py` to `/config/pyscript/`.
4.  Upload `doors.yaml` to `/config/pyscript/`.
5.  **Reload Pyscript:** Go to **Developer Tools > YAML > Pyscript Python Scripting > Reload**

### 4. Configure Your Doors
Open `/config/pyscript/doors.yaml` and configure your locks.

**Example `doors.yaml`:**
```yaml
Settings:
  pause_entity: input_boolean.pause_door_schedule
  night_mode_start: input_datetime.night_mode_start
  night_mode_end: input_datetime.night_mode_end

Defaults:
  pre_buffer: 15
  post_buffer: 15
  notification_service: notify.mobile_app_iphone

Front Door:
  entity: lock.front_door
  calendar: calendar.office
  # Hybrid Config: Point to a helper for dashboard control...
  keyword_helper: input_text.door_keyword
  # ...OR just hardcode it here!
  # keyword: "D1"
  pre_buffer: 15
  post_buffer: 15
```

---

## 🆕 What's New in This Version

### File-Based Memory System
The system now uses **persistent JSON file storage** instead of the `input_text.door_manager_memory` helper:

**Benefits:**
- ✅ **Survives reboots** - No more duplicate notifications after Home Assistant restarts
- ✅ **No size limits** - Can track unlimited conflicts and events
- ✅ **Auto-cleanup** - Old entries are automatically purged
- ✅ **Easy debugging** - Just open `/config/pyscript/door_manager_memory.json` to inspect
- ✅ **Minimal disk writes** - Only writes when memory changes (typically 5-10 times per day)

**Memory File Location:** `/config/pyscript/door_manager_memory.json`

### Automatic Cleanup
The system automatically removes:
- Conflict alerts older than 7 days
- First unlock tracking after the date passes
- Night mode verification after the date passes

This prevents memory bloat and ensures optimal performance.

### Night Mode Improvements
- Events that end AFTER night mode begins no longer trigger 10-minute warnings
- Night mode start alert consolidates all active conflicts
- Better handling of events that span across night mode boundaries

---

## 📊 How It Works

### Memory Structure
The system tracks:
```json
{
  "Front Door": "2026-01-24",                          // Last unlock date
  "conflict_Front Door_20260124_D1CONFLI": "alerted",  // Conflict notification sent
  "reminder_Front Door_20260124": "2026-01-24",        // 10-min warning sent
  "night_verify_2026-01-24": "2026-01-24"             // Night mode check completed
}
```

### Cleanup Rules
Entries are removed when:
- **Conflict alerts:** After 7 days
- **Date-based entries:** After the date has passed
- **Night verifications:** After the date has passed

---

## 🐛 Troubleshooting

### Memory file not created?
1. Check logs: **Settings > System > Logs**
2. Look for: `"📝 Creating new memory file (first run)"` or `"✅ Loaded memory: X entries"`
3. Verify Pyscript is loaded: **Developer Tools > YAML > Pyscript Python Scripting > Reload**

### Duplicate notifications after reboot?
- Check if `/config/pyscript/door_manager_memory.json` exists
- Verify file has proper permissions (should be readable/writable)
- Check logs for file load errors

### Memory file getting too large?
- Old entries should auto-delete after 7 days
- Manually delete the file and it will recreate automatically
- Check for very old conflict alerts that might be stuck

---

## 📝 Configuration Notes

### Keyword Configuration
You can configure keywords in two ways:

**Option 1: Dashboard Control (Hybrid)**
```yaml
Front Door:
  keyword_helper: input_text.door_keyword
```

**Option 2: Hardcoded**
```yaml
Front Door:
  keyword: "D1"
```

### Buffer Times
- **Pre-Buffer:** Minutes before event to unlock (prevents late arrivals from being locked out)
- **Post-Buffer:** Minutes after event to keep unlocked (allows for cleanup/stragglers)

### Night Mode
- Events that **overlap** night mode start time receive warnings
- Events that **start after** night mode are blocked entirely
- Night mode verification runs once per day to catch new conflicts

---

## 🤝 Contributing
Found a bug? Have a feature request? Open an issue on GitHub!

---

## 📜 License
MIT License - Use at your own risk.

---

## 🙏 Credits
Built with ❤️ using Home Assistant, Pyscript, and way too much coffee.
