import json
import uuid
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import ai, matching, matching_service
from .db import get_db, init_db
from .pdf_utils import extract_text_from_pdf_bytes

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SUITABLE_FLOOR = 35.0
SUITABLE_MARGIN = 15.0

init_db()


@app.get("/candidates/by-email/{email}")
async def get_candidate_by_email(email: str):
    conn = get_db()
    row = conn.execute("SELECT * FROM candidates WHERE email = ?", (email,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="not found")
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "cv_analysis": json.loads(row["cv_analysis"]),
    }


@app.post("/candidates")
async def create_candidate(name: str = Form(...), email: str = Form(...), file: UploadFile = File(...)):
    conn = get_db()
    existing = conn.execute("SELECT * FROM candidates WHERE email = ?", (email,)).fetchone()
    if existing:
        conn.close()
        return {
            "id": existing["id"],
            "name": existing["name"],
            "email": existing["email"],
            "cv_analysis": json.loads(existing["cv_analysis"]),
            "already_existed": True,
        }

    pdf_bytes = await file.read()
    cv_text = extract_text_from_pdf_bytes(pdf_bytes)
    cv_analysis = ai.analyze_cv(cv_text)

    candidate_id = str(uuid.uuid4())[:8]
    conn.execute(
        "INSERT INTO candidates (id, name, email, cv_text, cv_analysis, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (candidate_id, name, email, cv_text, json.dumps(cv_analysis, ensure_ascii=False), datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()

    return {
        "id": candidate_id,
        "name": name,
        "email": email,
        "cv_analysis": cv_analysis,
        "already_existed": False,
    }


class JobCreateRequest(BaseModel):
    title: str
    company: str = ""
    text: str


@app.post("/jobs")
async def create_job(req: JobCreateRequest):
    job_analysis = ai.analyze_job(req.text)

    conn = get_db()
    job_id = str(uuid.uuid4())[:8]
    conn.execute(
        "INSERT INTO jobs (id, title, company, text, job_analysis, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (job_id, req.title, req.company, req.text, json.dumps(job_analysis, ensure_ascii=False), datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()
    return {"id": job_id, "title": req.title, "company": req.company, "text": req.text, "job_analysis": job_analysis}


@app.get("/jobs")
async def list_jobs():
    conn = get_db()
    rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
    conn.close()
    return {"jobs": [dict(r) for r in rows]}


@app.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    conn = get_db()
    conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    conn.execute("DELETE FROM match_cache WHERE job_id = ?", (job_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted"}


@app.get("/candidates/{candidate_id}/matches")
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
    # match_cache tablosuna yazilir - aday/ilan sayisi buyudukce GPT maliyetini
    # kontrol altinda tutar. Hesaplama mantigi matching_service'te - ilan
    # tarafindaki /jobs/{id}/candidates endpoint'i de AYNI fonksiyonu kullanir.
    scored_entries = []
    for job in job_list:
        score, explanation = matching_service.get_or_compute_match(conn, candidate_dict, job)
        scored_entries.append({"job": job, "explanation": explanation, "score": score})

    conn.commit()
    conn.close()

    max_score = max((e["score"] for e in scored_entries), default=0.0)
    dynamic_threshold = max(SUITABLE_FLOOR, max_score - SUITABLE_MARGIN)

    suitable = []
    others = []
    for e in scored_entries:
        job = e["job"]
        score = round(e["score"], 1)
        explanation = e["explanation"]
        entry = {
            "job_id": job["id"],
            "job_title": job["title"],
            "company": job.get("company", ""),
            "similarity_score": score,
            "eslesen_beceriler": explanation.get("eslesen_beceriler", []),
            "eksik_beceriler": explanation.get("eksik_beceriler", []),
            "kisa_degerlendirme": explanation.get("kisa_degerlendirme", ""),
            "tavsiye_edilir_mi": explanation.get("tavsiye_edilir_mi", ""),
            "gereksinim_degerlendirmesi": explanation.get("gereksinim_degerlendirmesi", []),
        }
        if score >= dynamic_threshold:
            suitable.append(entry)
        else:
            others.append(entry)

    suitable.sort(key=lambda x: x["similarity_score"], reverse=True)
    others.sort(key=lambda x: x["similarity_score"], reverse=True)

    return {"suitable": suitable, "others": others, "candidate_name": candidate["name"]}


@app.get("/jobs/{job_id}/candidates")
async def get_job_candidates(job_id: str):
    """Isverenin bir ilana uygun aday havuzunu gormesi icin. Ayni skorlama
    mantigini (matching_service) kullanir - bir aday hem kendi eslesme
    sayfasinda hem burada ayni skoru gorur, cunku ikisi de ayni cache'i
    okur/yazar."""
    conn = get_db()
    job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    candidate_rows = conn.execute("SELECT * FROM candidates ORDER BY created_at DESC").fetchall()

    if not job:
        conn.close()
        raise HTTPException(status_code=404, detail="job not found")

    job_dict = dict(job)
    candidate_list = [dict(c) for c in candidate_rows]
    if not candidate_list:
        conn.close()
        return {"candidates": [], "job_title": job_dict["title"]}

    scored_entries = []
    for candidate in candidate_list:
        score, explanation = matching_service.get_or_compute_match(conn, candidate, job_dict)
        scored_entries.append({"candidate": candidate, "explanation": explanation, "score": score})

    conn.commit()
    conn.close()

    results = []
    for e in scored_entries:
        c = e["candidate"]
        score = round(e["score"], 1)
        explanation = e["explanation"]
        results.append({
            "candidate_id": c["id"],
            "name": c["name"],
            "email": c["email"],
            "similarity_score": score,
            "eslesen_beceriler": explanation.get("eslesen_beceriler", []),
            "eksik_beceriler": explanation.get("eksik_beceriler", []),
            "kisa_degerlendirme": explanation.get("kisa_degerlendirme", ""),
            "tavsiye_edilir_mi": explanation.get("tavsiye_edilir_mi", ""),
            "gereksinim_degerlendirmesi": explanation.get("gereksinim_degerlendirmesi", []),
        })

    results.sort(key=lambda x: x["similarity_score"], reverse=True)
    return {"candidates": results, "job_title": job_dict["title"]}


app.mount("/", StaticFiles(directory=".", html=True), name="static")
