"""AI enrichment — 调用 DeepSeek-V3.2-Fast 生成刻迹的标题与艺术信息."""

from __future__ import annotations

import json
import re
from typing import Optional

import httpx

DMXAPI_URL = "https://www.dmxapi.cn/v1/chat/completions"
DMXAPI_KEY = "sk-4u2zIMAMnZfH1h7f8YlbNlyAgCCt9z6Qw4y3cP0qL3fVHLpL"
DMXAPI_MODEL = "deepseek-v4-flash"

SYSTEM_PROMPT_BASE = """你是一个"刻迹"铸造师。用户上传一张照片，系统会自动获取拍摄地点的GPS坐标、天气、空气质量、地点名称、地点风格等信息。

你的任务：基于这些时空数据，为这张照片生成富有诗意和艺术感的元数据。

风格参考：
- terracotta（陶土风）：厚重、历史感、帝国、泥土、不朽
- ink（水墨风）：淡雅、山水、留白、诗意、宁静
- mural（壁画风）：神秘、飞天、矿物颜料、石窟、宗教感
- cyber（赛博风）：霓虹、未来、数字、都市、速度感"""


def _clean_json(raw: str) -> str:
    """Extract JSON from possibly markdown-wrapped response."""
    match = re.search(r"\{[\s\S]*\}", raw)
    if match:
        return match.group(0)
    return raw


def _parse_ai_response(text: str) -> dict:
    """Parse AI response, return dict with sensible defaults on failure."""
    try:
        data = json.loads(_clean_json(text))
    except (json.JSONDecodeError, ValueError):
        return {}

    return {
        "title": str(data.get("title", "")),
        "subtitle": str(data.get("subtitle", "")),
        "short_description": str(data.get("short_description", "")),
        "story": str(data.get("story", "")),
        "golden_line": str(data.get("golden_line", "")),
        "poem_text": str(data.get("poem_text", "")),
        "call_to_action": str(data.get("call_to_action", "")),
        "tags": data.get("tags", []) if isinstance(data.get("tags"), list) else [],
        "material_keywords": data.get("material_keywords", []) if isinstance(data.get("material_keywords"), list) else [],
        "image_alt": str(data.get("image_alt", "")),
    }


async def enrich_spacetime_imprint(
    location_name: str,
    location_style: str,
    weather_condition: str,
    temperature: float,
    province: str,
    district: str,
    era_label: str,
    aqi_level: str,
    wind_direction: str,
    wind_level: int,
    message: str = "",
    ai_poetry: bool = False,
) -> dict:
    """Call DMXAPI to generate artistic metadata for a spacetime imprint."""

    style_names = {
        "terracotta": "陶土风（厚重历史感）",
        "ink": "水墨风（淡雅诗意）",
        "mural": "壁画风（神秘宗教感）",
        "cyber": "赛博风（未来都市感）",
    }
    style_desc = style_names.get(location_style, location_style)

    # Build system prompt based on ai_poetry flag
    if ai_poetry:
        golden_line_instruction = (
            '"golden_line": "一首原创古诗（五言或七言绝句，共4句），必须原创，'
            '融入地点名、天气、时间感，符合中国传统诗词格律",\n'
            '  "poem_text": "古诗全文（纯文本，每句之间用逗号或句号分隔，方便渲染到画面上）"'
        )
        call_to_action_instruction = (
            '"call_to_action": "将上面生成的古诗原文（poem_text）完整复制到这里，作为分享时的底部文案"'
        )
    else:
        golden_line_instruction = (
            '"golden_line": "一句金句（15-30字），像诗一样，关于时间、地点、存在的感悟",\n'
            '  "poem_text": ""'
        )
        call_to_action_instruction = (
            '"call_to_action": "分享行动号召文案（12-20字），邀请他人打开刻迹，融入地点特色或诗意，必须每次不同、不可雷同"'
        )

    system_prompt = (
        f'{SYSTEM_PROMPT_BASE}\n\n'
        f'输出格式：严格的JSON，不要包含任何其他文字。\n\n'
        f'{{\n'
        f'  "title": "刻迹标题（8-16字，有诗意，融合地点名+天气+时间感）",\n'
        f'  "subtitle": "副标题（6-12字）",\n'
        f'  "short_description": "一行简短描述（15-30字），包含年代、天气、温度",\n'
        f'  "story": "2-3句话的故事叙述（60-120字），从第一人称视角描述站在此地的感受，融入历史感和天气氛围",\n'
        f'  {golden_line_instruction},\n'
        f'  {call_to_action_instruction},\n'
        f'  "tags": ["标签1", "标签2", "标签3"],\n'
        f'  "material_keywords": ["材质1", "材质2", "材质3"],\n'
        f'  "image_alt": "图片alt描述文本（10-20字）"\n'
        f'}}'
    )

    user_message = f"""地点：{location_name}
省份：{province}
区县：{district}
时代标签：{era_label}
风格：{style_desc}
天气：{weather_condition}
温度：{int(temperature)}°C
空气质量：{aqi_level}
风向：{wind_direction}
风力：{wind_level}级
用户留言：{message if message else "无"}"""

    payload = {
        "model": DMXAPI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    }

    headers = {
        "Authorization": f"Bearer {DMXAPI_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(DMXAPI_URL, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()

    raw_content = result["choices"][0]["message"]["content"]
    return _parse_ai_response(raw_content)
