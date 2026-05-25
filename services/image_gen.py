"""AI image generation via DMXAPI (gemini-3.1-flash-image-preview).

Uses google-genai SDK with DMXAPI as base URL.
Photo + text multimodal input: the uploaded photo is passed directly
as an image in the contents array alongside the prompt.

Prompt weight hierarchy:
  PRIMARY   — uploaded photo (the image itself, main visual reference)
  SECONDARY — user-selected options (artStyle, mood, season, dynasty, etc.)
  TERTIARY  — auto-anchored data (location name, weather, time — light seasoning only)
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from google import genai
from google.genai import types
from PIL import Image

# Register HEIC/HEIF opener so iPhone photos can be loaded by PIL
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    print("[DEBUG] HEIC/HEIF opener registered successfully")
except ImportError:
    print("[DEBUG] pillow-heif not installed, HEIC photos will fail to load")

from .weather import get_weather
from .geocode import reverse_geocode

DMXAPI_KEY = "sk-4u2zIMAMnZfH1h7f8YlbNlyAgCCt9z6Qw4y3cP0qL3fVHLpL"
DMXAPI_BASE_URL = "https://www.dmxapi.cn"
DMXAPI_MODEL = "gemini-3.1-flash-image-preview"

UPLOAD_DIR = Path(__file__).parent.parent / "uploads"

_client: genai.Client | None = None
_client_lock = asyncio.Lock()


async def _get_client() -> genai.Client:
    global _client
    if _client is None:
        async with _client_lock:
            if _client is None:
                _client = genai.Client(
                    api_key=DMXAPI_KEY,
                    http_options={'base_url': DMXAPI_BASE_URL},
                )
    return _client


# ── Style base prompts (used only when location_style is the sole guide) ──

STYLE_PROMPTS: dict[str, str] = {
    "terracotta": (
        "ancient Chinese archaeological aesthetic, terracotta clay texture, "
        "Qin dynasty small seal script calligraphy elements, bronze and copper rust tones, "
        "ancient ceramic surface, weathered stone textures, "
        "premium collectible card artwork with museum quality, "
        "warm ochre and earthen color palette, dramatic lighting"
    ),
    "ink": (
        "Chinese ink wash painting style, misty atmosphere, negative space composition, "
        "jade green and celadon color palette, poetic landscape aesthetic, "
        "soft watercolor washes, elegant calligraphy accents, "
        "premium collectible card artwork, refined literati taste"
    ),
    "mural": (
        "Dunhuang Mogao Caves mural art style, flying apsaras celestial beings motif, "
        "mineral pigment texture, ancient fresco surface with craquelure, "
        "warm ochre and lapis lazuli blue palette, Silk Road aesthetic, "
        "premium collectible card, weathered yet vibrant colors"
    ),
    "cyber": (
        "cyberpunk neon aesthetic, glass refraction effects, "
        "deep purple and electric blue color palette, futuristic urban atmosphere, "
        "chrome and holographic accents, sleek modern lines, "
        "premium collectible card design, nocturnal cityscape glow"
    ),
}

# ── User option → bilingual prompt fragment mappings ──

ART_STYLE_PROMPTS: dict[str, str] = {
    "ink-wash": (
        "Chinese ink wash painting style (水墨画). "
        "Large areas of negative space, layered ink washes, misty atmosphere. "
        "Jade green and celadon color tones. Calligraphic brushwork. "
        "Poetic literati landscape aesthetic. Soft, flowing lines."
    ),
    "dunhuang-mural": (
        "Dunhuang Mogao Caves mural fresco style (敦煌壁画). "
        "Mineral pigment textures, ancient weathered wall surface with craquelure. "
        "Flying apsaras (飞天) flowing lines. "
        "Warm ochre and lapis lazuli blue palette. Silk Road aesthetic."
    ),
    "oil-painting": (
        "Classical oil painting style (油画). "
        "Visible thick brushstrokes, deep chiaroscuro lighting like Rembrandt. "
        "Rich layered colors, museum-quality fine art texture. "
        "Dramatic light and shadow depth."
    ),
    "woodblock": (
        "Woodblock print style (木刻版画). "
        "Bold black and white contrast, strong carved line marks. "
        "Wood grain texture visible. Folk art power and simplicity. "
        "Graphic, striking visual impact."
    ),
    "watercolor": (
        "Watercolor painting style (水彩画). "
        "Transparent wet washes, soft gentle gradients. "
        "Light, airy colors like memory. "
        "Delicate bleeding edges, luminous paper-white highlights."
    ),
    "cyber-neon": (
        "Cyberpunk neon aesthetic (赛博霓虹). "
        "Holographic glass refraction effects. "
        "Deep purple and electric blue color palette. "
        "Futuristic city night atmosphere with glowing neon lights. "
        "Chrome and digital surface textures."
    ),
}

COLOR_TONE_PROMPTS: dict[str, str] = {
    "warm-earth": "Warm earth tones: ochre, terracotta, amber, golden brown. Like sunset on ancient ruins.",
    "cool-jade": "Cool jade tones: celadon, jade green, ink blue, grey-blue. Like moonlight on clear spring water.",
    "vintage-fade": "Vintage faded photo tones: yellowed ivory white, light sepia brown. Like old photographs from the 1920s.",
    "monochrome": "Monochrome black and white. Extreme light-shadow contrast. Silver gelatin film aesthetic, timeless.",
}

TIME_TEXTURE_PROMPTS: dict[str, str] = {
    "ancient-weathered": "Ancient weathered surface texture. Deep erosion marks from millennia. Old and solemn.",
    "century-patina": "Century patina texture. Copper green oxidation layer. Historical warm mellow surface.",
    "contemporary": "Contemporary fresh texture. Clean and crisp. Digital-age precision and clarity.",
    "future-gloss": "Future gloss texture. Like liquid metal and smart glass. High-tech futuristic sheen.",
}

MOOD_PROMPTS: dict[str, str] = {
    "lonely": "Lonely and desolate mood. Vast empty space, one person facing the immense world. Melancholic.",
    "lively": "Lively and bustling mood. Full of vibrant energy, crowds, thriving life. Energetic.",
    "serene": "Serene and peaceful mood. Like a temple at dawn or lake at dusk. Inner calm and tranquility.",
    "vast": "Vast and majestic mood. Epic narrative scale. Awe-inspiring grand landscape.",
    "mysterious": "Mysterious and enigmatic mood. Like distant mountains in mist or moonlit castles. Intriguing.",
    "romantic": "Romantic and lyrical mood. Like flower rain or starry river. Gentle and touching.",
    "tragic": "Tragic and solemn mood. Like ruins at sunset or a hero's end. Deep and powerful.",
    "hopeful": "Hopeful and bright mood. Like the first ray of dawn or spring sprouts. Uplifting and warm.",
}

NARRATIVE_PERSPECTIVE_PROMPTS: dict[str, str] = {
    "third-person": "Third-person documentary perspective. Objective and profound gaze like a documentary film.",
    "first-person": "First-person diary perspective. As if the witness recorded this moment with their camera.",
    "archaeological": "Archaeological report perspective. Scientific excavation photography. Rigorous yet full of discovery.",
    "poetic": "Poetic perspective. The image as a visual poem full of metaphor and rhythmic beauty.",
}

DETAIL_DENSITY_PROMPTS: dict[str, str] = {
    "minimal": "Minimalist. Dramatically simplified details. Emphasis on composition and negative space.",
    "moderate": "Moderate detail density. Subject in focus, background appropriately simplified.",
    "elaborate": "Extremely elaborate detail. Every inch of the image filled with carefully crafted textures and ornaments.",
}

CONTRAST_PROMPTS: dict[str, str] = {
    "soft": "Soft contrast. Like thin mist covering. Smooth gentle light-shadow transitions.",
    "standard": "Standard contrast. Natural light layers. Clear but not harsh.",
    "high": "High contrast. Strong light-shadow conflict. Like dramatic theater spotlight effect.",
}

GRAIN_PROMPTS: dict[str, str] = {
    "smooth": "Smooth digital surface. Clean like a mirror. No noise or texture interference.",
    "film-grain": "Film grain texture. Classic 35mm film noise. Warm vintage photography feel.",
    "mural-peel": "Mural peeling texture. Natural flaking marks on the surface. Revealing ancient layers beneath.",
}

SEASON_PROMPTS: dict[str, str] = {
    "spring": "Spring atmosphere. Peach blossoms blooming, fresh green sprouts. Air full of life and gentleness.",
    "summer": "Summer atmosphere. Dense green shade, intense sunlight. Nature at its peak of growth.",
    "autumn": "Autumn atmosphere. Golden falling leaves, crisp autumn wind. Season of maturity and harvest.",
    "winter": "Winter atmosphere. White snow covering, bare branches with ice. World in quiet stillness.",
}

DYNASTY_PROMPTS: dict[str, str] = {
    "qin": "Qin Dynasty elements: small seal script (小篆), terracotta clay textures, bronze weapon patterns, black-red color scheme, unified measurement symbols.",
    "han": "Han Dynasty elements: Han clerical script (汉隶), stone relief textures, Silk Road motifs, Four Gods roof tile patterns (四神瓦当), vermillion-ink color scheme.",
    "tang": "Tang Dynasty elements: flourishing floral patterns, Tang Sancai (唐三彩) glaze flowing colors, flying apsaras dance poses, plump horse and lady silhouettes, gold-splendid palette.",
    "song": "Song Dynasty elements: Song ceramic crackle glaze (开片), Slender Gold calligraphy (瘦金体), landscape painting texture strokes (皴法), Ru ware celadon tones, minimalist elegance.",
    "ming": "Ming Dynasty elements: Ming furniture lines, blue-white porcelain (青花瓷) patterns, cloisonné (景泰蓝) filigree, garden frame views, vermillion-royal blue palette.",
    "qing": "Qing Dynasty elements: enamel painted (珐琅彩) fine decorations, Suzhou garden leak windows (漏窗), Beijing opera facial makeup colors, intricate brocade patterns, ornate luxury.",
}


def _build_style_prompt(gen_opts: dict) -> str:
    """Build the user-option style prompt."""
    parts: list[str] = []

    art_style = gen_opts.get("artStyle", "")
    if art_style and art_style in ART_STYLE_PROMPTS:
        parts.append(f"ART STYLE (highest priority): {ART_STYLE_PROMPTS[art_style]}")

    color_tone = gen_opts.get("colorTone", "")
    if color_tone and color_tone in COLOR_TONE_PROMPTS:
        parts.append(f"Color tone: {COLOR_TONE_PROMPTS[color_tone]}")

    time_texture = gen_opts.get("timeTexture", "")
    if time_texture and time_texture in TIME_TEXTURE_PROMPTS:
        parts.append(f"Surface texture: {TIME_TEXTURE_PROMPTS[time_texture]}")

    mood = gen_opts.get("mood", "")
    if mood and mood in MOOD_PROMPTS:
        parts.append(f"Mood: {MOOD_PROMPTS[mood]}")

    narrative = gen_opts.get("narrativePerspective", "")
    if narrative and narrative in NARRATIVE_PERSPECTIVE_PROMPTS:
        parts.append(f"Narrative perspective: {NARRATIVE_PERSPECTIVE_PROMPTS[narrative]}")

    detail = gen_opts.get("detailDensity", "")
    if detail and detail in DETAIL_DENSITY_PROMPTS:
        parts.append(f"Detail level: {DETAIL_DENSITY_PROMPTS[detail]}")

    contrast = gen_opts.get("contrast", "")
    if contrast and contrast in CONTRAST_PROMPTS:
        parts.append(f"Contrast: {CONTRAST_PROMPTS[contrast]}")

    grain = gen_opts.get("grain", "")
    if grain and grain in GRAIN_PROMPTS:
        parts.append(f"Image grain: {GRAIN_PROMPTS[grain]}")

    season = gen_opts.get("season", "")
    if season and season in SEASON_PROMPTS:
        parts.append(f"Season: {SEASON_PROMPTS[season]}")

    dynasty = gen_opts.get("dynastyCollage", "")
    if dynasty and dynasty in DYNASTY_PROMPTS:
        parts.append(f"Dynasty elements: {DYNASTY_PROMPTS[dynasty]}")

    keywords = gen_opts.get("customKeywords", "")
    if keywords:
        parts.append(f"Additional keywords: {keywords}")

    ai_poetry = gen_opts.get("aiPoetry", False)
    if ai_poetry:
        parts.append(
            "AI Poetry overlay: Render a short classical Chinese poem (古诗/绝句, 2-4 lines) "
            "directly onto the image as elegant calligraphy text. "
            "Place it in an unobtrusive corner with subtle ink-brush calligraphy style. "
            "The poem should complement the scene's mood and location atmosphere. "
            "Use vertical or semi-vertical traditional Chinese layout. "
            "The calligraphy must blend naturally with the artwork style — like an ancient scroll painting with marginalia."
        )

    return "\n".join(parts)


def _build_system_prompt(
    location_style: str, gen_opts: dict, location_name: str, weather_cond: str,
    lat: float = 0, lng: float = 0, timestamp: str = "", mint_number: int = 0,
) -> str:
    """Build the full prompt. User-selected artStyle OVERRIDES location_style."""
    style_section = _build_style_prompt(gen_opts)

    art_style = gen_opts.get("artStyle", "")
    if art_style and art_style in ART_STYLE_PROMPTS:
        primary_style = ART_STYLE_PROMPTS[art_style]
    else:
        primary_style = STYLE_PROMPTS.get(location_style, STYLE_PROMPTS["terracotta"])

    # Build watermark text
    lat_str = f"{abs(lat):.2f}°{'N' if lat >= 0 else 'S'}"
    lng_str = f"{abs(lng):.2f}°{'E' if lng >= 0 else 'W'}"
    watermark_text = f"Collection #{mint_number}  |  {location_name}  |  {lat_str} {lng_str}  |  {weather_cond}  |  {timestamp}"

    # Build prompt: style instruction FIRST, then photo transformation guidance
    prompt = (
        f"Generate a premium collectible card image in this EXACT style:\n"
        f"{primary_style}\n"
        f"{style_section}\n"
        f"\n"
        f"CRITICAL PHOTO-TRANSFORMATION RULES:\n"
        f"- The uploaded photo is your ONLY source material. This is an img2img style transfer.\n"
        f"- KEEP the photo's subject, composition, and visual focus EXACTLY as they are.\n"
        f"- Apply the style like a filter: change texture, color, and surface, NOT content.\n"
        f"- Do NOT invent new buildings, people, or scenery. Use ONLY what is in the photo.\n"
        f"- If the photo shows a building, the output must show THAT building, styled.\n"
        f"\n"
        f"Location context (subtle seasoning only): {location_name}, weather: {weather_cond}\n"
        f"\n"
        f"WATERMARK REQUIREMENT (MANDATORY):\n"
        f"- At the very bottom of the image, add a thin horizontal strip/band (subtle, semi-transparent dark overlay).\n"
        f"- Inside this strip, render this exact text in a small, elegant, monospaced font:\n"
        f'  \\"{watermark_text}\\"\n'
        f"- The watermark text must be clearly readable but subtle — like museum artifact labels.\n"
        f"- Use white or light-colored text on a semi-transparent dark strip.\n"
        f"- The watermark must NOT cover or obscure the main artwork content.\n"
        f"\n"
        f"Technical: museum-quality collectible card composition, high detail, premium finish."
    )

    print(f"[DEBUG] gen_opts received: {gen_opts}")
    print(f"[DEBUG] artStyle value: '{art_style}'")
    print(f"[DEBUG] location_style: {location_style}")
    print(f"[DEBUG] Prompt (first 300 chars): {prompt[:300]}...")

    return prompt


def _load_photo(photo_path: str) -> Image.Image | None:
    """Load uploaded photo as PIL Image. Returns None if path is empty or missing."""
    if not photo_path:
        print("[DEBUG] photo_path is empty!")
        return None
    path = Path(photo_path)
    if not path.exists():
        print(f"[DEBUG] photo_path does not exist: {photo_path}")
        # Try the .png fallback (uploaded photos are converted to PNG)
        png_path = path.with_suffix('.png')
        if png_path.exists():
            path = png_path
            print(f"[DEBUG] Using PNG fallback: {png_path}")
        else:
            return None

    try:
        img = Image.open(path)
        # Convert to RGB if RGBA (gemini prefers RGB)
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGBA').convert('RGB')
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        print(f"[DEBUG] Photo loaded: {path} (size={img.size}, mode={img.mode})")
        return img
    except Exception as e:
        print(f"[DEBUG] Failed to load photo: {e}")
        # Try reading raw bytes as last resort
        try:
            raw = path.read_bytes()
            print(f"[DEBUG] File size: {len(raw)} bytes, first 16 bytes: {raw[:16].hex()}")
        except Exception:
            pass
        return None


def convert_upload_to_png(filepath: str) -> str:
    """Convert uploaded photo to PNG format for reliable loading.
    Returns the PNG filepath (may be same as input if already PNG)."""
    path = Path(filepath)
    if path.suffix.lower() in ('.png',):
        return filepath

    png_path = path.with_suffix('.png')
    try:
        img = Image.open(path)
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGBA')
        else:
            img = img.convert('RGB')
        img.save(str(png_path), 'PNG')
        print(f"[DEBUG] Converted uploaded photo to PNG: {png_path} (size={img.size})")
        return str(png_path)
    except Exception as e:
        print(f"[DEBUG] Failed to convert to PNG: {e}, using original file")
        return filepath


async def _generate_and_save(
    prompt: str,
    photo_path: str = "",
    aspect_ratio: str = "16:9",
    image_size: str = "2K",
) -> str:
    """Call gemini image model via DMXAPI — matches the user's DMXAPI example pattern."""
    client = await _get_client()

    # Build contents in the EXACT pattern from DMXAPI example: [prompt] + images
    images = []
    photo = _load_photo(photo_path)
    if photo is not None:
        images.append(photo)
        print(f"[DEBUG] Adding photo to contents, total images: {len(images)}")
    else:
        print("[DEBUG] WARNING: No photo in contents — generating without reference image!")

    contents = [prompt] + images
    print(f"[DEBUG] Contents: prompt + {len(images)} image(s)")

    response = client.models.generate_content(
        model=DMXAPI_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=['IMAGE'],
            image_config=types.ImageConfig(
                aspect_ratio=aspect_ratio,
                image_size=image_size,
            ),
        ),
    )

    # Parse response — extract the generated image
    for part in response.parts:
        if part.inline_data is not None:
            image = part.as_image()
            filename = f"gen_{uuid.uuid4().hex}.png"
            filepath = UPLOAD_DIR / filename
            image.save(str(filepath))
            print(f"[DEBUG] Generated image saved: {filepath}")
            return f"/uploads/{filename}"

    raise RuntimeError("No image returned from model")


async def generate_collectible_image(
    lat: float, lng: float, location_style: str,
    photo_path: str = "", gen_opts: dict | None = None,
    timestamp: str = "", mint_number: int = 0,
) -> str:
    """Generate a collectible-style hero image — 16:9 horizontal."""
    if gen_opts is None:
        gen_opts = {}

    loc = await reverse_geocode(lat, lng)
    weather = await get_weather(lat, lng)

    location_name = loc.get("location_name", f"{lat},{lng}")
    weather_cond = weather.get("weather_condition", "Clear")

    prompt = _build_system_prompt(
        location_style, gen_opts, location_name, weather_cond,
        lat=lat, lng=lng, timestamp=timestamp, mint_number=mint_number,
    )

    try:
        return await _generate_and_save(prompt, photo_path, aspect_ratio="16:9", image_size="2K")
    except Exception as e:
        print(f"[DEBUG] generate_collectible_image failed: {e}")
        return ""


async def generate_thumbnail(
    lat: float, lng: float, location_style: str,
    photo_path: str = "", gen_opts: dict | None = None,
    timestamp: str = "", mint_number: int = 0,
) -> str:
    """Generate a square thumbnail — 1:1."""
    if gen_opts is None:
        gen_opts = {}

    loc = await reverse_geocode(lat, lng)
    location_name = loc.get("location_name", f"{lat},{lng}")
    weather = await get_weather(lat, lng)
    weather_cond = weather.get("weather_condition", "Clear")

    prompt = _build_system_prompt(
        location_style, gen_opts, location_name, weather_cond,
        lat=lat, lng=lng, timestamp=timestamp, mint_number=mint_number,
    )
    prompt += "\nSquare 1:1 composition, suitable for thumbnail use"

    try:
        return await _generate_and_save(prompt, photo_path, aspect_ratio="1:1", image_size="1K")
    except Exception as e:
        print(f"[DEBUG] generate_thumbnail failed: {e}")
        return ""


async def generate_share_image(
    lat: float, lng: float, location_style: str,
    photo_path: str = "", gen_opts: dict | None = None,
    timestamp: str = "", mint_number: int = 0,
) -> str:
    """Generate a vertical share poster — 9:16."""
    if gen_opts is None:
        gen_opts = {}

    loc = await reverse_geocode(lat, lng)
    location_name = loc.get("location_name", f"{lat},{lng}")
    weather = await get_weather(lat, lng)
    weather_cond = weather.get("weather_condition", "Clear")

    prompt = _build_system_prompt(
        location_style, gen_opts, location_name, weather_cond,
        lat=lat, lng=lng, timestamp=timestamp, mint_number=mint_number,
    )
    prompt += "\nVertical poster composition, suitable for social media sharing, elegant museum exhibition poster design"

    try:
        return await _generate_and_save(prompt, photo_path, aspect_ratio="9:16", image_size="2K")
    except Exception as e:
        print(f"[DEBUG] generate_share_image failed: {e}")
        return ""
