"""Checklist tabanli deterministik skorlama.

Skor modelden dogrudan istenmiyor; model (ai.py araciligiyla) sadece her
gereksinim icin durum tespiti yapiyor, nihai skoru bu modul hesapliyor.
Boylece ayni CV+ilan cifti her zaman ayni skoru uretir. Bu modul kasitli
olarak LangChain/OpenAI'den bagimsiz - sadece dict/list uzerinde calisir,
boylece LLM cagrisi yapmadan izole test edilebilir.
"""
import re

ZORUNLU_AGIRLIK = 1.0
TERCIH_AGIRLIK = 0.4
DURUM_CARPANI = {"karsilaniyor": 1.0, "kismen": 0.5, "karsilanmiyor": 0.0}
DENEYIM_SIRASI = {"junior": 1, "mid": 2, "senior": 3}
DENEYIM_FARKI_CEZASI = 15.0  # her seviye farki icin skordan dusulen puan

_TR_FOLD = str.maketrans({
    "ş": "s", "ı": "i", "ç": "c", "ğ": "g", "ü": "u", "ö": "o",
    "Ş": "s", "İ": "i", "Ç": "c", "Ğ": "g", "Ü": "u", "Ö": "o",
})

_STOPWORDS_TR_EN = {
    "ve", "ile", "icin", "deneyimi", "deneyim", "kullanarak", "gelistirme", "gelistirilmesi",
    "sistemi", "sistemleri", "mimarisi", "mimarileri", "seviyesinde", "seviyesi", "temelleri",
    "temel", "entegrasyon", "entegrasyonu", "entegrasyonlari", "entegrasyonlarina", "asinalik",
    "bilgisi", "hakimiyet", "hakimiyeti", "gibi", "veya", "olan", "olmasi", "calismasi",
    "yonetimi", "takim", "ekip", "iletisim", "proje", "projeleri", "becerisi", "becerileri",
    "yetkinlik", "yetkinligi", "sartlari", "with", "and", "of", "in", "on", "for", "using",
    "development", "experience", "skills", "management", "knowledge", "the", "a", "an", "to",
    "or", "etc", "tabanli", "destekli", "uzerine", "hakkinda", "konusunda", "aranan", "artik",
}


def _fold(s: str) -> str:
    return (s or "").strip().lower().translate(_TR_FOLD)


def normalize_durum(raw: str) -> str:
    """Modelin dondurdugu durum degerini kanonik forma cevirir.

    with_structured_output + Literal tipi kullandigimiz icin bu artik cogu
    zaman gereksiz (model zaten sadece 3 kanonik degerden birini donebilir),
    ama eski (Literal-oncesi donemden kalma) match_cache kayitlari veya
    ileride farkli bir saglayiciya gecilirse diye ikinci bir guvence katmani
    olarak tutuluyor.
    """
    s = _fold(raw)
    if not s:
        return "kismen"
    if "kismen" in s or "kismi" in s:
        return "kismen"
    if "miyor" in s or "muyor" in s or " yok" in s or s == "yok" or "degil" in s or "hayir" in s:
        return "karsilanmiyor"
    if "iyor" in s or "landi" in s or "evet" in s or "var" in s:
        return "karsilaniyor"
    return "kismen"


def normalize_tur(raw: str) -> str:
    s = _fold(raw)
    return "tercih" if "tercih" in s else "zorunlu"


def find_cv_evidence(requirement: str, cv_terms: list, cv_text: str):
    """Gereksinim CV'de gercekten geciyor mu, deterministik olarak kontrol eder."""
    req_folded = _fold(requirement)
    if not req_folded:
        return None

    for term in cv_terms:
        term_folded = _fold(term)
        if len(term_folded) >= 2 and (term_folded in req_folded or req_folded in term_folded):
            return term

    cv_text_folded = _fold(cv_text)
    for token in re.findall(r"[a-z0-9]+", req_folded):
        if len(token) < 3 or token in _STOPWORDS_TR_EN:
            continue
        if token in cv_text_folded:
            return token

    return None


def apply_evidence_safety_net(gereksinimler: list, cv_analysis: dict, cv_text: str) -> None:
    """gereksinimler listesini yerinde degistirir: 'karsilanmiyor' olan ama CV'de
    aslinda kaniti bulunan ogeleri 'kismen'e yukseltir. Asla 'karsilaniyor'a
    yukseltmez - sadece yanlis negatifi telafi eder."""
    cv_terms = list(cv_analysis.get("teknik_beceriler") or []) + list(cv_analysis.get("diger_nitelikler") or [])
    for g in gereksinimler:
        if g.get("durum") != "karsilanmiyor":
            continue
        evidence = find_cv_evidence(g.get("gereksinim", ""), cv_terms, cv_text)
        if evidence:
            g["durum"] = "kismen"
            g["kanit"] = f"[Otomatik kontrol] CV'de '{evidence}' terimi tespit edildi (ilk degerlendirme bunu atlamisti)."


def compute_match_score(gereksinimler: list, cv_deneyim: str, job_deneyim: str) -> float:
    total_weight = 0.0
    earned = 0.0
    for item in gereksinimler:
        tur = normalize_tur(item.get("tur"))
        durum = normalize_durum(item.get("durum"))
        weight = ZORUNLU_AGIRLIK if tur == "zorunlu" else TERCIH_AGIRLIK
        multiplier = DURUM_CARPANI.get(durum, 0.0)
        total_weight += weight
        earned += weight * multiplier

    base_score = (earned / total_weight * 100) if total_weight > 0 else 0.0

    cv_ord = DENEYIM_SIRASI.get(_fold(cv_deneyim))
    job_ord = DENEYIM_SIRASI.get(_fold(job_deneyim))
    penalty = 0.0
    if cv_ord and job_ord and job_ord > cv_ord:
        penalty = (job_ord - cv_ord) * DENEYIM_FARKI_CEZASI

    return round(max(0.0, min(100.0, base_score - penalty)), 1)


def recommendation_from_score(score: float) -> str:
    if score >= 80:
        return "evet"
    if score >= 50:
        return "kismen"
    return "hayir"
