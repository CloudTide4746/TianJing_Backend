"""Weather and AQI data via Open-Meteo (free, no API key)."""

from __future__ import annotations

import httpx

OPEN_METEO_WEATHER = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_AQI = "https://air-quality-api.open-meteo.com/v1/air-quality"


async def get_weather(lat: float, lng: float) -> dict:
    """Fetch current weather conditions from Open-Meteo."""
    params = {
        "latitude": lat,
        "longitude": lng,
        "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,wind_direction_10m",
        "timezone": "Asia/Shanghai",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(OPEN_METEO_WEATHER, params=params)
        resp.raise_for_status()
        data = resp.json()

    current = data.get("current", {})
    weather_code = current.get("weather_code", 0)
    temp = current.get("temperature_2m", 20)
    wind_speed = current.get("wind_speed_10m", 0)
    wind_dir = current.get("wind_direction_10m", 0)

    return {
        "weather_condition": _weather_code_to_text(weather_code),
        "temperature": temp,
        "wind_direction": _wind_dir_to_text(wind_dir),
        "wind_level": _wind_speed_to_level(wind_speed),
    }


async def get_aqi(lat: float, lng: float) -> dict:
    """Fetch current AQI from Open-Meteo Air Quality API."""
    params = {
        "latitude": lat,
        "longitude": lng,
        "current": "european_aqi,pm2_5,pm10",
        "timezone": "Asia/Shanghai",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(OPEN_METEO_AQI, params=params)
        resp.raise_for_status()
        data = resp.json()

    current = data.get("current", {})
    european_aqi = current.get("european_aqi", 1)
    pm25 = current.get("pm2_5", 0)

    return {
        "aqi": _european_to_cn_aqi(european_aqi),
        "aqi_level": _aqi_to_level(_european_to_cn_aqi(european_aqi)),
        "pm25": pm25,
    }


def _weather_code_to_text(code: int) -> str:
    wmo: dict[int, str] = {
        0: "晴", 1: "晴", 2: "多云", 3: "阴",
        45: "雾", 48: "雾凇",
        51: "小雨", 53: "中雨", 55: "大雨",
        61: "小雨", 63: "中雨", 65: "大雨",
        71: "小雪", 73: "中雪", 75: "大雪",
        80: "阵雨", 81: "中阵雨", 82: "大阵雨",
        95: "雷暴", 96: "冰雹雷暴", 99: "冰雹雷暴",
    }
    return wmo.get(code, "多云")


def _wind_dir_to_text(degrees: float) -> str:
    dirs = ["北", "东北", "东", "东南", "南", "西南", "西", "西北"]
    idx = round(degrees / 45) % 8
    return dirs[idx]


def _wind_speed_to_level(speed_ms: float) -> int:
    if speed_ms < 0.3:
        return 0
    if speed_ms < 1.6:
        return 1
    if speed_ms < 3.4:
        return 2
    if speed_ms < 5.5:
        return 3
    if speed_ms < 8.0:
        return 4
    if speed_ms < 10.8:
        return 5
    if speed_ms < 13.9:
        return 6
    return 7


def _european_to_cn_aqi(eu_aqi: float) -> int:
    mapping = {1: 25, 2: 50, 3: 100, 4: 150, 5: 250}
    return mapping.get(int(eu_aqi), 50)


def _aqi_to_level(aqi: int) -> str:
    if aqi <= 50:
        return "优"
    if aqi <= 100:
        return "良"
    if aqi <= 150:
        return "轻度污染"
    if aqi <= 200:
        return "中度污染"
    return "重度污染"
