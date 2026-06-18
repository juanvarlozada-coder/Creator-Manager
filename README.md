# Creator Manager v1.0 (Beta)
### Automated AI Content Workflow & Multi-Profile Credit Tracker

Creator Manager is an open-source, automation-driven desktop application written in Python. It is designed specifically for power users and content creators who leverage multiple accounts and generative AI platforms (such as ChatGPT, Gemini, Tensor Art, Kling, and Higgsfield) to generate massive quantities of daily assets.

Managing multiple active profiles often results in disorganized downloads, untracked asset histories, and unexpected credit depletion. Creator Manager elegantly solves this niche problem by continuously watching custom download directories, identifying asset origins via smart filename parsing, moving files automatically into organized monthly project folders, and precisely tracking resource/credit utilization across all configured profiles.

> ℹ️ *This project is a fully open-source public release (v1.0 Beta). All hardcoded personal paths, credentials, and custom profiles have been fully decoupled so anyone can configure their own setup instantly.*

---

## Key Features

* **⚡ Real-Time Directory Watcher:** Monitors multiple specific download folders simultaneously to capture and process newly generated assets the moment they are downloaded.
* **📂 Smart Asset Sorting & Categorization:** Automatically creates dedicated Image and Video subfolders inside your main directory on the 17th of each month. It reads filename indicators (e.g., `ChatGPT`, `Gemini_Generated`, `TA`, `kling`, `hf_`) to group files cleanly by tool origin.
* **📊 Advanced Credit Deductions:** Automatically calculates and tracks asset costs. Supports intricate tiered credit formulas such as Tensor Art LTX 2.3 video resolutions (10-second 480p costs 13 credits, 720p costs 30 credits, 3-second 480p costs 3.6 credits, and standalone images cost 0.2 credits).
* **🗂️ Tabbed UI Panel Navigation:** Fluid, modern tabbed browser structure built into a native window layout. Users can switch between profile workspaces with a single click, open or close tabs dynamically, and handle infinitely scaling profiles smoothly.
* **🌐 Native Multi-Language Support:** Completely multilingual from the ground up. Includes native language selection at first launch supporting English, Spanish, and Simplified Chinese (changeable at any time from Settings).
* **🌙 Secondary Dark Theme:** Full user customization with beautiful pre-configured Light and Dark themes. Theme configurations are isolated in a separate, human-readable file for easy extension and custom styles.
* **🔔 Desktop Notifications & Local Logs:** Provides instant OS-level desktop notification alerts for file movements and credit deductions, while logging every historical action inside a local `history.txt` file.
* **🔄 One-Click Updater & Launcher:** Includes streamlined `.bat` file launchers: `launcher.bat` to start the app cleanly via its subfolder, and `update.bat` to automatically look up updates on the GitHub repository.

---


## Credit Deductions & Platform Architecture

To accurately monitor resource depletion across multiple daily-resetting and monthly-resetting profiles, Creator Manager utilizes a rule-based credit parser based on file prefixes and sizes:

| AI Platform | Filename Keyword | Asset Type Supported | Credit Deduction Cost |
| :--- | :--- | :--- | :--- |
| **ChatGPT (OpenAI)** | `ChatGPT` | Daily Images | 1 Generation (Limit: 8/day) |
| **Gemini (Google)** | `Gemini_Generated` | Daily Images | 1 Generation (Limit: 20/day) |
| **Tensor Art (Images)** | `TA` | Images | 0.2 Credits per Image |
| **Tensor Art (LTX Video)** | `TA` | Video (10s @ 720p) | 30.0 Credits |
| **Tensor Art (LTX Video)** | `TA` | Video (10s @ 480p) | 13.0 Credits |
| **Tensor Art (LTX Video)** | `TA` | Video (3s @ 480p) | 3.6 Credits (approx) |
| **Kling AI 3.0** | `kling` | Monthly Videos | 1 Generation (Limit: 1/month) |
| **Higgsfield** | `hf_` | Dynamic Videos | 1 Generation (Variable) |

---

## Application Interface Showcase

Below are the actual interface captures from the application demonstrating the responsive multi-profile dashboard, navigation panels, and the integrated settings controller:

### Interface Snapshot 1
![Operational Interface Snapshot 1](image_d58d1e.png)

### Interface Snapshot 2
![Operational Interface Snapshot 2](image_d58cc2.png)

### Interface Snapshot 3
![Operational Interface Snapshot 3](image_d58c88.png)

---

## Installation & Setup Guide

### 📋 Prerequisites & Dependencies

Before running the application, make sure you have **Python 3.8+** installed on your system. 

You will also need to install the following external libraries required for core automation, the graphical user interface, and system notifications. Run this command in your terminal:

```bash
pip install watchdog plyer customtinter
