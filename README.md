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
* **Dynamic Master Key:** Use an `input_text` helper on your dashboard to instantly set a "Master Password" that unlocks ALL doors (e.g., "CompanyParty2024").
* **Night Mode ("The Bouncer"):** Forces all doors to lock at a set time (e.g., 11:59 PM). If a door is manually unlocked during this time, the script re-locks it within 60 seconds.
* **Emergency Controls:**
    * **Lockdown Mode:** Reacts instantly to the physical UniFi "Lock All Doors" switch or individual door overrides.
    * **Maintenance Pause:** Pauses the automation completely for manual testing or hardware maintenance.

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
* **Example:**
    * **Dashboard Setting:** `ALL`
    * **Event Title:** `Company Party ALL` -> Unlocks EVERY door.

### 4. Privacy Protection
If an event title does **not** contain a matching keyword (e.g., "Dentist Appointment"), the script ignores it completely. The doors stay locked.

---

## 📦 Installation Guide

### Step 1: Install Dependencies
1.  **Install Pyscript:**
    * Open HACS > Integrations > Explore > Search "Pyscript" > Download.
    * Restart Home Assistant.
    * Go to Settings > Devices & Services > Add Integration > Pyscript.
    * *Check "Allow all imports" if prompted.*

### Step 2: Install the Door Manager
1.  **Download the Code:**
    * Go to the [GitHub Repository](https://github.com/YOUR_USERNAME/YOUR_REPO).
    * Click the green **Code** button > **Download ZIP**.
    * Extract the ZIP file on your computer.
2.  **Copy Files to Home Assistant:**
    * Use the **File Editor** add-on (or Studio Code Server) in Home Assistant.
    * Navigate to `/config/`.
    * Create a folder named `pyscript` (if it doesn't exist).
    * Upload `door_manager_ui.py` and `doors_example.yaml` into that folder.

### Step 3: Configure Settings
1.  In the `/config/pyscript/` folder, find `doors_example.yaml`.
2.  **Rename it** to `doors.yaml`.
3.  Open `doors.yaml` and update the Entity IDs to match your UniFi locks and rules.

### Step 4: Create Dashboard Helpers
Go to **Settings > Devices & Services > Helpers** and create these (required):

| Name | Entity ID | Type |
| :--- | :--- | :--- |
| **Pause Door Schedule** | `input_boolean.pause_door_schedule` | Toggle |
| **Door Keyword** | `input_text.door_keyword` | Text |
| **Global Keyword** | `input_text.global_door_keyword` | Text |
| **Door Manager Memory** | `input_text.door_manager_memory` | Text |
| **Pre-Buffer** | `input_number.front_door_pre_buffer` | Number |
| **Post-Buffer** | `input_number.front_door_post_buffer` | Number |

### Step 5: Add the Status Card
1.  Open `dashboard_card.yaml` in the downloaded files.
2.  Copy the code.
3.  In Home Assistant, go to **Dashboard > Edit > Add Card > Manual**.
4.  Paste the code and update the entity IDs.
    * *Note: Requires "Mushroom Cards" from HACS.*

---

### Happy Automating! 🏠🔓
