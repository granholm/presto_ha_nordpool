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
#
# If QUIET_START < QUIET_END  → same-day window, e.g. 1 and 9  = off from 01:00 to 09:00
# If QUIET_START > QUIET_END  → wraps midnight,  e.g. 23 and 7 = off from 23:00 to 07:00
# If QUIET_START == QUIET_END → quiet mode disabled entirely
#
QUIET_START   = 23   # hour to turn display off (local time, 0-23)
QUIET_END     = 7    # hour to turn display on  (local time, 0-23)
WAKE_DURATION = 300  # seconds to stay on after a touch during quiet hours (300 = 5 min)
