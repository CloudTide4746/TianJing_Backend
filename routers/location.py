"""Location info endpoint — reverse geocoding + weather + mint counter."""

from __future__ import annotations

from fastapi import APIRouter, Query

import database as db
from models import LocationInfoOut
from services.weather import get_weather, get_aqi
from services.geocode import reverse_geocode

router = APIRouter(prefix="/api/location", tags=["location"])


@router.get("/info", response_model=LocationInfoOut)
async def get_location_info(
    lat: float = Query(..., alias="lat"),
    lng: float = Query(..., alias="lng"),
):
    # Fetch geocode, weather, AQI in parallel
    loc = await reverse_geocode(lat, lng)
    weather = await get_weather(lat, lng)
    aqi_data = await get_aqi(lat, lng)

    # Read counter without incrementing (preview only)
    counter = db.get_or_create_location_counter(lat, lng)

    # Store location metadata on counter if not yet set (no increment)
    if loc.get("location_name") and not counter.get("location_name"):
        db.update_location_counter_meta(
            lat, lng,
            location_name=loc["location_name"],
            province=loc["province"],
            district=loc["district"],
            era_label=loc["era_label"],
            location_style=loc["location_style"],
            suggested_kind=loc["suggested_kind"],
        )
        counter = db.get_or_create_location_counter(lat, lng)

    mint_number = int(counter.get("counter", 0))
    earliest = counter.get("earliest_imprint", "")

    return LocationInfoOut(
        location_name=loc["location_name"],
        province=loc["province"],
        district=loc["district"],
        era_label=loc["era_label"],
        location_style=loc["location_style"],
        suggested_kind=loc["suggested_kind"],
        mint_number=mint_number + 1,  # next mint number
        earliest_imprint=earliest or "",
        weather_condition=weather["weather_condition"],
        temperature=weather["temperature"],
        wind_direction=weather["wind_direction"],
        wind_level=weather["wind_level"],
        aqi=aqi_data["aqi"],
        aqi_level=aqi_data["aqi_level"],
    )
