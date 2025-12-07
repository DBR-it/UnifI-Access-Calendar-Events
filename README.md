<p align="center">
  <img src="Unifi.png" alt="Your Image Alt Text" style="width: 100%; height: auto;">
</p>

# UniFi Access Door Manager for Home Assistant

### ⚠️ IMPORTANT DISCLAIMER: READ BEFORE USE
**USE THIS SOFTWARE AT YOUR OWN RISK.**

This project is a community-created automation script and is **not** an official product of Ubiquiti/UniFi or Home Assistant. By using this software, you acknowledge and agree to the following:

1.  **You are responsible for your own security.** The author(s) of this script accept **no liability** for any security breaches, unlocked doors, property damage, or theft resulting from the use or misuse of this software.
2.  **Integration Dependencies:** This system relies entirely on third-party integrations (Home Assistant, UniFi Access, Pyscript, and Cloud Calendars). If any of these services fail, change their API, or lose internet connectivity, this automation **will fail**.
3.  **Configuration Responsibility:** Incorrect setup of entity IDs, helpers, or time zones can result in doors remaining unlocked overnight or locking unexpectedly. It is your responsibility to test your configuration thoroughly before relying on it.
4.  **No Warranty:** This software is provided "as is" without warranty of any kind.

---

**Automate your UniFi Access doors based on Google/Outlook Calendar schedules.**

This project allows Home Assistant to manage physical door locks by syncing with a calendar. It replaces the basic UniFi scheduling with advanced logic, including buffer times, safety lockdowns, night mode enforcement, and persistent "Keep Unlocked" rules.

## 🚀 Key Features

* **Universal Calendar Support:** Works with **any** calendar integration supported by Home Assistant (Google Calendar, Outlook 365, iCloud, CalDAV, Local Calendar, etc.). If Home Assistant can see the events, this script can use them.
* **Smart Buffers:** Configurable "Pre-Start" and "Post-End" buffers to keep doors open slightly longer than the event itself (e.g., unlock 15 mins early).
* **Persistent Unlocking:** Uses the UniFi "Keep Unlocked" rule instead of a momentary unlock command. This prevents the door from timing out and locking every 5 seconds.
* **Manual Override Respect:** The script is "State Aware." If you manually set a door to **"Keep Locked"** (via the UniFi App or HA), the script will detect this as an intentional override and **SKIP** that door until you reset it.
* **Night Mode ("The Bouncer"):** A security feature that forces all doors to lock at a set time (e.g., 11:59 PM). If a door is manually unlocked during the night, the script will automatically re-lock it within 60 seconds.
* **Emergency Controls:**
    * **Lockdown Mode:** Instantly locks *all* doors via a single dashboard toggle.
    * **Maintenance Pause:** Pauses the automation completely for manual testing or hardware maintenance.
* **Smart Notifications:** Choose between receiving alerts for *every* event or just a daily summary ("Schedule Started" / "Building Secured").

---

## ☁️ CRITICAL WARNING: Cloud Calendar Delays

**Please read this if you use Google Calendar or Outlook 365.**

Home Assistant does **not** receive updates from cloud calendars instantly. It polls for changes roughly every **15 minutes**.

* **The Risk:** If you create an event *now* for a meeting starting in 5 minutes, Home Assistant might not see it until *after* the meeting starts.
* **The Solution:**
    1.  **Plan Ahead:** Add events to your calendar at least 20-30 minutes in advance.
    2.  **Emergency Cancellation:** If you need to stop an event *immediately* while the door is unlocked, **DELETE the event** (do not just rename it). Deleting is often processed faster, but for instant results, use the **"Lockdown Mode"** helper on your dashboard.
* **Instant Alternative:** For immediate response times, use the **Local Calendar** integration built directly into Home Assistant. It has zero delay.

---

## 📦 Installation Guide

### Step 1: Install UniFi Access Integration
You first need to connect your UniFi Access Hubs to Home Assistant.
1.  Go to **HACS** > Integrations > Explore.
2.  Search for **UniFi Access** (by specialized-hacs or similar community developer).
3.  Click **Download** and then **Restart Home Assistant**.
4.  Go to **Settings > Devices & Services > Add Integration**.
5.  Search for **UniFi Access** and follow the prompts to log in to your UniFi Console.
6.  **Verify:** Check your Dashboard to ensure you can see your door locks (e.g., `lock.front_door`) and rule selectors (`select.front_door_rule`).

### Step 2: Install Pyscript
1.  Go to **HACS** > Integrations > Explore.
2.  Search for **Pyscript**.
3.  Click **Download** and then **Restart Home Assistant**.
4.  Go to **Settings > Devices & Services > Add Integration**.
5.  Search for **Pyscript** and add it.
    * *Note: If prompted, enable "Allow all imports".*

### Step 3: Create Dashboard Helpers
You need to create "Helpers" to act as the settings knobs for your dashboard. Go to **Settings > Devices & Services > Helpers** and create the following:

| Name | Entity ID (Example) | Type | Purpose |
| :--- | :--- | :--- | :--- |
| **Pause Door Schedule** | `input_boolean.pause_door_schedule` | Toggle | Master switch to pause automation. |
| **Lockdown Mode** | `input_boolean.lockdown_mode` | Toggle | Emergency lock for ALL doors. |
| **Door Keyword** | `input_text.door_keyword` | Text | The keyword to look for in events (e.g., `*`). |
| **Pre-Buffer** | `input_number.front_door_pre_buffer` | Number | Minutes to unlock *before* event. |
| **Post-Buffer** | `input_number.front_door_post_buffer` | Number | Minutes to keep open *after* event. |

### Step 4: Download & Install Files
1.  Download the **`doors.yaml`** and **`door_manager_ui.py`** files from this repository.
2.  Using your File Editor (or VS Code) in Home Assistant, navigate to the `/config/` directory.
3.  Find (or create) the folder named `pyscript`.
4.  **Upload both files into the `/config/pyscript/` folder.**

---

## ⚙️ Configuration

### Update `doors.yaml`
You **must** edit the `doors.yaml` file to match your specific system. Open the file and update the following:

1.  **Entity IDs:** Change `lock.door_0664` and `select.door_0664_door_lock_rule` to match your actual UniFi device names found in Step 1.
2.  **Calendar Entity:** Update `calendar.ha` to the name of your specific calendar entity.
3.  **Notifications:** Add your notification service (e.g., `notify.mobile_app_iphone`) and choose your style (`summary` or `all`).

---

## 🛠️ Maintenance & Support Policy

**This project is provided as a "Set and Forget" solution.**

* **Updates:** I will attempt to maintain this repository if breaking changes occur in Home Assistant or UniFi, but **updates are not guaranteed**.
* **Support:** Please do not rely on this for life-safety or critical security operations. If the integration breaks due to an external API change, you may need to disable the script and control your doors manually until a fix is found.

---

### Happy Automating! 🏠🔓
