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

### 2. Create Required Helpers (Crucial!)
You must create these manually in **Settings > Devices & Services > Helpers**.
*Note: The script will not run without these.*

| Name | Entity ID | Type | Purpose |
| :--- | :--- | :--- | :--- |
| **Door Alerts** | `input_text.door_alerts` | Text | Displays conflict warnings on the dashboard. |
| **Selected Door** | `input_select.selected_door` | Dropdown | Selects which door to edit on the dashboard. **Add your door names as options** (e.g., "Front Door"). |
| **Door Memory** | `input_text.door_manager_memory` | Text | Internal memory to prevent notification spam. |
| **Pause Schedule** | `input_boolean.pause_door_schedule` | Toggle | Master switch to pause all automation. |
| **Show Door List**| `input_boolean.show_door_list` | Toggle | Used for the collapsible list on the dashboard. |
| **Global Keyword**| `input_text.global_door_keyword` | Text | Master keyword to unlock ALL doors (e.g., "ALL"). |
| **Night Mode Start**| `input_datetime.night_mode_start` | Time | When the building closes (Lockdown starts). |
| **Night Mode End** | `input_datetime.night_mode_end` | Time | When the building opens (Lockdown ends). |

### 3. Install the Script
1.  Navigate to your `/config/` folder using File Editor or VS Code.
2.  Create a folder named `pyscript` if it doesn't exist.
3.  Upload `door_manager_ui.py` to `/config/pyscript/`.
4.  Upload `doors.yaml` to `/config/pyscript/`.

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
