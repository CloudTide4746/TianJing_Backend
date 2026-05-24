"""Collectible generation — trigger creation + status polling."""

from __future__ import annotations

import asyncio
import base64
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException

import database as db
from models import (
    CollectibleKind,
    GenerationPhaseOut,
    GenerationStatus,
    GenerationStatusOut,
    LocationStyleId,
    UploadResponse,
    SpacetimeAnchorOut,
)
from services.weather import get_weather, get_aqi
from services.geocode import reverse_geocode
from services.image_gen import generate_collectible_image, convert_upload_to_png
from services.golden_line import generate_golden_line
from services.ai_enrich import enrich_spacetime_imprint

router = APIRouter(prefix="/api/generate", tags=["generate"])

UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# In-memory generation state (for polling)
_generation_states: dict[str, dict] = {}

GENERATION_PHASES = [
    {"id": "queued", "label": "锚定时空坐标", "detail": "系统正在锁定GPS、时间戳与气象数据，建立不可篡改的时空锚点。", "progress": 0.08, "tone": "textSecondary", "status": "queued", "duration_ms": 800, "can_cancel": True},
    {"id": "analyze", "label": "识别地点气质", "detail": "AI 正在分析地点类型、地貌特征与人文属性，确定视觉风格。", "progress": 0.24, "tone": "gold", "status": "generating", "duration_ms": 1400, "can_cancel": True},
    {"id": "restore", "label": "生成风格化图像", "detail": "根据地点气质与照片内容，生成陶土/水墨/壁画/赛博风格的藏品图。", "progress": 0.48, "tone": "gold", "status": "generating", "duration_ms": 5000, "can_cancel": True},
    {"id": "compose", "label": "铸造时空卡面", "detail": "将坐标、天气、计数器与风格化图像融合为一张完整的刻迹卡。", "progress": 0.72, "tone": "success", "status": "generating", "duration_ms": 2000, "can_cancel": False},
    {"id": "seal", "label": "封印金句", "detail": "AI 基于地点与时间生成一行独属于此刻的金句，写入卡面底部。", "progress": 0.92, "tone": "success", "status": "generating", "duration_ms": 2000, "can_cancel": False},
    {"id": "complete", "label": "印记铸造完成", "detail": "刻迹已存入收藏库，可查看完整卡面并分享。", "progress": 1.0, "tone": "success", "status": "complete", "duration_ms": 500, "can_cancel": False},
]


@router.post("/upload", response_model=UploadResponse)
async def upload_and_create(
    imageBase64: str = Form(""),
    imageFilename: str = Form("photo.jpg"),
    latitude: float = Form(...),
    longitude: float = Form(...),
    message: str = Form(""),
    imprintTitle: str = Form(""),
    artStyle: str = Form(""),
    colorTone: str = Form(""),
    timeTexture: str = Form(""),
    customKeywords: str = Form(""),
    mood: str = Form(""),
    narrativePerspective: str = Form(""),
    detailDensity: str = Form(""),
    contrast: str = Form(""),
    grain: str = Form(""),
    season: str = Form(""),
    dynastyCollage: str = Form(""),
    aiPoetry: str = Form("false"),
):
    # Save uploaded photo from base64
    ext = os.path.splitext(imageFilename or "photo.jpg")[1] or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = UPLOAD_DIR / filename
    image_data = base64.b64decode(imageBase64)
    filepath.write_bytes(image_data)
    print(f"[DEBUG UPLOAD] Decoded base64 image: {len(image_data)} bytes")

    # DEBUG: log all received generate options
    print(f"[DEBUG UPLOAD] artStyle='{artStyle}' colorTone='{colorTone}' timeTexture='{timeTexture}'")
    print(f"[DEBUG UPLOAD] mood='{mood}' narrativePerspective='{narrativePerspective}' detailDensity='{detailDensity}'")
    print(f"[DEBUG UPLOAD] contrast='{contrast}' grain='{grain}' season='{season}' dynastyCollage='{dynastyCollage}'")
    print(f"[DEBUG UPLOAD] customKeywords='{customKeywords}' aiPoetry='{aiPoetry}'")
    print(f"[DEBUG UPLOAD] photo saved to: {filepath}")

    # Convert to PNG for reliable loading (handles HEIC, etc.)
    photo_path_for_gen = convert_upload_to_png(str(filepath))

    # Fetch location + weather + AQI
    loc = await reverse_geocode(latitude, longitude)
    weather = await get_weather(latitude, longitude)
    aqi_data = await get_aqi(latitude, longitude)

    # Increment location counter for real mint
    counter = db.increment_location_counter(
        latitude, longitude,
        location_name=loc["location_name"],
        province=loc["province"],
        district=loc["district"],
        era_label=loc["era_label"],
        location_style=loc["location_style"],
        suggested_kind=loc["suggested_kind"],
    )

    mint_number = counter.get("counter", 1)
    earliest = counter.get("earliest_imprint", "")
    location_style = loc.get("location_style", "terracotta")
    suggested_kind = loc.get("suggested_kind", "ruin")
    location_name = loc.get("location_name", f"{latitude:.4f}°N {longitude:.4f}°E")

    # ── AI enrichment (non-blocking: fallback to templates on failure) ──
    ai: dict = {}
    ai_poetry_enabled = aiPoetry.lower() == "true"
    try:
        ai = await enrich_spacetime_imprint(
            location_name=location_name,
            location_style=location_style,
            weather_condition=weather["weather_condition"],
            temperature=weather["temperature"],
            province=loc["province"],
            district=loc["district"],
            era_label=loc["era_label"],
            aqi_level=aqi_data["aqi_level"],
            wind_direction=weather["wind_direction"],
            wind_level=weather["wind_level"],
            message=message,
            ai_poetry=ai_poetry_enabled,
        )
    except Exception:
        ai = {}

    # ── Template fallbacks ──
    subtitle_templates = {
        "terracotta": f"站在{loc.get('era_label', '历史')}的遗址前",
        "ink": "每一帧都是一幅水墨",
        "mural": "飞天的线条穿过千年",
        "cyber": "城市生长的瞬间被存档",
    }
    tag_keywords = {
        "terracotta": [loc["location_name"], "遗址", loc.get("era_label", "")],
        "ink": [loc["location_name"], "山水", "水墨"],
        "mural": [loc["location_name"], "壁画", "石窟"],
        "cyber": [loc["location_name"], "都市", "霓虹"],
    }
    material_keywords_map = {
        "terracotta": ["陶土", "铜锈", "夯土"],
        "ink": ["水墨", "宣纸", "青绿"],
        "mural": ["矿物颜料", "壁画肌理", "砂岩"],
        "cyber": ["霓虹", "玻璃", "金属"],
    }

    def _fallback_story(style: str) -> str:
        stories = {
            "terracotta": f"公元前{loc.get('era_label', '古老')}的陶土在{weather['weather_condition']}天里沉默。每一道裂纹都是时间的笔迹，{location_name}见证了帝国的兴衰与泥土的不朽。",
            "ink": f"{weather['weather_condition']}日的{location_name}，山水如墨。千百年来，文人墨客在此驻足，将天地灵气收入一方画卷。",
            "mural": f"风沙掠过{location_name}的洞窟，壁画上的飞天依旧舞动。矿物颜料在{weather['weather_condition']}的光线下泛出千年之前的色泽。",
            "cyber": f"{location_name}的霓虹在{weather['weather_condition']}的夜晚闪烁。这座城市以代码和玻璃为材料，不断生长出新的天际线。",
        }
        return stories.get(style, f"在{location_name}，时空在此交汇。")

    fallback_golden = generate_golden_line(
        location_name=location_name, location_style=location_style,
        weather_condition=weather["weather_condition"], temperature=weather["temperature"],
        aqi_level=aqi_data["aqi_level"], province=loc["province"],
    )

    # ── Merge: AI first, user imprintTitle overrides, NEVER use lat/lng as title ──
    # Determine the best title for the collectible
    if imprintTitle.strip():
        title = imprintTitle.strip()
    elif ai.get("title"):
        title = ai.get("title")
    else:
        # AI failed to generate a title, build one from context — never use raw lat/lng
        weather_desc = weather["weather_condition"]
        district_or_province = loc.get("district") or loc.get("province") or "此地"
        title = f"{weather_desc}{district_or_province}·第{mint_number}印记"
    subtitle = ai.get("subtitle") or subtitle_templates.get(location_style, "刻迹")
    short_desc = ai.get("short_description") or f"{loc.get('era_label', '')} · {weather['weather_condition']} · {int(weather['temperature'])}°C"
    story = ai.get("story") or _fallback_story(location_style)
    golden_line = message or ai.get("poem_text") or ai.get("golden_line") or fallback_golden
    image_alt = ai.get("image_alt") or f"{location_name}刻迹"
    tags = ai.get("tags") or [t for t in tag_keywords.get(location_style, []) if t]
    mat_keywords = ai.get("material_keywords") or material_keywords_map.get(location_style, [])

    # Share call_to_action: when aiPoetry on → use poem as bottom text; else AI-generated CTA
    if ai_poetry_enabled and ai.get("poem_text"):
        call_to_action_val = ai["poem_text"]
    elif ai.get("call_to_action"):
        call_to_action_val = ai["call_to_action"]
    else:
        call_to_action_val = f"打开时空卡，见证你在{location_name}的坐标被存档。"

    now_iso = datetime.now(timezone.utc).isoformat()
    timestamp_display = datetime.now(timezone.utc).strftime("%Y.%m.%d %H:%M")

    collectible_id = str(uuid.uuid4())
    slug = f"{location_style}-{mint_number}-{uuid.uuid4().hex[:6]}"

    collectible_data = {
        "id": collectible_id,
        "slug": slug,
        "kind": suggested_kind,
        "location_style": location_style,
        "title": title,
        "subtitle": subtitle,
        "short_description": short_desc,
        "site_name": location_name,
        "province": loc["province"],
        "district": loc["district"],
        "era_label": loc["era_label"],
        "created_at": now_iso,
        "updated_at": now_iso,
        "hero_url": f"/uploads/{filename}",
        "thumbnail_url": f"/uploads/{filename}",
        "share_url": f"/uploads/{filename}",
        "image_alt": image_alt,
        "story": story,
        "tags": tags,
        "material_keywords": mat_keywords,
        "collector_note": message or None,
        "generation_status": "idle",
        "latitude": latitude,
        "longitude": longitude,
        "timestamp": timestamp_display,
        "weather_condition": weather["weather_condition"],
        "temperature": weather["temperature"],
        "wind_direction": weather["wind_direction"],
        "wind_level": weather["wind_level"],
        "aqi": aqi_data["aqi"],
        "aqi_level": aqi_data["aqi_level"],
        "location_name": location_name,
        "mint_number": mint_number,
        "earliest_imprint": earliest,
        "golden_line": golden_line,
        "call_to_action": call_to_action_val,
    }
    db.insert_collectible(collectible_data)

    # Parse generate options
    gen_opts = {
        "artStyle": artStyle,
        "colorTone": colorTone,
        "timeTexture": timeTexture,
        "customKeywords": customKeywords,
        "mood": mood,
        "narrativePerspective": narrativePerspective,
        "detailDensity": detailDensity,
        "contrast": contrast,
        "grain": grain,
        "season": season,
        "dynastyCollage": dynastyCollage,
        "aiPoetry": aiPoetry.lower() == "true",
    }

    # Trigger async generation
    asyncio.create_task(_run_generation(
        collectible_id, location_style, latitude, longitude,
        photo_path_for_gen, gen_opts, timestamp_display, mint_number,
    ))

    anchor = SpacetimeAnchorOut(
        latitude=latitude,
        longitude=longitude,
        timestamp=timestamp_display,
        weather_condition=weather["weather_condition"],
        temperature=weather["temperature"],
        wind_direction=weather["wind_direction"],
        wind_level=weather["wind_level"],
        aqi=aqi_data["aqi"],
        aqi_level=aqi_data["aqi_level"],
        location_name=location_name,
        mint_number=mint_number,
        earliest_imprint=earliest,
        golden_line=golden_line,
    )

    return UploadResponse(
        collectible_id=collectible_id,
        image_url=f"/uploads/{filename}",
        anchor=anchor,
    )


async def _run_generation(collectible_id: str, location_style: str, lat: float, lng: float, photo_path: str = "", gen_opts: dict | None = None, timestamp: str = "", mint_number: int = 0):
    """Background async generation: images + golden line."""
    state = {
        "status": "generating",
        "current_phase_index": 0,
        "phases": GENERATION_PHASES,
    }
    _generation_states[collectible_id] = state

    try:
        # Phase 0: queued (already done, move to phase 1)
        await asyncio.sleep(0.5)
        state["current_phase_index"] = 1

        # Phase 1: analyze location style
        await asyncio.sleep(1.0)
        state["current_phase_index"] = 2

        # Phase 2: generate one image — used for hero, thumbnail, and share
        image_url = await generate_collectible_image(
            lat, lng, location_style, photo_path, gen_opts or {},
            timestamp=timestamp, mint_number=mint_number,
        )

        if image_url:
            db.update_collectible(collectible_id, {
                "hero_url": image_url,
                "thumbnail_url": image_url,
                "share_url": image_url,
                "generation_status": "generating",
            })
        state["current_phase_index"] = 3

        # Phase 3: compose card (simulated)
        await asyncio.sleep(1.0)
        state["current_phase_index"] = 4

        # Phase 4: seal golden line
        await asyncio.sleep(1.0)
        state["current_phase_index"] = 5

        # Complete
        db.update_collectible(collectible_id, {
            "generation_status": "complete",
            "is_featured": True,
        })
        state["status"] = "complete"
        state["current_phase_index"] = 5

    except Exception as e:
        db.update_collectible(collectible_id, {
            "generation_status": "failed",
        })
        state["status"] = "failed"
        state["error_message"] = str(e)


@router.get("/{collectible_id}/status", response_model=GenerationStatusOut)
def get_generation_status(collectible_id: str):
    item = db.get_collectible_by_id(collectible_id)
    if not item:
        raise HTTPException(status_code=404, detail="刻迹不存在")

    state = _generation_states.get(collectible_id, {})
    phases = state.get("phases", GENERATION_PHASES)
    current_idx = state.get("current_phase_index", 0)

    return GenerationStatusOut(
        status=item.get("generation_status", "idle"),
        phases=[
            GenerationPhaseOut(
                id=p["id"],
                label=p["label"],
                detail=p["detail"],
                progress=p["progress"],
                tone=p["tone"],
                status="complete" if i < current_idx else ("generating" if i == current_idx and item.get("generation_status") == "generating" else ("complete" if item.get("generation_status") == "complete" else p.get("status", "queued"))),
                duration_ms=p["duration_ms"],
                can_cancel=p["can_cancel"],
            )
            for i, p in enumerate(phases)
        ],
        current_phase_index=current_idx,
        redirect_collectible_id=collectible_id if item.get("generation_status") == "complete" else None,
        error_message=state.get("error_message"),
    )


@router.post("/{collectible_id}/trigger")
async def trigger_generation(collectible_id: str):
    item = db.get_collectible_by_id(collectible_id)
    if not item:
        raise HTTPException(status_code=404, detail="刻迹不存在")

    location_style = item.get("location_style", "terracotta")
    lat = item.get("latitude", 0)
    lng = item.get("longitude", 0)

    # Determine original photo path: hero_url before generation is the uploaded photo.
    # After generation it becomes /uploads/gen_xxx.png, and we lose the original ref.
    hero_url = item.get("hero_url", "")
    photo_path = ""
    if hero_url.startswith("/uploads/") and not hero_url.startswith("/uploads/gen_"):
        photo_path = str(UPLOAD_DIR / hero_url.replace("/uploads/", ""))

    db.update_collectible(collectible_id, {"generation_status": "generating"})
    ts = item.get("timestamp", "")
    mn = item.get("mint_number", 0)
    asyncio.create_task(_run_generation(collectible_id, location_style, lat, lng, photo_path, None, ts, mn))

    return {"ok": True, "collectible_id": collectible_id}
