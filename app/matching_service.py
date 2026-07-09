"""Aday-ilan eslestirmesini hesaplayan/getiren ortak katman.

Hem 'bir adaya uygun ilanlar' (candidate->jobs) hem 'bir ilana uygun
adaylar' (job->candidates) endpoint'i, ayni (aday, ilan) cifti icin ayni
eslesme mantigini kullanir. Bu modul o mantigi TEK YERDE tutar - iki
endpoint de buradan cagirir, boylece kod tekrari ve iki tarafin farkli
davranmasi riski olmaz.
"""
import json
from datetime import datetime

from . import ai, matching


def get_or_compute_match(conn, candidate: dict, job: dict) -> tuple[float, dict]:
    """Verilen (aday, ilan) cifti icin skor+aciklamayi dondurur.

    Onceden hesaplanmissa match_cache'den okur, degilse GPT ile hesaplayip
    cache'e yazar. Commit islemi CAGIRAN tarafindan yapilmali (ayni conn
    uzerinde birden fazla cift islenirken tek seferde commit etmek icin).
    """
    cached = conn.execute(
        "SELECT score, explanation FROM match_cache WHERE candidate_id = ? AND job_id = ?",
        (candidate["id"], job["id"]),
    ).fetchone()
    if cached:
        return cached["score"], json.loads(cached["explanation"])

    cv_analysis = json.loads(candidate["cv_analysis"])

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
        (candidate["id"], job["id"], score, json.dumps(explanation, ensure_ascii=False), datetime.utcnow().isoformat()),
    )
    return score, explanation
