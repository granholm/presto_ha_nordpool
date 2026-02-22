# Pimoroni Presto Nordpool Energy Price Dashboard

<img width="380" height="402" alt="image" src="https://github.com/user-attachments/assets/50e681ee-80ed-4ea3-a0a1-3b66fc660d3a" />



A real-time electricity price dashboard for the [Pimoroni Presto](https://shop.pimoroni.com/products/presto), powered by the [Nordpool integration](https://github.com/custom-components/nordpool) for Home Assistant.

## Features

- **Large current price** display, colour-coded by tier (green / yellow / red)
- **Daily stats** — today's average, minimum, and maximum prices
- **Bar chart** showing 1 hour of history and 5 hours ahead, in 15-minute slots
- **Blue "now" marker** that snaps to the current 15-minute slot and moves forward every 15 minutes
- **NTP-synced clock** that updates every minute, with configurable UTC offset for your timezone
- **Night mode** — display turns off during configurable quiet hours and wakes on touch for a configurable duration

## Requirements

### Hardware
- [Pimoroni Presto](https://shop.pimoroni.com/products/presto)

### Software
- [Pimoroni MicroPython](https://github.com/pimoroni/presto/releases) (the Presto-specific build)
- [Home Assistant](https://www.home-assistant.io/) with the [Nordpool custom integration](https://github.com/custom-components/nordpool) installed and configured

## Files

| File | Description |
|------|-------------|
| `dashboard.py` | Main application — copy to `main.py` on the Presto |
| `secrets.py` | Your personal config (WiFi, HA token, timezone, night mode) |

## Setup

**1. Install the Nordpool integration in Home Assistant**

Follow the [nordpool integration instructions](https://github.com/custom-components/nordpool). Once installed, your sensor will be available as `sensor.nordpool` (the default assumed by this app).

**2. Create a Long-Lived Access Token in Home Assistant**

Go to your HA profile → *Long-Lived Access Tokens* → create one and copy it.

**3. Configure `secrets.py`**

```python
WIFI_SSID     = "your_wifi_ssid"
WIFI_PASSWORD = "your_wifi_password"

HA_HOST       = "http://192.168.x.x:8123"  # Your HA URL, no trailing slash
HA_TOKEN      = "your_long_lived_access_token"

# UTC offset in hours — update manually when clocks change (no DST handling)
# EET (Finland standard):  2
# EEST (Finland summer):   3
# CET (Central Europe):    1
# CEST (Central Europe summer): 2
TIMEZONE_OFFSET = 2

# Night mode
QUIET_START   = 23   # Hour to turn display off (local time, 0–23)
QUIET_END     = 7    # Hour to turn display back on (local time, 0–23)
WAKE_DURATION = 300  # Seconds to stay on after a touch during quiet hours (e.g. 300 = 5 min)
```

**4. Copy files to the Presto**

Connect the Presto via USB and copy both files using Thonny or `mpremote`:

```bash
mpremote cp secrets.py :secrets.py
mpremote cp dashboard.py :main.py
```

The device will start the dashboard automatically on next boot.

## How it works

On startup the Presto connects to WiFi, syncs its clock via NTP, then immediately fetches data from Home Assistant. From there:

- **Every minute** — the display redraws with the current time from the RTC
- **Every 15 minutes** — fresh price data is fetched from HA; the chart window shifts one bar forward and the now-marker advances to the next slot

### Colour coding

Bars and the current price are coloured by tier:

| Colour | Threshold |
|--------|-----------|
| 🟢 Green | Below 8 c/kWh |
| 🟡 Yellow | 8–15 c/kWh |
| 🔴 Red | Above 15 c/kWh |

Thresholds can be adjusted in `dashboard.py`:

```python
PRICE_LOW_THRESHOLD  = 8.0
PRICE_MID_THRESHOLD  = 15.0
```

### Night mode

When the current hour falls within the quiet window (default 23:00–07:00), the backlight is turned off completely. The main loop keeps running silently — NTP stays synced and data keeps fetching.

Touching the screen during quiet hours wakes the display for `WAKE_DURATION` seconds (default 5 minutes), after which it turns itself off again. Outside quiet hours the display is always on.

The quiet window wraps midnight correctly, so `QUIET_START = 23, QUIET_END = 7` works as expected. If you want a window that doesn't cross midnight (e.g. a midday nap: `QUIET_START = 13, QUIET_END = 15`) that works too.

### Timezone

MicroPython has no DST awareness, so `TIMEZONE_OFFSET` is a simple integer UTC offset that you update manually twice a year when the clocks change.

## Customisation

| Variable | Location | Description |
|----------|----------|-------------|
| `PRICE_LOW_THRESHOLD` | `dashboard.py` | Green/yellow boundary (c/kWh) |
| `PRICE_MID_THRESHOLD` | `dashboard.py` | Yellow/red boundary (c/kWh) |
| `CHART_SLOTS_PAST` | `dashboard.py` | Bars to show before now (each = 15 min) |
| `CHART_SLOTS_FUTURE` | `dashboard.py` | Bars to show after now (each = 15 min) |
| `SENSOR_ID` | `dashboard.py` | HA entity ID if yours differs from `sensor.nordpool` |
| `TIMEZONE_OFFSET` | `secrets.py` | UTC offset in hours |
| `QUIET_START` / `QUIET_END` | `secrets.py` | Night mode window (hours, local time) |
| `WAKE_DURATION` | `secrets.py` | Touch-wake duration in seconds |

## Troubleshooting

**"WiFi failed"** — check `WIFI_SSID` and `WIFI_PASSWORD` in `secrets.py`.

**"NTP sync failed"** — the device will continue with a potentially wrong clock and retry on the next boot. Check that your network allows outbound UDP on port 123.

**HTTP errors from HA** — verify `HA_HOST` includes the scheme and port (`http://192.168.x.x:8123`) and that your `HA_TOKEN` is valid and hasn't been revoked.

**Price shows stale data** — `raw_tomorrow` prices are only published by Nordpool in the early afternoon. Before that, the chart will only show today's slots.

**Clock is off by an hour** — your DST offset has changed. Update `TIMEZONE_OFFSET` in `secrets.py`.
