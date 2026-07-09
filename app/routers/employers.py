"""Isveren hesaplari: kayit ve giris. Once (sirket adi metin kutusuna
girilip hicbir dogrulama yapilmayan) sahte bir 'giris' vardi - artik gercek
e-posta+sifre ile hesap olusturuluyor ve dogrulaniyor."""
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..auth import hash_password, verify_password
from ..db import get_db

router = APIRouter(prefix="/employers", tags=["employers"])


class EmployerRegisterRequest(BaseModel):
    company_name: str
    email: str
    password: str


class EmployerLoginRequest(BaseModel):
    email: str
    password: str


class EmployerResetPasswordRequest(BaseModel):
    company_name: str
    email: str
    new_password: str


def _public(row) -> dict:
    return {"id": row["id"], "company_name": row["company_name"], "email": row["email"]}


@router.post("/register")
async def register_employer(req: EmployerRegisterRequest):
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Şifre en az 6 karakter olmalı")

    conn = get_db()
    existing = conn.execute("SELECT id FROM employers WHERE email = ?", (req.email,)).fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=409, detail="Bu e-posta ile zaten bir hesap var, giriş yapın")

    employer_id = str(uuid.uuid4())[:8]
    conn.execute(
        "INSERT INTO employers (id, company_name, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
        (employer_id, req.company_name, req.email, hash_password(req.password), datetime.utcnow().isoformat()),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM employers WHERE id = ?", (employer_id,)).fetchone()
    conn.close()
    return _public(row)


@router.post("/login")
async def login_employer(req: EmployerLoginRequest):
    conn = get_db()
    row = conn.execute("SELECT * FROM employers WHERE email = ?", (req.email,)).fetchone()
    conn.close()
    if not row or not verify_password(req.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="E-posta veya şifre hatalı")
    return _public(row)


@router.post("/reset-password")
async def reset_employer_password(req: EmployerResetPasswordRequest):
    """E-posta gondermeden basit bir kimlik dogrulamasi: kayitli sirket adi
    VE e-posta esleserse yeni sifre belirlenir. Bkz. candidates.py'deki
    ayni mekanizmanin notu - gercek e-posta dogrulamasi degildir."""
    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="Şifre en az 6 karakter olmalı")

    conn = get_db()
    row = conn.execute("SELECT * FROM employers WHERE email = ?", (req.email,)).fetchone()
    if not row or row["company_name"].strip().lower() != req.company_name.strip().lower():
        conn.close()
        raise HTTPException(status_code=404, detail="Şirket adı ve e-posta eşleşen bir hesap bulunamadı")

    conn.execute(
        "UPDATE employers SET password_hash = ? WHERE id = ?",
        (hash_password(req.new_password), row["id"]),
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}
