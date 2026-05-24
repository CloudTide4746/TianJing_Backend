"""Reverse geocoding via Nominatim (free, no API key)."""

from __future__ import annotations

import httpx

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"


# Location style mapping based on keywords in address
LOCATION_STYLE_KEYWORDS: dict[str, tuple[str, str, str]] = {
    "museum": ("terracotta", "ruin", "博物馆"),
    "temple": ("terracotta", "ruin", "古寺"),
    "pagoda": ("terracotta", "ruin", "古塔"),
    "tower": ("cyber", "crystal", "现代建筑"),
    "city": ("cyber", "crystal", "都市地标"),
    "wall": ("terracotta", "ruin", "古城墙"),
    "tomb": ("terracotta", "ruin", "古墓"),
    "cave": ("mural", "ruin", "石窟"),
    "lake": ("ink", "message", "自然景观"),
    "park": ("ink", "message", "自然景观"),
    "mountain": ("ink", "message", "山岳景观"),
    "river": ("ink", "message", "河流景观"),
    "garden": ("ink", "message", "园林景观"),
    "bridge": ("ink", "message", "古桥"),
    "palace": ("terracotta", "ruin", "宫殿遗址"),
    "ruins": ("terracotta", "ruin", "历史遗址"),
    "mosque": ("mural", "ruin", "宗教建筑"),
    "cathedral": ("mural", "ruin", "宗教建筑"),
    "church": ("mural", "ruin", "宗教建筑"),
    "market": ("cyber", "crystal", "市集"),
    "street": ("cyber", "crystal", "街区"),
    "square": ("cyber", "crystal", "广场"),
    "station": ("cyber", "crystal", "交通枢纽"),
}


async def reverse_geocode(lat: float, lng: float) -> dict:
    """Reverse geocode coordinates to get location name and metadata."""
    params = {
        "lat": lat,
        "lon": lng,
        "format": "json",
        "accept-language": "zh",
        "zoom": 14,
    }
    headers = {
        "User-Agent": "SpacetimeArchive/1.0 (hackathon project; contact@example.com)",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(NOMINATIM_URL, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return _fallback_location(lat, lng)

    address = data.get("address", {})
    name_parts = []

    # Build location name
    for key in ("tourism", "historic", "amenity", "building", "road", "suburb"):
        val = address.get(key)
        if val:
            name_parts.append(val)
            break
    if not name_parts:
        name_parts.append(address.get("city", address.get("town", address.get("village", ""))))

    location_name = name_parts[0] if name_parts else f"{lat:.4f},{lng:.4f}"
    province = address.get("state", address.get("province", ""))
    city = address.get("city", address.get("town", address.get("county", "")))
    district = f"{province}·{city}" if province and city else province or city

    # Determine location style and era
    style, kind, era = _classify_location(address, data.get("category", ""))

    return {
        "location_name": location_name,
        "province": province or "",
        "district": district or location_name,
        "era_label": era,
        "location_style": style,
        "suggested_kind": kind,
    }


def _classify_location(address: dict, category: str) -> tuple[str, str, str]:
    """Determine visual style, collectible kind, and era label from location data."""
    # Check address fields for keywords
    for field in ("tourism", "historic", "amenity", "building", "category"):
        val = (address.get(field) or "").lower()
        for keyword, (style, kind, era) in LOCATION_STYLE_KEYWORDS.items():
            if keyword in val:
                return style, kind, era

    # Default by category
    if category in ("historic", "archaeological"):
        return "terracotta", "ruin", "历史遗址"
    if category in ("natural", "waterway"):
        return "ink", "message", "自然景观"
    if category in ("tourism", "amenity"):
        return "mural", "ruin", "人文景观"

    return "ink", "message", "自然景观"


def _fallback_location(lat: float, lng: float) -> dict:
    return {
        "location_name": f"{lat:.4f}°N {lng:.4f}°E",
        "province": "",
        "district": f"{lat:.4f}°N {lng:.4f}°E",
        "era_label": "未知地点",
        "location_style": "ink",
        "suggested_kind": "message",
    }
