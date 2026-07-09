import json
import uuid
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import ai, matching
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
    conn.close()

    if not candidate:
        raise HTTPException(status_code=404, detail="candidate not found")

    job_list = [dict(j) for j in job_rows]
    if not job_list:
        return {"suitable": [], "others": []}

    cv_analysis = json.loads(candidate["cv_analysis"])

    # Her (aday, ilan) cifti icin eslesme SADECE BIR KEZ GPT ile hesaplanir ve
    # match_cache tablosuna yazilir - aday/ilan sayisi buyudukce GPT maliyetini
    # kontrol altinda tutar.
    conn = get_db()
    scored_entries = []
    for job in job_list:
        cached = conn.execute(
            "SELECT score, explanation FROM match_cache WHERE candidate_id = ? AND job_id = ?",
            (candidate_id, job["id"]),
        ).fetchone()

        if cached:
            score = cached["score"]
            explanation = json.loads(cached["explanation"])
        else:
            job_analysis_raw = job.get("job_analysis")
            if job_analysis_raw:
                job_analysis = json.loads(job_analysis_raw)
            else:
                job_analysis = ai.analyze_job(job["text"])

            # Eski semadaki ilanlarda "aranan_beceriler" tek listeydi.
            if "zorunlu_beceriler" not in job_analysis and "aranan_beceriler" in job_analysis:
                job_analysis = {
                    **job_analysis,
                    "zorunlu_beceriler": job_analysis.get("aranan_beceriler", []),
                    "tercih_beceriler": [],
                }

            raw_result = ai.explain_match(cv_analysis, candidate["cv_text"], job_analysis, job["text"])
            gereksinimler = raw_result.get("gereksinim_degerlendirmesi", [])

            for g in gereksinimler:
                g["durum"] = matching.normalize_durum(g.get("durum"))
                g["tur"] = matching.normalize_tur(g.get("tur"))

            matching.apply_evidence_safety_net(gereksinimler, cv_analysis, candidate["cv_text"])

            score = matching.compute_match_score(
                gereksinimler,
                cv_deneyim=cv_analysis.get("deneyim_seviyesi"),
                job_deneyim=job_analysis.get("deneyim_seviyesi"),
            )
            tavsiye = matching.recommendation_from_score(score)
            eslesen_beceriler = [
                g.get("gereksinim", "") for g in gereksinimler
                if g.get("durum") in ("karsilaniyor", "kismen") and g.get("gereksinim")
            ]
            eksik_beceriler = [
                g.get("gereksinim", "") for g in gereksinimler
                if g.get("durum") == "karsilanmiyor" and g.get("gereksinim")
            ]

            explanation = {
                "gereksinim_degerlendirmesi": gereksinimler,
                "eslesen_beceriler": eslesen_beceriler,
                "eksik_beceriler": eksik_beceriler,
                "kisa_degerlendirme": raw_result.get("kisa_degerlendirme", ""),
                "tavsiye_edilir_mi": tavsiye,
            }
            conn.execute(
                "INSERT OR REPLACE INTO match_cache (candidate_id, job_id, score, explanation, computed_at) VALUES (?, ?, ?, ?, ?)",
                (candidate_id, job["id"], score, json.dumps(explanation, ensure_ascii=False), datetime.utcnow().isoformat()),
            )

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


app.mount("/", StaticFiles(directory=".", html=True), name="static")
