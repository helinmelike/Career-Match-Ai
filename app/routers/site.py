"""Site geneli ayarlar - su an sadece logo yukleme. Kullanici bazli degil,
tum siteye ait tek bir logo dosyasi (frontend/uploads/logo.png)."""
import os

from fastapi import APIRouter, File, HTTPException, UploadFile

router = APIRouter(prefix="/site", tags=["site"])

_UPLOAD_DIR = os.path.join("frontend", "uploads")
_ALLOWED_TYPES = {"image/png", "image/jpeg", "image/svg+xml", "image/webp"}


@router.post("/logo")
async def upload_logo(file: UploadFile = File(...)):
    if file.content_type not in _ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Sadece PNG/JPEG/SVG/WEBP kabul edilir")

    os.makedirs(_UPLOAD_DIR, exist_ok=True)
    content = await file.read()
    dest = os.path.join(_UPLOAD_DIR, "logo.png")
    with open(dest, "wb") as f:
        f.write(content)

    return {"status": "ok", "url": "/uploads/logo.png"}
