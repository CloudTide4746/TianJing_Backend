"""QR code generation for sharing spacetime imprints."""

from __future__ import annotations

import qrcode
from io import BytesIO

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

import database as db

router = APIRouter(prefix="/api/share", tags=["share"])


@router.get("/{collectible_id}/qrcode")
def get_share_qrcode(
    collectible_id: str,
    size: int = Query(300, ge=100, le=800),
):
    """Generate a QR code PNG for sharing a collectible."""
    item = db.get_collectible_by_id(collectible_id)
    if not item:
        raise HTTPException(status_code=404, detail="刻迹不存在")

    # Encode a share URL — use a universal link scheme
    share_url = f"https://spacetime.app/share/{collectible_id}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(share_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#1b1714", back_color="#f6f2e9")
    img = img.resize((size, size))

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")
