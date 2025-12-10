<p align="center">
  <img src="Banner.png" alt="UniFi Access Door Manager Banner" style="width: 100%; height: auto;">
</p>

# UniFi Access Door Manager for Home Assistant

### ⚠️ IMPORTANT DISCLAIMER: READ BEFORE USE
**USE THIS SOFTWARE AT YOUR OWN RISK.**

This project is a community-created automation script and is **not** an official product of Ubiquiti/UniFi or Home Assistant. By downloading or using this software, you acknowledge and agree to the following:

1.  **NO LIABILITY:** The author(s) of this script accept **zero responsibility or liability** for any consequences resulting from the use of this software. This includes, but is not limited to: security breaches, unlocked doors, property damage, theft, hardware failure, or personal injury. You are solely responsible for the security of your facility.
2.  **NO WARRANTY:** This software is provided "as is," without warranty of any kind, express or implied.
3.  **Integration Dependencies:** This system relies entirely on third-party integrations (Home Assistant, UniFi Access, Pyscript, and Cloud Calendars). If any of these services fail, change their API, or lose internet connectivity, this automation **will fail**.
4.  **Configuration Responsibility:** Incorrect setup of entity IDs, helpers, or time zones can result in doors remaining unlocked overnight or locking unexpectedly. It is your responsibility to test your configuration thoroughly.

---

## 📺 Video Tutorial

**Need help setting this up? Watch my step-by-step guide on YouTube:**

**Coming soon**

*(Subscribe to the channel to be notified when it drops!)*

**If this project helped you, please don't forget to hit the Thumbs Up 👍 and Subscribe to the channel! It really helps out.**

---

**Automate your UniFi Access doors based on Google/Outlook Calendar schedules.**

This project allows Home Assistant to manage physical door locks by syncing with a calendar. It replaces the basic UniFi scheduling with advanced logic, including buffer times, safety lockdowns, night mode enforcement, and persistent "Keep Unlocked" rules.

## 🚀 Key Features

* **Universal Calendar Support:** Works with **any** calendar integration supported by Home Assistant (Google Calendar, Outlook 365, iCloud, CalDAV, Local Calendar, etc.).
* **Smart Buffers:** Configurable "Pre-Start" and "Post-End" buffers to keep doors open slightly longer than the event itself (e.g., unlock 15 mins early).
* **Conflict Detection:** Proactively warns you if a calendar event conflicts with your "Night Mode" security hours (e.g., scheduling a meeting that ends after the building automatically locks).
* **Persistent Unlocking:** Uses the UniFi "Keep Unlocked" rule instead of a momentary unlock command. This prevents the door from timing out and locking every 5 seconds.
* **Manual Override Respect:** The script is "State Aware." If you manually set a door to **"Keep Locked"** (Lockdown Mode), the script will detect this as an intentional override and **SKIP** that door until you reset it.
* **Night Mode ("The Bouncer"):** Forces all doors to lock at a set time (e.g., 11:59 PM). If a door is manually unlocked during the night, the script re-locks it within 60 seconds.
* **Emergency Controls:**
    * **Lockdown Mode:** Reacts instantly to the physical UniFi "Lock All Doors" switch or individual door overrides.
    * **Maintenance Pause:** Pauses the automation completely for manual testing or hardware maintenance.
* **Smart Notifications:** Receive daily summaries ("Schedule Started") and critical safety alerts.

---

## 📅 How Scheduling Works (The Keyword System)

Since you might have multiple doors (Front Door, Warehouse, Side Entrance) sharing one calendar, the script needs a way to know **which specific door** to unlock for a specific event.

It does this by looking for a **"Secret Code" (Keyword)** in your event title.

### 1. The Setup (Making the Link)
First, you assign a unique, short keyword to each door in your settings (inside `doors.yaml` or the Dashboard Helper).
* **Front Door Keyword:** `D1`
* **Warehouse Keyword:** `WH`

### 2. The Trigger (Creating the Event)
When you put an event on your Google/Outlook calendar, you simply **include that keyword in the Title**.
* **Event Title:** `Board Meeting D1`
    * **Result:** The script sees `D1`, looks up your settings, finds it belongs to **Front Door**, and unlocks it.

### 3. The Master Key (Unlock EVERYTHING)
You can create a special "Global Keyword" helper (e.g., `input_text.global_door_keyword`).
* **How it works:** Whatever text you type into this dashboard box becomes the **Master Key**.
* **Security Benefit:** If you use "ALL" and suspect someone guessed it, just go to your Dashboard and change the text to "Eagle77". The old keyword stops working instantly.
* **Example:**
    * **Dashboard Setting:** `ALL`
    * **Event Title:** `Company Party ALL` -> Unlocks EVERY door.

### 4. Privacy Protection
If an event title does **not** contain a matching keyword (e.g., "Dentist Appointment"), the script ignores it completely. The doors stay locked.

---

## ☁️ CRITICAL WARNING: Cloud Calendar Delays

**Please read this if you use Google Calendar or Outlook 365.**

Home Assistant polls cloud calendars roughly every **15 minutes**.
* **The Risk:** If you create an event *now* for a meeting starting in 5 minutes, Home Assistant might not see it until *after* the meeting starts.
* **The Solution:** Plan ahead (add events 30 mins early) OR use the **Local Calendar** integration for instant updates.

---

## 📦 Installation Guide

### Step 1: Install UniFi Access Integration
1.  Go to **HACS** > Integrations > Explore.
2.  Search for **UniFi Access** (by specialized-hacs).
3.  Click **Download** and then **Restart Home Assistant**.
4.  Go to **Settings > Devices & Services > Add Integration**.
5.  Search for **UniFi Access** and follow the prompts to log in.

### Step 2: Install Pyscript
1.  Go to **HACS** > Integrations > Explore.
2.  Search for **Pyscript**.
3.  Click **Download** and then **Restart Home Assistant**.
4.  Go to **Settings > Devices & Services > Add Integration**.
5.  Search for **Pyscript** and add it. (*Enable "Allow all imports" if prompted*).

### Step 3: Create Dashboard Helpers
Go to **Settings > Devices & Services > Helpers** and create the following:

| Name | Entity ID (Example) | Type | Purpose |
| :--- | :--- | :--- | :--- |
| **Pause Door Schedule** | `input_boolean.pause_door_schedule` | Toggle | Master switch to pause automation. |
| **Door Keyword** | `input_text.door_keyword` | Text | The keyword to look for in events (e.g., `*`). |
| **Global Keyword** | `input_text.global_door_keyword` | Text | **(Optional)** The Master Key to open ALL doors. |
| **Pre-Buffer** | `input_number.front_door_pre_buffer` | Number | Minutes to unlock *before* event. |
| **Post-Buffer** | `input_number.front_door_post_buffer` | Number | Minutes to keep open *after* event. |
| **Door Manager Memory** | `input_text.door_manager_memory` | Text | **Required.** Stores conflict alerts & prevents spam. |

### Step 4: Install via HACS (Custom Repository)
1.  Open **HACS** > Integrations.
2.  Click the **3 Dots** (top right) > **Custom Repositories**.
3.  **Repository:** Paste the URL of this GitHub repository.
4.  **Category:** Select **Integration** from the dropdown menu.
    * *(Note: HACS uses "Integration" for backend logic scripts like this).*
5.  Click **Add**.
6.  Find **"UniFi Access Door Manager"** in the list and click **Download**.

### Step 5: Add the Status Card
We have created a "Smart Status" card that shows you if the system is Running, Paused, or in Lockdown.

1.  Open the **`dashboard_card.yaml`** file in this GitHub repository.
2.  Copy the code.
3.  In Home Assistant, go to **Dashboard > Edit > Add Card > Manual**.
4.  Paste the code and update the entity IDs.
    * *Note: Requires "Mushroom Cards" from HACS.*

---

## ⚙️ Configuration

### Update `doors.yaml`
1.  Navigate to your `/config` folder using File Editor or VS Code.
2.  You will see a file named **`doors_example.yaml`** (downloaded by HACS).
3.  **RENAME this file** to **`doors.yaml`**.
    * *Why? This protects your settings. HACS will only update the example file, never your actual config.*
4.  Open it and update the following:
    * **Entity IDs:** Match your actual UniFi locks and rules.
    * **Calendar Entity:** Update `calendar.ha` to your calendar name.
    * **Physical Switch:** If you have a physical "All Doors Lockdown" switch in UniFi, add its entity ID to `lockdown_switch`.
    * **Notifications:** Add your service (e.g., `notify.mobile_app_iphone`).

---

## 🛠️ Maintenance & Support Policy

**This project is provided as a "Set and Forget" solution.**

* **Updates:** I will attempt to maintain this repository if breaking changes occur, but updates are not guaranteed.
* **Support:** Please do not rely on this for life-safety or critical security operations. If the integration breaks due to an external API change, you may need to disable the script and control your doors manually.

---

### Happy Automating! 🏠🔓
