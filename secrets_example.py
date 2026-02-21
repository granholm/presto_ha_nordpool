# secrets.py — update with your own values

WIFI_SSID     = "your_wifi_ssid"
WIFI_PASSWORD = "your_wifi_password"

HA_HOST       = "http://192.168.x.x:8123"   # Home Assistant URL (no trailing slash)
HA_TOKEN      = "your_long_lived_access_token"

# UTC offset in hours (no DST handling — update manually when clocks change)
# Examples:
#   Finland standard time (EET):  TIMEZONE_OFFSET = 2
#   Finland summer time (EEST):   TIMEZONE_OFFSET = 3
#   UK standard time (GMT):       TIMEZONE_OFFSET = 0
#   UK summer time (BST):         TIMEZONE_OFFSET = 1
#   Central Europe (CET):         TIMEZONE_OFFSET = 1
#   Central Europe summer (CEST): TIMEZONE_OFFSET = 2
TIMEZONE_OFFSET = 2

# Night mode — screen turns off during quiet hours
# Set QUIET_START >= QUIET_END to wrap midnight (e.g. 23 to 7)
QUIET_START   = 23   # hour to turn off (local time, 0-23)
QUIET_END     = 7    # hour to turn back on (local time, 0-23)
WAKE_DURATION = 300  # seconds to stay on after a touch (e.g. 300 = 5 minutes)