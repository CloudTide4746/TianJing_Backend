from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────

class CollectibleKind(str, Enum):
    ruin = "ruin"
    message = "message"
    crystal = "crystal"


class LocationStyleId(str, Enum):
    terracotta = "terracotta"
    ink = "ink"
    mural = "mural"
    cyber = "cyber"


class GenerationStatus(str, Enum):
    idle = "idle"
    queued = "queued"
    generating = "generating"
    complete = "complete"
    failed = "failed"


# ── Request models ─────────────────────────────────────────────

class CreateCollectibleRequest(BaseModel):
    latitude: float
    longitude: float
    message: str = ""


class GenerateRequest(BaseModel):
    pass  # trigger generation for an existing collectible


# ── Response models ─────────────────────────────────────────────

class SpacetimeAnchorOut(BaseModel):
    latitude: float
    longitude: float
    timestamp: str
    weather_condition: str
    temperature: float
    wind_direction: str
    wind_level: int
    aqi: int
    aqi_level: str
    location_name: str
    mint_number: int
    earliest_imprint: str
    golden_line: str


class CollectibleImageSetOut(BaseModel):
    hero_url: str
    thumbnail_url: str
    share_url: str
    alt: str


class CollectibleShareContentOut(BaseModel):
    title: str
    caption: str
    call_to_action: str
    hashtags: list[str]


class CollectibleMetricsOut(BaseModel):
    view_count: int = 0
    share_count: int = 0
    save_count: int = 0


class GenerationPhaseOut(BaseModel):
    id: str
    label: str
    detail: str
    progress: float
    tone: str
    status: str
    duration_ms: int
    can_cancel: bool


class CollectibleOut(BaseModel):
    id: str
    slug: str
    kind: CollectibleKind
    location_style: LocationStyleId
    title: str
    subtitle: str
    short_description: str
    site_name: str
    province: str
    district: str
    era_label: str
    created_at: str
    updated_at: str
    images: CollectibleImageSetOut
    story: str
    tags: list[str]
    material_keywords: list[str]
    collector_note: Optional[str] = None
    is_favorite: bool = False
    is_featured: bool = False
    generation_status: GenerationStatus
    related_ids: list[str] = []
    metrics: CollectibleMetricsOut
    share: CollectibleShareContentOut
    anchor: SpacetimeAnchorOut


class CollectibleListItem(BaseModel):
    id: str
    kind: CollectibleKind
    location_style: LocationStyleId
    title: str
    subtitle: str
    site_name: str
    province: str
    district: str
    created_at: str
    thumbnail_url: str
    generation_status: GenerationStatus
    anchor: SpacetimeAnchorOut


class LocationInfoOut(BaseModel):
    location_name: str
    province: str
    district: str
    era_label: str
    location_style: LocationStyleId
    suggested_kind: CollectibleKind
    mint_number: int
    earliest_imprint: str
    weather_condition: str
    temperature: float
    wind_direction: str
    wind_level: int
    aqi: int
    aqi_level: str


class GenerationStatusOut(BaseModel):
    status: GenerationStatus
    phases: list[GenerationPhaseOut]
    current_phase_index: int
    redirect_collectible_id: Optional[str] = None
    error_message: Optional[str] = None


class TimelineGroup(BaseModel):
    date_label: str
    items: list[CollectibleListItem]


class MapPoint(BaseModel):
    id: str
    title: str
    latitude: float
    longitude: float
    location_style: LocationStyleId
    thumbnail_url: str
    mint_number: int


class CityAggregation(BaseModel):
    province: str
    city: str
    count: int
    thumbnail_url: str


class CollectibleListResponse(BaseModel):
    items: list[CollectibleListItem]
    total: int


class UploadResponse(BaseModel):
    collectible_id: str
    image_url: str
    anchor: SpacetimeAnchorOut
