"""Aday (is arayan) ile ilgili route'lar: kayit/giris, CV yukleme/guncelleme,
eslesme sorgulama, favoriler. Is mantigi burada degil - ai/matching/
matching_service modullerinde; bu dosya sadece HTTP<->DB orkestrasyonu yapar."""
import json
import uuid
from datetime import datetime

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from .. import ai, matching, matching_service
from ..auth import hash_password, verify_password
from ..db import get_db
from ..pdf_utils import extract_text_from_pdf_bytes

router = APIRouter(prefix="/candidates", tags=["candidates"])


def _profile_fields(row) -> dict:
    """Isverenin adayla iletisime gecmesi icin gereken alanlar. Eski
    kayitlarda bu kolonlar bos (NULL) olabilir, bu yuzden hepsi icin
    varsayilan bos string donuyoruz."""
    return {
        "phone": row["phone"] or "",
        "linkedin": row["linkedin"] or "",
        "github": row["github"] or "",
        "location": row["location"] or "",
    }


class LoginRequest(BaseModel):
    email: str
    password: str


class ResetPasswordRequest(BaseModel):
    name: str
    email: str
    new_password: str


@router.post("/login")
async def login_candidate(req: LoginRequest):
    conn = get_db()
    row = conn.execute("SELECT * FROM candidates WHERE email = ?", (req.email,)).fetchone()
    conn.close()
    if not row or not verify_password(req.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="E-posta veya şifre hatalı")
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "cv_analysis": json.loads(row["cv_analysis"]),
        **_profile_fields(row),
    }


@router.post("/reset-password")
async def reset_candidate_password(req: ResetPasswordRequest):
    """E-posta gondermeden basit bir kimlik dogrulamasi: kayitli ad soyad
    VE e-posta esleserse yeni sifre belirlenir. Not: bu gercek bir e-posta
    dogrulamasi degil, sadece ad+e-posta bilgisine dayanir - gelecekte
    gercek e-posta ile sifirlamaya (SMTP) yukseltilebilir."""
    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="Şifre en az 6 karakter olmalı")

    conn = get_db()
    row = conn.execute("SELECT * FROM candidates WHERE email = ?", (req.email,)).fetchone()
    if not row or row["name"].strip().lower() != req.name.strip().lower():
        conn.close()
        raise HTTPException(status_code=404, detail="Ad soyad ve e-posta eşleşen bir hesap bulunamadı")

    conn.execute(
        "UPDATE candidates SET password_hash = ?, updated_at = ? WHERE id = ?",
        (hash_password(req.new_password), datetime.utcnow().isoformat(), row["id"]),
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}


@router.post("")
async def create_candidate(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    file: UploadFile = File(...),
):
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Şifre en az 6 karakter olmalı")

    conn = get_db()
    existing = conn.execute("SELECT * FROM candidates WHERE email = ?", (email,)).fetchone()
    if existing:
        conn.close()
        # E-posta zaten kayitli - sifreyi bilmeden mevcut hesabin verisini
        # dondurmuyoruz. Kullanici giris ekranina yonlendirilmeli.
        raise HTTPException(status_code=409, detail="Bu e-posta ile zaten bir hesap var, giriş yapın")

    pdf_bytes = await file.read()
    cv_text = extract_text_from_pdf_bytes(pdf_bytes)
    cv_analysis = ai.analyze_cv(cv_text)

    candidate_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat()
    conn.execute(
        "INSERT INTO candidates (id, name, email, password_hash, cv_text, cv_analysis, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (candidate_id, name, email, hash_password(password), cv_text, json.dumps(cv_analysis, ensure_ascii=False), now, now),
    )
    conn.commit()
    conn.close()

    return {
        "id": candidate_id,
        "name": name,
        "email": email,
        "cv_analysis": cv_analysis,
        "phone": "",
        "linkedin": "",
        "github": "",
        "location": "",
    }


@router.put("/{candidate_id}/cv")
async def update_candidate_cv(candidate_id: str, file: UploadFile = File(...)):
    """Adayin CV'sini yeniden yukleyip analiz eder. Onceki analizin uzerine
    yazar ve bu adaya ait TUM eski eslesme sonuclarini gecersiz kilar (silinir)
    ki bir sonraki eslestirmede guncel CV'ye gore YENIDEN hesaplansin."""
    conn = get_db()
    candidate = conn.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,)).fetchone()
    if not candidate:
        conn.close()
        raise HTTPException(status_code=404, detail="candidate not found")

    pdf_bytes = await file.read()
    cv_text = extract_text_from_pdf_bytes(pdf_bytes)
    cv_analysis = ai.analyze_cv(cv_text)

    conn.execute(
        "UPDATE candidates SET cv_text = ?, cv_analysis = ?, updated_at = ? WHERE id = ?",
        (cv_text, json.dumps(cv_analysis, ensure_ascii=False), datetime.utcnow().isoformat(), candidate_id),
    )
    conn.execute("DELETE FROM match_cache WHERE candidate_id = ?", (candidate_id,))
    conn.commit()
    conn.close()

    return {
        "id": candidate_id,
        "name": candidate["name"],
        "email": candidate["email"],
        "cv_analysis": cv_analysis,
    }


@router.put("/{candidate_id}/profile")
async def update_candidate_profile(candidate_id: str, profile: dict):
    """Adayin iletisim/profil bilgilerini gunceller (telefon, LinkedIn,
    GitHub, konum). Bunlar CV'den GPT ile cikarilmiyor - dogrudan adayin
    kendisinin girdigi, isverenin adayla iletisime gecmesi icin gereken
    alanlar."""
    conn = get_db()
    candidate = conn.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,)).fetchone()
    if not candidate:
        conn.close()
        raise HTTPException(status_code=404, detail="candidate not found")

    conn.execute(
        "UPDATE candidates SET phone = ?, linkedin = ?, github = ?, location = ?, updated_at = ? WHERE id = ?",
        (
            (profile.get("phone") or "").strip(),
            (profile.get("linkedin") or "").strip(),
            (profile.get("github") or "").strip(),
            (profile.get("location") or "").strip(),
            datetime.utcnow().isoformat(),
            candidate_id,
        ),
    )
    conn.commit()
    updated = conn.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,)).fetchone()
    conn.close()

    return {
        "id": candidate_id,
        "name": updated["name"],
        "email": updated["email"],
        **_profile_fields(updated),
    }


@router.get("/{candidate_id}/matches")
async def get_matches(candidate_id: str):
    conn = get_db()
    candidate = conn.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,)).fetchone()
    job_rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()

    if not candidate:
        conn.close()
        raise HTTPException(status_code=404, detail="candidate not found")

    job_list = [dict(j) for j in job_rows]
    candidate_dict = dict(candidate)
    if not job_list:
        conn.close()
        return {"suitable": [], "others": []}

    # Her (aday, ilan) cifti icin eslesme SADECE BIR KEZ GPT ile hesaplanir ve
    # match_cache tablosuna yazilir. Hesaplama mantigi matching_service'te -
    # ilan tarafindaki /jobs/{id}/candidates route'u da AYNI fonksiyonu kullanir.
    scored = []
    for job in job_list:
        score, explanation = matching_service.get_or_compute_match(conn, candidate_dict, job)
        scored.append((job, score, explanation))

    favorite_ids = {
        r["job_id"] for r in conn.execute(
            "SELECT job_id FROM favorites WHERE candidate_id = ?", (candidate_id,)
        ).fetchall()
    }

    conn.commit()
    conn.close()

    entries = [
        matching.build_match_entry(job, score, explanation, is_favorite=job["id"] in favorite_ids)
        for job, score, explanation in scored
    ]
    suitable, others = matching.split_suitable_others(entries)

    return {"suitable": suitable, "others": others, "candidate_name": candidate["name"]}


@router.post("/{candidate_id}/favorites/{job_id}")
async def add_favorite(candidate_id: str, job_id: str):
    conn = get_db()
    conn.execute(
        "INSERT OR IGNORE INTO favorites (candidate_id, job_id, created_at) VALUES (?, ?, ?)",
        (candidate_id, job_id, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()
    return {"status": "added"}


@router.delete("/{candidate_id}/favorites/{job_id}")
async def remove_favorite(candidate_id: str, job_id: str):
    conn = get_db()
    conn.execute("DELETE FROM favorites WHERE candidate_id = ? AND job_id = ?", (candidate_id, job_id))
    conn.commit()
    conn.close()
    return {"status": "removed"}


@router.get("/{candidate_id}/favorites")
async def list_favorites(candidate_id: str):
    conn = get_db()
    rows = conn.execute("SELECT job_id FROM favorites WHERE candidate_id = ?", (candidate_id,)).fetchall()
    conn.close()
    return {"job_ids": [r["job_id"] for r in rows]}
