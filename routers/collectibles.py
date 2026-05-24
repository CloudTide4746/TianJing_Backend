"""Collectible CRUD + list views (timeline, map, cities)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

import database as db
from models import (
    CityAggregation,
    CollectibleListItem,
    CollectibleListResponse,
    CollectibleOut,
    MapPoint,
    SpacetimeAnchorOut,
    TimelineGroup,
    CollectibleImageSetOut, CollectibleShareContentOut, CollectibleMetricsOut,
)

router = APIRouter(prefix="/api/collectibles", tags=["collectibles"])


def _to_collectible_out(data: dict) -> CollectibleOut:
    return CollectibleOut(
        id=data["id"],
        slug=data.get("slug", ""),
        kind=data.get("kind", "ruin"),
        location_style=data.get("location_style", "terracotta"),
        title=data.get("title", ""),
        subtitle=data.get("subtitle", ""),
        short_description=data.get("short_description", ""),
        site_name=data.get("site_name", ""),
        province=data.get("province", ""),
        district=data.get("district", ""),
        era_label=data.get("era_label", ""),
        created_at=data.get("created_at", ""),
        updated_at=data.get("updated_at", ""),
        images=CollectibleImageSetOut(
            hero_url=data.get("hero_url", ""),
            thumbnail_url=data.get("thumbnail_url", ""),
            share_url=data.get("share_url", ""),
            alt=data.get("image_alt", ""),
        ),
        story=data.get("story", ""),
        tags=data.get("tags", []),
        material_keywords=data.get("material_keywords", []),
        collector_note=data.get("collector_note"),
        is_favorite=bool(data.get("is_favorite", False)),
        is_featured=bool(data.get("is_featured", False)),
        generation_status=data.get("generation_status", "idle"),
        related_ids=data.get("related_ids", []),
        metrics=CollectibleMetricsOut(
            view_count=data.get("view_count", 0),
            share_count=data.get("share_count", 0),
            save_count=data.get("save_count", 0),
        ),
        share=CollectibleShareContentOut(
            title=f"我在{data.get('location_name', '')}留下了第{data.get('mint_number', 0)}个刻迹",
            caption=data.get("golden_line", ""),
            call_to_action=data.get("call_to_action") or f"打开时空卡，见证你在{data.get('location_name', '')}的坐标被存档。",
            hashtags=[f"#刻迹", f"#{data.get('site_name', '')}"],
        ),
        anchor=SpacetimeAnchorOut(
            latitude=data.get("latitude", 0),
            longitude=data.get("longitude", 0),
            timestamp=data.get("timestamp", ""),
            weather_condition=data.get("weather_condition", ""),
            temperature=data.get("temperature", 0),
            wind_direction=data.get("wind_direction", ""),
            wind_level=data.get("wind_level", 0),
            aqi=data.get("aqi", 0),
            aqi_level=data.get("aqi_level", ""),
            location_name=data.get("location_name", ""),
            mint_number=data.get("mint_number", 0),
            earliest_imprint=data.get("earliest_imprint", ""),
            golden_line=data.get("golden_line", ""),
        ),
    )


def _to_list_item(data: dict) -> CollectibleListItem:
    return CollectibleListItem(
        id=data["id"],
        kind=data.get("kind", "ruin"),
        location_style=data.get("location_style", "terracotta"),
        title=data.get("title", ""),
        subtitle=data.get("subtitle", ""),
        site_name=data.get("site_name", ""),
        province=data.get("province", ""),
        district=data.get("district", ""),
        created_at=data.get("created_at", ""),
        thumbnail_url=data.get("thumbnail_url", ""),
        generation_status=data.get("generation_status", "idle"),
        anchor=SpacetimeAnchorOut(
            latitude=data.get("latitude", 0),
            longitude=data.get("longitude", 0),
            timestamp=data.get("timestamp", ""),
            weather_condition=data.get("weather_condition", ""),
            temperature=data.get("temperature", 0),
            wind_direction=data.get("wind_direction", ""),
            wind_level=data.get("wind_level", 0),
            aqi=data.get("aqi", 0),
            aqi_level=data.get("aqi_level", ""),
            location_name=data.get("location_name", ""),
            mint_number=data.get("mint_number", 0),
            earliest_imprint=data.get("earliest_imprint", ""),
            golden_line=data.get("golden_line", ""),
        ),
    )


@router.get("/", response_model=CollectibleListResponse)
def list_collectibles(
    kind: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    sort: str = Query("newest"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    items = db.list_collectibles(kind=kind, status=status, sort=sort, limit=limit, offset=offset)
    total = db.count_collectibles(kind=kind, status=status)
    return CollectibleListResponse(
        items=[_to_list_item(it) for it in items],
        total=total,
    )


@router.get("/timeline", response_model=list[TimelineGroup])
def get_timeline():
    items = db.list_collectibles(sort="newest", limit=200)
    groups: dict[str, list[CollectibleListItem]] = {}
    for item in items:
        try:
            dt = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
            label = f"{dt.year}年{dt.month}月"
        except Exception:
            label = "未知时间"
        groups.setdefault(label, []).append(_to_list_item(item))
    return [
        TimelineGroup(date_label=label, items=group_items)
        for label, group_items in groups.items()
    ]


@router.get("/map", response_model=list[MapPoint])
def get_map_points():
    items = db.list_collectibles(sort="newest", limit=200)
    return [
        MapPoint(
            id=it["id"],
            title=it.get("location_name", it.get("title", "")),
            latitude=it.get("latitude", 0),
            longitude=it.get("longitude", 0),
            location_style=it.get("location_style", "terracotta"),
            thumbnail_url=it.get("thumbnail_url", ""),
            mint_number=it.get("mint_number", 0),
        )
        for it in items
        if it.get("latitude") and it.get("longitude")
    ]


@router.get("/cities", response_model=list[CityAggregation])
def get_cities():
    items = db.list_collectibles(sort="newest", limit=500)
    cities: dict[str, dict] = {}
    for it in items:
        city_key = f"{it.get('province', '')}-{it.get('district', '')}"
        if city_key not in cities:
            cities[city_key] = {
                "province": it.get("province", ""),
                "city": it.get("district", it.get("location_name", "")),
                "count": 0,
                "thumbnail_url": it.get("thumbnail_url", ""),
            }
        cities[city_key]["count"] += 1
        if not cities[city_key]["thumbnail_url"] and it.get("thumbnail_url"):
            cities[city_key]["thumbnail_url"] = it["thumbnail_url"]
    return [
        CityAggregation(**v) for v in sorted(cities.values(), key=lambda x: -x["count"])
    ]


@router.get("/{collectible_id}", response_model=CollectibleOut)
def get_collectible(collectible_id: str):
    item = db.get_collectible_by_id(collectible_id)
    if not item:
        raise HTTPException(status_code=404, detail="刻迹不存在")
    # Increment view count without bumping updated_at
    db.increment_view_count(collectible_id)
    item["view_count"] = item.get("view_count", 0) + 1
    return _to_collectible_out(item)


@router.patch("/{collectible_id}/favorite")
def toggle_favorite(collectible_id: str):
    result = db.toggle_favorite(collectible_id)
    if result is None:
        raise HTTPException(status_code=404, detail="刻迹不存在")
    return {"ok": True, "is_favorite": result}


@router.delete("/{collectible_id}")
def delete_collectible(collectible_id: str):
    if not db.delete_collectible(collectible_id):
        raise HTTPException(status_code=404, detail="刻迹不存在")
    return {"ok": True}
