"""Golden line generation — AI-powered one-liner based on location/time/weather."""

from __future__ import annotations

GOLDEN_LINES_BY_STYLE: dict[str, list[str]] = {
    "terracotta": [
        "你站在这里的时候，这片土地已经等了{dynasty}年。",
        "每一个站在这里的人，都是在跟{dynasty}年前的历史对话。",
        "时间是最大的雕塑家，你此刻看见的，是它留下的痕迹。",
        "这些石头不说话，但你站得够久，就能听见。",
    ],
    "ink": [
        "每一滴{weather}都曾被一位诗人看见。",
        "山水不问人来人往，只是静静地——等你站进来的这一刻。",
        "你的倒影落入湖面的那一秒，和千年前的某个倒影重叠了。",
        "风从这里经过的时候，总会多停一会儿。大概是知道你来了。",
    ],
    "mural": [
        "{color}的颜料还没褪尽，风沙还没停，你来了。",
        "飞天的线条穿过千年，落进你眼里。",
        "画这面墙的人不会想到，千年后会是你站在这里。",
        "每一颗矿物颜料都在说——我见过太多朝代，但你不一样。",
    ],
    "cyber": [
        "城市每天都在生长，你按下快门这一刻，它刚好停了一下。",
        "钢筋和玻璃在夜色里呼吸。你是第一个注意到的人。",
        "这座城市的每盏灯都亮着一个故事。你此刻站的位置，是你自己的。",
        "时间在这里变快了，但快门能把它停下来。一秒，就够了。",
    ],
}

ERA_FILLERS: dict[str, str] = {
    "terracotta": "2200",
    "ink": "1000",
    "mural": "1600",
    "cyber": "0",
}


def generate_golden_line(
    location_name: str,
    location_style: str,
    weather_condition: str,
    temperature: float,
    aqi_level: str,
    province: str,
) -> str:
    """Generate a poetic one-liner based on location and atmospheric data."""
    import random
    import hashlib

    lines = GOLDEN_LINES_BY_STYLE.get(location_style, GOLDEN_LINES_BY_STYLE["terracotta"])
    dynasty = ERA_FILLERS.get(location_style, "1000")

    # Use location+weather hash for deterministic but varied selection
    seed = hashlib.md5(f"{location_name}{weather_condition}{temperature:.0f}".encode()).hexdigest()
    idx = int(seed, 16) % len(lines)

    line = lines[idx]
    color = "青金" if location_style == "mural" else "矿物"
    return line.format(
        location=location_name,
        weather=weather_condition,
        dynasty=dynasty,
        temperature=int(temperature),
        color=color,
        province=province,
    )
