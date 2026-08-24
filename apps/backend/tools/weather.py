"""Open-Meteo weather (no API key)."""
from __future__ import annotations

import httpx

WMO_RU = {
    0: "ясно",
    1: "почти ясно",
    2: "переменная облачность",
    3: "пасмурно",
    45: "туман",
    48: "изморозь",
    51: "лёгкая морось",
    53: "морось",
    55: "сильная морось",
    61: "небольшой дождь",
    63: "дождь",
    65: "сильный дождь",
    71: "небольшой снег",
    73: "снег",
    75: "сильный снег",
    80: "ливень",
    81: "ливни",
    82: "сильный ливень",
    95: "гроза",
    96: "гроза с градом",
    99: "сильная гроза с градом",
}


async def get_weather(city: str) -> str:
    query = (city or "").strip() or "Оренбург"
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            geo = await client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": query, "count": 1, "language": "ru", "format": "json"},
            )
            geo.raise_for_status()
            results = (geo.json() or {}).get("results") or []
            if not results:
                return f"Не нашла город {query}."
            place = results[0]
            lat = place["latitude"]
            lon = place["longitude"]
            label = place.get("name") or query
            country = place.get("country_code") or ""
            fc = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m,weather_code,wind_speed_10m,relative_humidity_2m",
                    "timezone": "auto",
                },
            )
            fc.raise_for_status()
            cur = (fc.json() or {}).get("current") or {}
            temp = cur.get("temperature_2m")
            code = int(cur.get("weather_code") or 0)
            wind = cur.get("wind_speed_10m")
            cond = WMO_RU.get(code, "переменная погода")
            where = f"{label}" + (f", {country}" if country else "")
            parts = [f"В {where} сейчас {cond}"]
            if temp is not None:
                parts.append(f"{round(float(temp))} градусов")
            if wind is not None:
                parts.append(f"ветер {round(float(wind))} метров в секунду")
            return ", ".join(parts) + "."
    except Exception as exc:
        return f"Не удалось получить погоду: {exc}"
