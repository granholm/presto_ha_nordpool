# Nordpool Energy Price Dashboard for Pimoroni Presto
# ---------------------------------------------------------------------------
# Clean layout: centered clock, large price display, color-coded bar chart
# ---------------------------------------------------------------------------

import network
import ntptime
import urequests
import ujson
import time
from presto import Presto
import secrets

# ---------------------------------------------------------------------------
# CONFIG from secrets.py
# ---------------------------------------------------------------------------
WIFI_SSID        = secrets.WIFI_SSID
WIFI_PASSWORD    = secrets.WIFI_PASSWORD
HA_HOST          = secrets.HA_HOST
HA_TOKEN         = secrets.HA_TOKEN
TIMEZONE_OFFSET  = secrets.TIMEZONE_OFFSET   # e.g. 2 for EET (UTC+2), 3 for EEST (UTC+3)
SENSOR_ID        = "sensor.nordpool"
REFRESH_SECS     = 900                        # 15 minutes

# Night mode — display turns off during quiet hours
QUIET_START      = secrets.QUIET_START    # hour to turn off (e.g. 23)
QUIET_END        = secrets.QUIET_END      # hour to turn on  (e.g. 7)
WAKE_DURATION    = secrets.WAKE_DURATION  # seconds to stay on after a touch (e.g. 300)

# Chart range: 4 slots back (1h) + 20 slots forward (5h) at 15-min granularity
CHART_SLOTS_PAST   = 4    # 15-min slots back  = 1 hour
CHART_SLOTS_FUTURE = 20   # 15-min slots forward = 5 hours
CHART_SLOTS_TOTAL  = CHART_SLOTS_PAST + CHART_SLOTS_FUTURE

# Price tier thresholds (c/kWh)
PRICE_LOW_THRESHOLD  = 8.0
PRICE_MID_THRESHOLD  = 15.0

# ---------------------------------------------------------------------------
# Presto setup
# ---------------------------------------------------------------------------
presto  = Presto()
display = presto.display
W, H    = display.get_bounds()   # 480 x 480

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
C_BG        = display.create_pen( 10,  12,  28)
C_PANEL     = display.create_pen( 20,  24,  48)
C_GRID      = display.create_pen( 40,  44,  80)
C_AXIS      = display.create_pen(160, 170, 200)
C_WHITE     = display.create_pen(255, 255, 255)
C_CYAN      = display.create_pen( 80, 220, 255)
C_NOW_LINE  = display.create_pen( 60, 140, 255)   # blue for current time marker

# Three-tier pricing colors
C_PRICE_LOW  = display.create_pen( 60, 220, 100)   # green  (< 8)
C_PRICE_MID  = display.create_pen(255, 200,  40)   # yellow (8-15)
C_PRICE_HIGH = display.create_pen(255,  80,  60)   # red    (> 15)

# ---------------------------------------------------------------------------
# Helper: get color based on price tier
# ---------------------------------------------------------------------------
def price_color(price):
    if price < PRICE_LOW_THRESHOLD:
        return C_PRICE_LOW
    elif price < PRICE_MID_THRESHOLD:
        return C_PRICE_MID
    else:
        return C_PRICE_HIGH

# ---------------------------------------------------------------------------
# WiFi
# ---------------------------------------------------------------------------
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        return True
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    for _ in range(20):
        if wlan.isconnected():
            return True
        time.sleep(0.5)
    return False

# ---------------------------------------------------------------------------
# NTP sync — sets the internal RTC to UTC, called once on startup
# ---------------------------------------------------------------------------
def sync_ntp():
    for attempt in range(3):
        try:
            ntptime.settime()   # sets RTC to UTC
            return True
        except Exception:
            time.sleep(2)
    return False

# ---------------------------------------------------------------------------
# Get current local time string "HH:MM" using RTC + timezone offset
# ---------------------------------------------------------------------------
def get_local_time_hm():
    """Return (hour, minute) in local time by applying TIMEZONE_OFFSET to UTC."""
    t = time.gmtime()           # UTC from RTC (set by NTP)
    utc_minutes = t[3] * 60 + t[4]
    local_minutes = utc_minutes + int(TIMEZONE_OFFSET * 60)
    # Wrap around midnight
    local_minutes = local_minutes % (24 * 60)
    h = local_minutes // 60
    m = local_minutes % 60
    return h, m

def get_local_time_str():
    h, m = get_local_time_hm()
    return "{:02d}:{:02d}".format(h, m)

# ---------------------------------------------------------------------------
# Fetch sensor state from HA
# ---------------------------------------------------------------------------
def fetch_nordpool():
    url     = "{}/api/states/{}".format(HA_HOST, SENSOR_ID)
    headers = {
        "Authorization": "Bearer " + HA_TOKEN,
        "Content-Type":  "application/json",
    }
    r    = urequests.get(url, headers=headers, timeout=10)
    data = ujson.loads(r.content)
    r.close()
    return data

# ---------------------------------------------------------------------------
# Parse timestamp "2026-02-16T18:30:00+02:00" → (hour, minute)
# ---------------------------------------------------------------------------
def parse_hm(ts):
    t = ts[11:16]   # "18:30"
    return int(t[:2]), int(t[3:5])

# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------
def draw_text_centred(text, cx, y, scale=1):
    display.text(text, cx - len(text) * 6 * scale // 2, y, scale=scale)


# ---------------------------------------------------------------------------
# Night mode helpers
# ---------------------------------------------------------------------------
def in_quiet_hours(h):
    """Return True if hour h falls within the quiet period.

    Examples:
      QUIET_START=1,  QUIET_END=9  → quiet from 01:00 to 09:00 (no midnight wrap)
      QUIET_START=23, QUIET_END=7  → quiet from 23:00 to 07:00 (wraps midnight)
      QUIET_START=0,  QUIET_END=0  → never quiet (disabled)
    """
    if QUIET_START == QUIET_END:         # disabled — never quiet
        return False
    elif QUIET_START < QUIET_END:        # e.g. 01:00–09:00, no midnight wrap
        return QUIET_START <= h < QUIET_END
    else:                                # e.g. 23:00–07:00, wraps midnight
        return h >= QUIET_START or h < QUIET_END

def set_backlight(on):
    presto.set_backlight(1.0 if on else 0.0)

# ---------------------------------------------------------------------------
# Main draw
# ---------------------------------------------------------------------------
def draw_dashboard(data):
    attrs         = data["attributes"]
    current_price = attrs["current_price"]          # c/kWh
    avg_price     = attrs["average"]
    raw_today     = attrs["raw_today"]
    raw_tomorrow  = attrs.get("raw_tomorrow", [])

    # Use real NTP-synced local time instead of last_changed
    now_h, now_m  = get_local_time_hm()
    current_time  = "{:02d}:{:02d}".format(now_h, now_m)

    # Build flat list of all slots
    all_slots = raw_today + raw_tomorrow

    # Find current 15-min slot: match hour AND minute bucket (0, 15, 30, 45)
    now_quarter = (now_m // 15) * 15   # round down to 0, 15, 30, or 45
    now_idx = 0
    for i, s in enumerate(all_slots):
        sh, sm = parse_hm(s["start"])
        if sh == now_h and sm == now_quarter:
            now_idx = i
            break

    # Extract chart range: 4 slots (1h) back, 20 slots (5h) forward
    start_idx  = max(0, now_idx - CHART_SLOTS_PAST)
    end_idx    = now_idx + CHART_SLOTS_FUTURE
    chart_data = all_slots[start_idx : end_idx]

    # now_offset is exact — the current slot IS the bar, no fractional needed
    now_offset = now_idx - start_idx

    chart_vals = [s["value"] for s in chart_data]
    chart_max  = max(chart_vals) * 1.1 if chart_vals else 20
    chart_min  = 0.0

    # -----------------------------------------------------------------------
    # Layout constants
    # -----------------------------------------------------------------------
    PANEL_H    = 115   # Top panel height
    CX         = 30    # Chart left margin
    CY         = PANEL_H + 15
    CW         = W - CX - 10
    CH         = H - CY - 20

    def val_y(v):
        ratio = (v - chart_min) / (chart_max - chart_min) if chart_max != chart_min else 0.5
        return CY + CH - int(ratio * CH)

    bar_gap = 2
    bar_w   = (CW / len(chart_vals)) - bar_gap if chart_vals else 1

    base_y = CY + CH

    # -----------------------------------------------------------------------
    # Background
    # -----------------------------------------------------------------------
    display.set_pen(C_BG)
    display.clear()

    # Top panel background
    display.set_pen(C_PANEL)
    display.rectangle(0, 0, W, PANEL_H)

    # -----------------------------------------------------------------------
    # Top panel — clock (real NTP local time)
    # -----------------------------------------------------------------------
    display.set_pen(C_CYAN)
    draw_text_centred(current_time, W // 2, 8, scale=3)

    # -----------------------------------------------------------------------
    # Current price - large, centered, color-coded
    # -----------------------------------------------------------------------
    price_str = "{:.2f}".format(current_price)

    display.set_pen(price_color(current_price))
    draw_text_centred(price_str, W // 2 - 25, 40, scale=5)

    display.set_pen(C_AXIS)
    display.text("c/kWh", W // 2 + 70, 65, scale=1)

    # -----------------------------------------------------------------------
    # Stats row
    # -----------------------------------------------------------------------
    avg_str = "avg {:.1f}".format(avg_price)
    min_str = "min {:.1f}".format(attrs["min"])
    max_str = "max {:.1f}".format(attrs["max"])

    display.set_pen(C_AXIS)
    display.text(avg_str, 12,  88, scale=2)
    display.set_pen(C_PRICE_LOW)
    display.text(min_str, 150, 88, scale=2)
    display.set_pen(C_PRICE_HIGH)
    display.text(max_str, 300, 88, scale=2)

    # -----------------------------------------------------------------------
    # Chart — grid lines
    # -----------------------------------------------------------------------
    NUM_GRID = 5
    for i in range(NUM_GRID + 1):
        gy  = CY + int(i * CH / NUM_GRID)
        gv  = chart_max - i * (chart_max - chart_min) / NUM_GRID
        display.set_pen(C_GRID)
        display.line(CX, gy, CX + CW, gy)
        display.set_pen(C_AXIS)
        lbl = "{:.0f}".format(gv)
        display.text(lbl, CX - len(lbl) * 6 - 4, gy - 4, scale=1)

    # -----------------------------------------------------------------------
    # Chart — bars (color-coded by price tier)
    # -----------------------------------------------------------------------
    for i, v in enumerate(chart_vals):
        bx = CX + int(i * (bar_w + bar_gap))
        by = val_y(v)
        bh = base_y - by
        display.set_pen(price_color(v))
        display.rectangle(int(bx), int(by), int(bar_w), int(bh))

    # -----------------------------------------------------------------------
    # Chart — "now" vertical marker (blue line)
    # -----------------------------------------------------------------------
    if 0 <= now_offset < len(chart_vals):
        now_x = CX + int(now_offset * (bar_w + bar_gap) + bar_w / 2)
        display.set_pen(C_NOW_LINE)
        for dx in [-1, 0, 1]:
            display.line(now_x + dx, CY, now_x + dx, base_y)

    # -----------------------------------------------------------------------
    # Chart — X-axis hour labels (every hour)
    # -----------------------------------------------------------------------
    display.set_pen(C_AXIS)
    for i, s in enumerate(chart_data):
        sh, sm = parse_hm(s["start"])
        if sm == 0:
            lx = CX + int(i * (bar_w + bar_gap))
            display.text("{:02d}".format(sh), int(lx), base_y + 4, scale=1)

    # -----------------------------------------------------------------------
    # Chart — axis lines
    # -----------------------------------------------------------------------
    display.set_pen(C_AXIS)
    display.line(CX, CY,      CX,      base_y)
    display.line(CX, base_y,  CX + CW, base_y)

    # -----------------------------------------------------------------------
    # Push to screen
    # -----------------------------------------------------------------------
    presto.update()


# ---------------------------------------------------------------------------
# Error screen
# ---------------------------------------------------------------------------
def draw_error(msg):
    display.set_pen(C_BG)
    display.clear()
    display.set_pen(C_PRICE_HIGH)
    display.text("Error:", 20, 20, scale=2)
    display.set_pen(C_WHITE)
    for i, chunk in enumerate([msg[j:j+38] for j in range(0, len(msg), 38)]):
        display.text(chunk, 20, 60 + i * 20, scale=1)
    presto.update()


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
draw_error("Connecting to WiFi...")

if not connect_wifi():
    draw_error("WiFi failed. Check secrets.py")
else:
    draw_error("Syncing time via NTP...")
    if not sync_ntp():
        draw_error("NTP sync failed - time may be wrong")
        time.sleep(3)

    cached_data      = None
    last_fetch_time  = -REFRESH_SECS   # force immediate fetch on first iteration
    screen_on        = True            # tracks current backlight state
    woke_at          = time.time()     # treat boot as a touch-wake so quiet hours respect WAKE_DURATION

    set_backlight(True)
    touch = presto.touch   # FT6236 object, polled each iteration

    while True:
        now_ticks      = time.time()
        now_h, _now_m  = get_local_time_hm()
        quiet          = in_quiet_hours(now_h)

        # --- Touch detection (always poll, even when screen is off) -----------
        touch.poll()
        if touch.state:
            if quiet:
                # Wake the screen on touch during quiet hours
                set_backlight(True)
                screen_on = True
                woke_at   = now_ticks

        # --- Decide whether screen should be on --------------------------------
        if quiet:
            if screen_on:
                if woke_at is None:
                    # Quiet hours just started (no touch-wake active) — turn off immediately
                    set_backlight(False)
                    screen_on = False
                elif now_ticks - woke_at >= WAKE_DURATION:
                    # Touch-wake timer has expired — turn off again
                    set_backlight(False)
                    screen_on = False
                    woke_at = None
        else:
            # Outside quiet hours: always on
            if not screen_on:
                set_backlight(True)
                screen_on = True
            woke_at = None   # reset so a leftover timer doesn't interfere

        # --- Fetch new data from HA every 15 minutes --------------------------
        if now_ticks - last_fetch_time >= REFRESH_SECS:
            try:
                cached_data     = fetch_nordpool()
                last_fetch_time = now_ticks
            except Exception as e:
                if screen_on:
                    draw_error(str(e))
                time.sleep(10)
                continue

        # --- Redraw (only when screen is on) -----------------------------------
        if screen_on and cached_data is not None:
            try:
                draw_dashboard(cached_data)
            except Exception as e:
                draw_error(str(e))

        # Sleep until the next whole minute boundary (keeps clock accurate)
        # The now-line snaps to 15-min quarters automatically on each redraw
        t = time.gmtime()
        seconds_past_minute = t[5]   # tm_sec
        sleep_secs = 60 - seconds_past_minute
        time.sleep(sleep_secs if sleep_secs > 0 else 60)
