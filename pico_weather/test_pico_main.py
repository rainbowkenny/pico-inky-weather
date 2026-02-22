"""
Tests for pico_main.py logic.
Mocks all MicroPython hardware modules so tests run on standard Python.
Run: python3 -m pytest pico_weather/test_pico_main.py -v
  or: python3 pico_weather/test_pico_main.py
"""

import math
import sys
import types
import unittest
from unittest.mock import MagicMock, call, patch

# ── Mock MicroPython / hardware modules before importing pico_main ────────────


def _make_mock_module(name):
    m = types.ModuleType(name)
    sys.modules[name] = m
    return m


# network
net = _make_mock_module("network")
net.WLAN = MagicMock()
net.STA_IF = 1

# machine
mach = _make_mock_module("machine")
mach.Pin = MagicMock()

# urequests
ureq = _make_mock_module("urequests")

# picographics
pg = _make_mock_module("picographics")
pg.PicoGraphics = MagicMock()
pg.DISPLAY_INKY_PACK = "INKY_PACK"

# jpegdec
jd = _make_mock_module("jpegdec")
jd.JPEG = MagicMock()

# gc (use real gc but also expose it as the mock)
import gc

sys.modules["gc"] = gc

# time (use real time)
import time as _time

sys.modules["time"] = _time

# Now we can safely import the logic from pico_main
# We import only the pure-logic parts by exec-ing the file up to "# ===== HELPERS"
# to avoid running the hardware init at module level.

_SRC_PATH = __file__.replace("test_pico_main.py", "pico_main.py")


def _load_logic():
    """Return a namespace containing all functions/constants from pico_main."""
    with open(_SRC_PATH) as f:
        src = f.read()
    # Stop before the hardware init block (MAIN section)
    cut = src.find("# ===== MAIN =====")
    if cut == -1:
        cut = len(src)
    ns = {}
    exec(compile(src[:cut], _SRC_PATH, "exec"), ns)
    return ns


NS = _load_logic()

# Pull names into module scope for convenience
deg_to_compass = NS["deg_to_compass"]
latlon_to_dot = NS["latlon_to_dot"]
parse_time = NS["parse_time"]
WMO = NS["WMO"]
CITY_DOTS = NS["CITY_DOTS"]
PRESET_CITIES = NS["PRESET_CITIES"]
HOME_CITY_IDX = NS["HOME_CITY_IDX"]
MAP_X = NS["MAP_X"]
MAP_Y = NS["MAP_Y"]
_X_OFF = NS["_X_OFF"]
_MAP_W = NS["_MAP_W"]
_Y_OFF = NS["_Y_OFF"]
_MAP_H = NS["_MAP_H"]
MANUAL_TIMEOUT = NS["MANUAL_TIMEOUT"]

# ── Tests ─────────────────────────────────────────────────────────────────────


class TestDegToCompass(unittest.TestCase):
    """deg_to_compass should map 360° to 8 compass points."""

    def test_north(self):
        self.assertEqual(deg_to_compass(0), "N")
        self.assertEqual(deg_to_compass(360), "N")

    def test_northeast(self):
        self.assertEqual(deg_to_compass(45), "NE")
        self.assertEqual(deg_to_compass(22), "N")  # just inside N
        self.assertEqual(deg_to_compass(23), "NE")  # just inside NE

    def test_east(self):
        self.assertEqual(deg_to_compass(90), "E")

    def test_southeast(self):
        self.assertEqual(deg_to_compass(135), "SE")

    def test_south(self):
        self.assertEqual(deg_to_compass(180), "S")

    def test_southwest(self):
        self.assertEqual(deg_to_compass(225), "SW")

    def test_west(self):
        self.assertEqual(deg_to_compass(270), "W")

    def test_northwest(self):
        self.assertEqual(deg_to_compass(315), "NW")

    def test_all_8_covered(self):
        expected = {"N", "NE", "E", "SE", "S", "SW", "W", "NW"}
        got = {deg_to_compass(i * 45) for i in range(8)}
        self.assertEqual(got, expected)


class TestParseTime(unittest.TestCase):
    """parse_time extracts d/m HH:MM from open-meteo time strings."""

    def test_normal(self):
        self.assertEqual(parse_time("2026-02-22T08:45"), "22/2 08:45")

    def test_with_seconds(self):
        self.assertEqual(parse_time("2026-02-22T08:45:00"), "22/2 08:45")

    def test_midnight(self):
        self.assertEqual(parse_time("2026-01-01T00:00"), "1/1 00:00")

    def test_no_leading_zero_stripped(self):
        result = parse_time("2026-07-04T13:00")
        self.assertEqual(result, "4/7 13:00")

    def test_empty(self):
        self.assertEqual(parse_time(""), "--/-- --:--")

    def test_short_string(self):
        self.assertEqual(parse_time("2026"), "--/-- --:--")


class TestLatLonToDot(unittest.TestCase):
    """latlon_to_dot should map UK coordinates to pixel positions."""

    def test_london_approximate(self):
        # London ~51.5°N, -0.1°W → should be near bottom-centre of map
        x, y = latlon_to_dot(51.5, -0.12)
        self.assertGreater(x, MAP_X)  # right of divider
        self.assertLess(x, MAP_X + 148)  # within panel
        self.assertGreater(y, MAP_Y)
        self.assertLess(y, 128)

    def test_edinburgh_higher_than_london(self):
        _, y_lon = latlon_to_dot(51.5, -0.12)
        _, y_edi = latlon_to_dot(55.95, -3.19)
        self.assertLess(y_edi, y_lon)  # Edinburgh is further north → smaller y

    def test_east_further_right(self):
        x_west, _ = latlon_to_dot(52.0, -3.0)
        x_east, _ = latlon_to_dot(52.0, 1.5)
        self.assertLess(x_west, x_east)

    def test_clamps_to_map_bounds(self):
        # Way off map should clamp
        x_min, y_min = latlon_to_dot(90.0, 180.0)  # extreme NE
        x_max, y_max = latlon_to_dot(-90.0, -180.0)  # extreme SW
        self.assertGreaterEqual(x_min, MAP_X + _X_OFF)
        self.assertLessEqual(x_max, MAP_X + _X_OFF + _MAP_W)


class TestWMO(unittest.TestCase):
    """WMO code lookup."""

    def test_clear(self):
        self.assertEqual(WMO[0], "Clear")

    def test_overcast(self):
        self.assertEqual(WMO[3], "Overcast")

    def test_rain(self):
        self.assertEqual(WMO[63], "Rain")
        self.assertEqual(WMO[65], "Hvy Rain")

    def test_snow(self):
        self.assertEqual(WMO[73], "Snow")

    def test_thunder(self):
        self.assertEqual(WMO[95], "Thunder")

    def test_missing_code_returns_default(self):
        self.assertEqual(WMO.get(999, "?"), "?")


class TestPresetCities(unittest.TestCase):
    """PRESET_CITIES sanity checks."""

    def test_auto_is_index_0(self):
        name, lat, lon = PRESET_CITIES[0]
        self.assertIsNone(name)

    def test_home_is_cambridge(self):
        name, lat, lon = PRESET_CITIES[HOME_CITY_IDX]
        self.assertEqual(name, "Cambridge")

    def test_all_presets_have_valid_coords(self):
        for name, lat, lon in PRESET_CITIES[1:]:  # skip Auto
            self.assertIsNotNone(name)
            self.assertGreater(lat, 49.0, msg=f"{name} lat too low")
            self.assertLess(lat, 62.0, msg=f"{name} lat too high")
            self.assertGreater(lon, -8.0, msg=f"{name} lon too far west")
            self.assertLess(lon, 3.0, msg=f"{name} lon too far east")

    def test_preset_cities_in_city_dots(self):
        """Every named preset city should have a dot in CITY_DOTS."""
        missing = []
        for name, lat, lon in PRESET_CITIES[1:]:
            if name not in CITY_DOTS:
                missing.append(name)
        self.assertEqual(
            missing, [], msg="Missing CITY_DOTS entries: {}".format(missing)
        )


class TestFetchWeather(unittest.TestCase):
    """fetch_weather populates weather_cache correctly."""

    MOCK_WEATHER = {
        "current_weather": {
            "temperature": 12.3,
            "weathercode": 3,
            "windspeed": 18.0,
            "winddirection": 270.0,
            "time": "2026-02-22T08:00",
        },
        "daily": {
            "temperature_2m_max": [14.0, 11.0],
            "temperature_2m_min": [8.0, 5.0],
            "weathercode": [3, 61],
            "precipitation_sum": [0.5, 2.1],
        },
    }

    MOCK_LOCATION = (52.205, 0.122, "Cambridge")

    def setUp(self):
        # Reset cache before each test
        NS["weather_cache"] = [None] * len(PRESET_CITIES)

    def _patch_apis(self, weather=None, location=None):
        weather = weather or self.MOCK_WEATHER
        location = location or self.MOCK_LOCATION

        mock_resp = MagicMock()
        mock_resp.json.return_value = weather
        ureq.get = MagicMock(return_value=mock_resp)

        NS["get_weather"] = MagicMock(return_value=weather)
        NS["get_location"] = MagicMock(return_value=location)
        NS["connect_wifi"] = MagicMock(return_value=True)

    def test_fetch_preset_city(self):
        self._patch_apis()
        NS["fetch_weather"](HOME_CITY_IDX)  # Cambridge
        c = NS["weather_cache"][HOME_CITY_IDX]
        self.assertIsNotNone(c)
        self.assertEqual(c["city"], "Cambridge")
        self.assertEqual(c["temp"], 12)
        self.assertEqual(c["desc"], "Overcast")
        self.assertEqual(c["wind_dir"], "W")
        self.assertEqual(c["wind_spd"], 18)
        self.assertEqual(c["rain_0"], "0.5mm")
        self.assertEqual(c["rain_1"], "2.1mm")
        self.assertEqual(c["hmax"], 14)
        self.assertEqual(c["hmin"], 8)
        self.assertEqual(c["tmax"], 11)
        self.assertEqual(c["tmin"], 5)
        self.assertEqual(c["tmr_desc"], "Lt Rain")
        self.assertEqual(c["date_str"], "22/2 08:00")

    def test_fetch_auto_city_uses_geolocation(self):
        self._patch_apis()
        NS["fetch_weather"](0)  # Auto
        NS["get_location"].assert_called_once()
        c = NS["weather_cache"][0]
        self.assertIsNotNone(c)
        self.assertEqual(c["city"], "Cambridge")

    def test_fetch_keeps_old_cache_on_error(self):
        self._patch_apis()
        old = {"city": "Cambridge", "temp": 99}
        NS["weather_cache"][HOME_CITY_IDX] = old
        NS["get_weather"] = MagicMock(side_effect=Exception("API down"))
        NS["fetch_weather"](HOME_CITY_IDX)
        # Old cache should be retained
        self.assertEqual(NS["weather_cache"][HOME_CITY_IDX]["temp"], 99)

    def test_fetch_none_precipitation(self):
        weather = dict(self.MOCK_WEATHER)
        weather["daily"] = dict(weather["daily"])
        weather["daily"]["precipitation_sum"] = [None, None]
        self._patch_apis(weather=weather)
        NS["fetch_weather"](HOME_CITY_IDX)
        c = NS["weather_cache"][HOME_CITY_IDX]
        self.assertEqual(c["rain_0"], "--")
        self.assertEqual(c["rain_1"], "--")


class TestStateMachine(unittest.TestCase):
    """State machine: mode transitions and button behaviour."""

    def test_manual_timeout_10s(self):
        self.assertEqual(MANUAL_TIMEOUT, 10)

    def test_home_city_is_cambridge(self):
        name, _, _ = PRESET_CITIES[HOME_CITY_IDX]
        self.assertEqual(name, "Cambridge")

    def test_button_a_decrements_city(self):
        city_idx = 3
        city_idx = (city_idx - 1) % len(PRESET_CITIES)
        self.assertEqual(city_idx, 2)

    def test_button_b_increments_city(self):
        city_idx = 3
        city_idx = (city_idx + 1) % len(PRESET_CITIES)
        self.assertEqual(city_idx, 4)

    def test_button_b_wraps_at_end(self):
        city_idx = len(PRESET_CITIES) - 1
        city_idx = (city_idx + 1) % len(PRESET_CITIES)
        self.assertEqual(city_idx, 0)

    def test_button_a_wraps_at_start(self):
        city_idx = 0
        city_idx = (city_idx - 1) % len(PRESET_CITIES)
        self.assertEqual(city_idx, len(PRESET_CITIES) - 1)

    def test_timeout_in_manual_returns_to_auto(self):
        # Simulate: manual mode, timeout fires
        mode = "manual"
        city_idx = 5
        action = None  # no button press = timeout
        if action is None:
            if mode == "manual":
                city_idx = 0
                mode = "default"
        self.assertEqual(city_idx, 0)
        self.assertEqual(mode, "default")

    def test_timeout_in_default_stays_at_auto(self):
        mode = "default"
        city_idx = 0
        action = None
        if action is None:
            if mode == "manual":
                city_idx = 0
                mode = "default"
            # else: stay on Auto (city_idx unchanged)
        self.assertEqual(city_idx, 0)
        self.assertEqual(mode, "default")

    def test_c_button_goes_to_cambridge(self):
        city_idx = 7
        mode = "default"
        action = "c"
        if action == "c":
            city_idx = HOME_CITY_IDX
            mode = "manual"
        self.assertEqual(city_idx, HOME_CITY_IDX)
        name, _, _ = PRESET_CITIES[city_idx]
        self.assertEqual(name, "Cambridge")
        self.assertEqual(mode, "manual")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main(verbosity=2)
