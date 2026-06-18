# English (source of truth). Keys here define the canonical set of strings.

STRINGS = {
    # App
    "app_title": "Creator Manager",
    "version": "v1.0",

    # Top bar
    "start_watch": "Start watching",
    "pause_watch": "Pause watching",
    "watching": "Watching",
    "paused": "Paused",
    "refresh_all": "Refresh",
    "add_profile": "Add Profile",
    "settings": "Settings",
    "open_program_folder": "Open program folder",
    "changelog": "Changelog",

    # Welcome (no profiles)
    "welcome_title": "Profiles",
    "welcome_no_profiles": "No profiles configured.\nClick the green \"Add Profile\" button to get started.",

    # Profile tab
    "cycle": "Cycle:",
    "open_folder": "Open folder",
    "images": "Images",
    "videos": "Videos (names)",
    "no_videos": "(no videos)",
    "thumbnail_error": "[?]",

    # Add profile dialog
    "add_profile_title": "Add Profile",
    "profile_name": "Profile name:",
    "watch_folders": "Download folders to watch:",
    "add_folder": "Add folder",
    "remove_selected": "Remove selected",
    "confirm_add": "Add profile",
    "warn_enter_name": "Please enter a profile name.",
    "warn_add_folder": "Please add at least one download folder.",
    "warn_profile_exists": "A profile named \"{name}\" already exists.",
    "profile_added": "Profile \"{name}\" added with {n} folder(s).",

    # Remove profile
    "remove_profile_title": "Remove Profile",
    "select_profile_remove": "Select a profile to remove:",
    "remove": "Remove",
    "confirm_remove": "Remove profile \"{name}\" and its counters?\nThe moved files on disk will NOT be deleted.",
    "profile_removed": "Profile \"{name}\" removed.",

    # Credits tab
    "credits_tab": "Credits & generations",
    "credits_refresh": "Refresh",
    "reset_cycle": "Reset cycle",
    "profile_col": "Profile",
    "chatgpt_col": "ChatGPT (today / 8)",
    "gemini_col": "Gemini (today / 20)",
    "ta_col": "Tensor Art (credits)",
    "kling_col": "Kling (cycle / 1)",
    "higgs_col": "Higgsfield (cycle / 1)",
    "reset_cycle_confirm": "This will reset ALL counters (ChatGPT, Gemini, TensorArt, Kling, Higgsfield) for ALL profiles.\n\nContinue?",
    "cycle_reset": "Cycle reset.",

    # History tab
    "history_tab": "History",
    "history_open_file": "Open history.txt",
    "history_clear": "Clear history",
    "history_empty": "(history empty)",
    "clear_history_confirm": "Delete all the contents of history.txt?\nThis cannot be undone.",
    "history_cleared_error": "Error",

    # Notifications
    "notif_new_day": "New day ({date}): daily counters reset.",
    "notif_watch_paused": "Watching paused.",
    "notif_watch_started": "Watching active. Monitoring {n} folder(s).",
    "notif_profile_added": "Profile \"{name}\" added.",
    "notif_profile_removed": "Profile \"{name}\" removed.",
    "notif_cycle_reset": "Cycle reset.",
    "notif_limit_reached": "Limit reached.",

    # Settings dialog
    "settings_title": "Settings",
    "language": "Language:",
    "theme": "Theme:",
    "cycle_frequency": "Cycle frequency:",
    "cycle_anchor": "Cycle anchor day:",
    "watch_interval": "Watch interval (seconds):",
    "save": "Save",
    "cancel": "Cancel",
    "lang_change_restart": "Language will apply on next restart.",
    "settings_saved": "Settings saved.",

    # Cycle frequencies
    "freq_daily": "Daily",
    "freq_weekly": "Weekly",
    "freq_monthly": "Monthly",
    "freq_yearly": "Yearly",

    # First launch dialog
    "first_launch_title": "Choose your language",
    "first_launch_msg": "Welcome to Creator Manager. Select your language:",
    "continue": "Continue",

    # Close dialog
    "close_watch_active": "Watching is active.\n\nStop it and exit?",
    "close_title": "Exit",

    # Misc
    "last_move": "Last move: {perfil} · {herramienta} ({estado})",
    "today": "Today",
    "ok": "OK",
    "reset_all_data": "Delete All Data",
    "reset_all_data_confirm": "WARNING: This will permanently delete ALL data:\n\n• All profiles and their settings\n• Credits and generation counters\n• Movement history\n• Error logs\n• All files inside Profiles/ folders\n\nThis action CANNOT be undone.\n\nAre you sure?",
    "reset_all_data_title": "Delete All Data",
    "data_reset_done": "All data has been deleted.\n\nProfiles/ folder and user settings have been reset.\n\nThe application will now close.",
    "notification_sound": "Notification sound",
    "auto_start_watch": "Auto-start watching on launch",

    # File context menu
    "open_file": "Open",
    "rename": "Rename",
    "duplicate": "Duplicate",
    "delete": "Delete",
    "copy_suffix": "Copy",
    "rename_title": "Rename",
    "rename_prompt": "Enter new name:",
    "rename_exists": "A file with that name already exists.",
    "delete_title": "Delete",
    "confirm_delete": "Delete \"{name}\"?",
    "error": "Error",
}
