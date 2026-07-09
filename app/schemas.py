"""Pydantic semalari - LLM ciktilarini API seviyesinde zorunlu kilmak icin.

Bu modeller LangChain'in with_structured_output() ile birlikte kullaniliyor.
OpenAI, bu semayi bir function-calling/JSON-schema tanimina cevirip modelin
CEVABINI bu semaya UYMAYA ZORLUYOR - yani "durum" alani icin model artik
sadece Literal olarak tanimladigimiz 3 degerden birini secebilir, "karşılıyor"
gibi diakritikli/serbest bir varyant DONDUREMEZ. Bu, daha once prompt
talimatiyla ("sadece ASCII yaz") cozmeye calistigimiz ve modelin zaman zaman
gormezden geldigi sorunu kaynagindan cozer.
"""
from typing import Dict, List, Literal

from pydantic import BaseModel, Field

DeneyimSeviyesi = Literal["junior", "mid", "senior", "belirtilmemis"]


class CVAnalysis(BaseModel):
    teknik_beceriler: List[str] = Field(description="CV'de gecen somut teknoloji/arac isimleri, HER BIRI ayri bir oge")
    beceri_agirliklari: Dict[str, float] = Field(
        default_factory=dict,
        description="Her teknik beceri icin 0.3-1.0 arasi kanit agirligi",
    )
    diger_nitelikler: List[str] = Field(
        default_factory=list,
        description="Sertifika, degisim programi, dil seviyesi gibi teknik olmayan somut nitelikler",
    )
    guclu_yonler: List[str] = Field(default_factory=list)
    gelisim_alanlari: List[str] = Field(default_factory=list)
    deneyim_seviyesi: Literal["junior", "mid", "senior"]
    one_cikan_projeler: List[str] = Field(default_factory=list)
    uygun_pozisyonlar: List[str] = Field(default_factory=list)


class JobAnalysis(BaseModel):
    pozisyon_ozeti: str
    zorunlu_beceriler: List[str] = Field(description="KISA/ATOMIK teknoloji-arac-beceri adlari")
    tercih_beceriler: List[str] = Field(default_factory=list, description="KISA/ATOMIK teknoloji-arac-beceri adlari")
    sorumluluklar_ozet: List[str] = Field(default_factory=list)
    deneyim_seviyesi: DeneyimSeviyesi


class RequirementEvaluation(BaseModel):
    gereksinim: str
    tur: Literal["zorunlu", "tercih"]
    durum: Literal["karsilaniyor", "kismen", "karsilanmiyor"]
    kanit: str = Field(description="CV'deki somut referans veya 'kanit yok'")


class MatchEvaluation(BaseModel):
    gereksinim_degerlendirmesi: List[RequirementEvaluation]
    kisa_degerlendirme: str
