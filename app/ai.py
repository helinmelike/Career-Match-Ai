"""LLM cagrilarini LangChain zincirleri araciligiyla yapan katman.

Onceki versiyonda her fonksiyon dogrudan `client.chat.completions.create(...)`
cagirip donen metni `json.loads` ile parse ediyordu - format tamamen prompt
talimatina baglıydı ve model bazen buna uymuyordu. Burada `with_structured_output`
kullaniliyor: LangChain, verdigimiz Pydantic modelini OpenAI'nin function-calling
semasina cevirip modelin CEVABINI o semaya UYMAYA ZORLUYOR. Ozellikle
RequirementEvaluation.durum gibi Literal alanlar icin bu, "karsilaniyor" disinda
bir deger donmesini API seviyesinde imkansiz kilar.
"""
import os
import json
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from . import prompts as p
from .schemas import CVAnalysis, JobAnalysis, MatchEvaluation

# load_dotenv()'in otomatik/goreceli aramasina guvenmek yerine, .env'i hem
# proje kok klasorunde (app/'in bir ust dizini) hem de app/ klasorunun
# icinde ariyoruz - kullanicinin .env'i nereye koydugundan bagimsiz calissin.
_APP_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _APP_DIR.parent
load_dotenv(_PROJECT_ROOT / ".env")
load_dotenv(_APP_DIR / ".env", override=False)

_api_key = os.getenv("OPENAI_API_KEY")
if not _api_key:
    raise RuntimeError(
        "OPENAI_API_KEY bulunamadi. .env dosyasinin "
        f"'{_PROJECT_ROOT}' veya '{_APP_DIR}' klasorunde oldugundan ve "
        "icinde 'OPENAI_API_KEY=...' satirinin (tirnaksiz, bosluksuz) "
        "bulundugundan emin ol."
    )

# CV/ilan analizi icin hafif bir yaraticilik payi birakiyoruz (temperature=0.3).
_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3, api_key=_api_key)

# Eslestirme (checklist) tamamen siniflandirma gorevi oldugu icin temperature=0:
# ayni CV+ilan cifti her zaman ayni checklist'i uretmeli.
_llm_deterministic = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=_api_key)

_cv_analysis_chain = ChatPromptTemplate.from_template(p.CV_ANALYSIS_PROMPT) | _llm.with_structured_output(CVAnalysis)
_job_analysis_chain = ChatPromptTemplate.from_template(p.JOB_ANALYSIS_PROMPT) | _llm.with_structured_output(JobAnalysis)
_match_chain = (
    ChatPromptTemplate.from_template(p.MATCH_EXPLANATION_PROMPT)
    | _llm_deterministic.with_structured_output(MatchEvaluation)
)


def analyze_cv(cv_text: str) -> dict:
    """CV metnini analiz eder. Donus degeri her zaman duz dict - cagiran
    kod (main.py, matching.py) Pydantic'ten habersiz kalir, sadece ai.py
    icinde structured output icin Pydantic kullanilir."""
    result: CVAnalysis = _cv_analysis_chain.invoke({"cv_text": cv_text})
    return result.model_dump()


def analyze_job(job_text: str) -> dict:
    result: JobAnalysis = _job_analysis_chain.invoke({"job_text": job_text})
    return result.model_dump()


def explain_match(cv_analysis: dict, cv_text: str, job_analysis: dict, job_text: str) -> dict:
    result: MatchEvaluation = _match_chain.invoke(
        {
            "cv_analysis": json.dumps(cv_analysis, ensure_ascii=False),
            "cv_text": cv_text,
            "job_analysis": json.dumps(job_analysis, ensure_ascii=False),
            "job_text": job_text,
        }
    )
    return result.model_dump()