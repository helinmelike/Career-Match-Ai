"""Ilan (is veren) ile ilgili route'lar: olusturma/duzenleme/silme, listeleme,
ve bir ilana uygun aday havuzunu getirme.

Her ilan bir employer_id'ye baglidir (sahiplik). GET /jobs varsayilan olarak
employer_id filtresi ISTER - boylece bir isveren sadece KENDI ilanlarini
gorur, baskalarinin ilanlarini degil. PUT/DELETE de sahiplik kontrolu yapar.
Adaylarin eslesme akisi (routers/candidates.py) bu filtreden etkilenmez -
orada TUM ilanlar (hangi isverene ait olursa olsun) degerlendirilir, cunku
bir adayin onune sadece tek bir sirketin degil TUM uygun ilanlarin gelmesi
gerekir."""
import json
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import ai, matching, matching_service
from ..db import get_db

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobCreateRequest(BaseModel):
    employer_id: str
    title: str
    company: str = ""
    text: str


@router.post("")
async def create_job(req: JobCreateRequest):
    job_analysis = ai.analyze_job(req.text)

    conn = get_db()
    job_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat()
    conn.execute(
        "INSERT INTO jobs (id, employer_id, title, company, text, job_analysis, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (job_id, req.employer_id, req.title, req.company, req.text, json.dumps(job_analysis, ensure_ascii=False), now, now),
    )
    conn.commit()
    conn.close()
    return {"id": job_id, "title": req.title, "company": req.company, "text": req.text, "job_analysis": job_analysis}


@router.put("/{job_id}")
async def update_job(job_id: str, req: JobCreateRequest):
    """Ilani gunceller, yeniden analiz eder ve bu ilana ait TUM eski
    eslesme sonuclarini gecersiz kilar (silinir) ki bir sonraki
    eslestirmede guncel ilana gore YENIDEN hesaplansin. Sadece ilanin
    sahibi olan isveren duzenleyebilir."""
    conn = get_db()
    job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not job:
        conn.close()
        raise HTTPException(status_code=404, detail="job not found")
    if job["employer_id"] and job["employer_id"] != req.employer_id:
        conn.close()
        raise HTTPException(status_code=403, detail="Bu ilan size ait değil")

    job_analysis = ai.analyze_job(req.text)

    conn.execute(
        "UPDATE jobs SET title = ?, company = ?, text = ?, job_analysis = ?, updated_at = ? WHERE id = ?",
        (req.title, req.company, req.text, json.dumps(job_analysis, ensure_ascii=False), datetime.utcnow().isoformat(), job_id),
    )
    conn.execute("DELETE FROM match_cache WHERE job_id = ?", (job_id,))
    conn.commit()
    conn.close()

    return {"id": job_id, "title": req.title, "company": req.company, "text": req.text, "job_analysis": job_analysis}


@router.get("")
async def list_jobs(employer_id: str | None = None):
    """employer_id verilirse sadece o isverenin ilanlari donuyor
    ('Ilanlarim' gorunumu). Verilmezse tum ilanlar doner - bu sadece
    ic/gelecekteki kullanimlar icin, frontend her zaman employer_id
    gonderiyor."""
    conn = get_db()
    if employer_id:
        rows = conn.execute(
            "SELECT * FROM jobs WHERE employer_id = ? ORDER BY created_at DESC", (employer_id,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
    conn.close()
    return {"jobs": [dict(r) for r in rows]}


@router.delete("/{job_id}")
async def delete_job(job_id: str, employer_id: str | None = None):
    conn = get_db()
    job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if job and job["employer_id"] and job["employer_id"] != employer_id:
        conn.close()
        raise HTTPException(status_code=403, detail="Bu ilan size ait değil")

    conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    conn.execute("DELETE FROM match_cache WHERE job_id = ?", (job_id,))
    conn.execute("DELETE FROM favorites WHERE job_id = ?", (job_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted"}


@router.get("/{job_id}/candidates")
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

    scored = []
    for candidate in candidate_list:
        score, explanation = matching_service.get_or_compute_match(conn, candidate, job_dict)
        scored.append((candidate, score, explanation))

    conn.commit()
    conn.close()

    results = [matching.build_candidate_entry(c, score, explanation) for c, score, explanation in scored]
    results.sort(key=lambda x: x["similarity_score"], reverse=True)
    return {"candidates": results, "job_title": job_dict["title"]}
