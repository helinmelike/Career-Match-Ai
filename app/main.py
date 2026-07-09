"""Uygulamanin giris noktasi. Bu dosya kasitli olarak KUCUK tutulur: sadece
FastAPI app'i olusturur, middleware/router'lari baglar ve statik dosyalari
mount eder. Hicbir is mantigi (DB sorgusu, GPT cagrisi, skor hesaplama)
burada YOK - hepsi ilgili modulde (routers/, ai.py, matching.py, db.py).

Statik dosyalar sadece frontend/ klasorunden servis ediliyor - calisma
dizininin tamami degil. Boylece .env ve kariyerai.db gibi dosyalar yanlislikla
disariya acik olmuyor (frontend/ disinda hicbir sey URL ile erisilebilir degil)."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .db import init_db
from .routers import candidates, employers, jobs, site

app = FastAPI(title="KariyerAI")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

app.include_router(candidates.router)
app.include_router(employers.router)
app.include_router(jobs.router)
app.include_router(site.router)

app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
