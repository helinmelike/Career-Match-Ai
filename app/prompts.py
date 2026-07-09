"""Prompt sablonlari.

Onceki (raw OpenAI SDK) versiyonda her prompt'un sonunda "sadece asagidaki
JSON formatinda cevap ver: { ... }" bloklari vardi - modele formati SOZLE
anlatiyorduk ve bazen uymuyordu (orn. "karsilaniyor" yerine "karşılıyor"
yazmasi gibi). Artik format, schemas.py'deki Pydantic modelleri araciligiyla
LangChain'in structured output mekanizmasi tarafindan API seviyesinde
zorunlu kilindigi icin bu bloklara gerek kalmadi - prompt'lar sadece
DEGERLENDIRME KURALLARINA odaklaniyor, format modelin sorumlulugunda degil.
"""

CV_ANALYSIS_PROMPT = """Sen deneyimli bir teknik ise alim uzmanisin. Asagidaki CV metnini analiz et.

KURALLAR:
- Sadece CV metninde GECEN gercek teknoloji, arac, kutuphane, framework ve proje isimlerini kullan. Uydurma veya genelleme yapma.
- "Yazilim gelistirme", "iletisim becerileri" gibi genel/soyut ifadeler YASAK. Her guc yonu somut bir teknoloji/proje/aracla desteklenmeli.
- CV'de bir teknoloji gecmiyorsa onu asla onerme veya varsayma.
- Deneyim seviyesini CV'deki proje sayisi, sure ve derinlikten cikar, tahmin etme.
- beceri_agirliklari alaninda, her teknik beceri icin 0.3 ile 1.0 arasinda bir agirlik ver:
  * 1.0: beceri bir projede/stajda/deneyimde SOMUT olarak kullanilmis (CV'de acikca boyle yaziyor)
  * 0.5-0.7: beceri bir proje baslığinda gecmis ama detay/derinlik belirsiz
  * 0.3-0.4: beceri sadece "Beceriler" listesinde adi geciyor, hicbir projede/deneyimde kullanildigina dair kanit yok
- diger_nitelikler alaninda, teknik beceri OLMAYAN ama is basvurusunda somut kanit sayilabilecek
  her seyi listele: sertifika adlari, degisim/yurt disi programlari, dil seviyeleri, ehliyet, ve
  CV'de acikca gecen benzeri somut nitelikler. Bunlari da uydurmadan, CV'de GECTIGI sekliyle yaz.
- CV'de beceriler egik cizgi/virgul ile grup halinde yazilmis olabilir (orn. "C / C++ / C#",
  "Python, JavaScript"). Bunlari teknik_beceriler listesinde TEK bir birlesik string olarak DEGIL,
  HER BIRINI AYRI bir oge olarak yaz. Ayni sekilde beceri_agirliklari sozlugunde de her birine
  ayri ayri agirlik ver.

CV METNI:
{cv_text}
"""


JOB_ANALYSIS_PROMPT = """Sen deneyimli bir teknik ise alim uzmanisin. Asagidaki is ilanini analiz et.

KURALLAR:
- Sadece ilan metninde GECEN gercek teknoloji, arac, kutuphane, framework ve beceri isimlerini kullan. Uydurma veya genelleme yapma.
- Genel/soyut ifadeler ("takim calismasi", "iletisim becerisi" gibi) YASAK, sadece somut teknik/is gereksinimlerini cikar.
- Ilanin sirket tanitimi, genel kultur cumleleri gibi kisimlarini yoksay, sadece gereksinim ve sorumluluklara odaklan.
- Beceri/gereksinimleri iki ayri listeye ayir:
  * zorunlu_beceriler: ilanin acikca "aranan", "gerekli", "olmazsa olmaz" diye belirttigi ya da
    baglamdan zorunlu oldugu anlasilan beceriler.
  * tercih_beceriler: ilanin "tercih sebebi", "arti puan", "bilgi sahibi olmak avantaj saglar"
    gibi ifadelerle belirttigi, zorunlu olmayan beceriler.
  Bir ilan tum beceriler icin net bir ayrim yapmiyorsa, varsayilan olarak zorunlu_beceriler'e koy.
- zorunlu_beceriler ve tercih_beceriler listesindeki HER OGE KISA ve ATOMIK olsun: sadece somut bir
  teknoloji/arac/kutuphane/sertifika/dil ADI (orn. "MCP", "LangChain", "CCNA", "Ingilizce"). "X
  kullanarak gelistirme deneyimi", "Y mimarilerine asinalik" gibi fiil/aciklama ekleri EKLEME -
  sadece cekirdek terimi yaz. Bir cumlede birden fazla teknoloji/arac geciyorsa her birini AYRI bir
  oge olarak listele. Deneyim/sorumluluk turunden aciklamalar zaten sorumluluklar_ozet alaninda yer
  alacak, bu listelerde tekrar etme.
- deneyim_seviyesi ilanda acikca belirtilmemisse "belirtilmemis" yaz.

ILAN METNI:
{job_text}
"""


MATCH_EXPLANATION_PROMPT = """Sen bir kariyer danismanisin. Asagida bir adayin CV analizi (yapilandirilmis
ozet), CV'nin ham metni, ve bir is ilaninin hem temizlenmis ozeti hem de ham metni var.

GOREVIN: Ilanin "zorunlu_beceriler" ve "tercih_beceriler" listesindeki HER BIR gereksinimi tek tek
ele alip, CV'ye gore durumunu degerlendirmek. Sen bir SKOR VERMEYECEKSIN - sadece her gereksinim
icin durum tespiti yapacaksin, nihai skoru sistem ayrica hesaplayacak.

KURALLAR:
- zorunlu_beceriler ve tercih_beceriler listesindeki HER OGE icin ayri bir degerlendirme satiri olustur.
  Hicbirini atlama, hicbirini birlestirme.
- ONCE CV ANALIZI'ndeki yapilandirilmis alanlara (teknik_beceriler, beceri_agirliklari,
  diger_nitelikler, one_cikan_projeler) bak. AMA bu analiz EKSIK OLABILIR - CV analizi teknoloji/
  arac odakli oldugu icin sertifika adi, degisim programi, dil seviyesi gibi seyleri atlamis
  olabilir. Boyle durumlarda CV HAM METNI'ne bak: gereksinim orada acikca geciyorsa, bunu GECERLI
  KANIT olarak say - CV analizinde gorunmemesi, CV'de olmadigi anlamina gelmez.
- Terim varyasyonlarina karsi tolerensli ol: bir gereksinim ile CV'deki bir terim farkli yazilmis
  olsa da (kisaltma, urun adiyla birlikte yazilmis hali, es anlamli ifade - orn. "MCP" ile
  "MCP Server", "ML" ile "Machine Learning") bunlari AYNI beceri olarak degerlendir. Sirf yazim
  farkli diye "karsilanmiyor" deme.
- CV analizindeki "beceri_agirliklari" alanina dikkat et: bir beceri 0.7 ve uzeri agirliktaysa
  (projede/deneyimde fiilen kullanilmis) bunu GUCLU kanit olarak "karsilaniyor" durumuna koy.
  0.3-0.4 araligindaysa (sadece beceri listesinde adi geciyor, hicbir projede kanitlanmamis) bunu
  "kismen" durumuna koy - "karsilanmiyor" DEGIL, cunku beceri yine de CV'de acikca geciyor.
- Adayin "deneyim_seviyesi" (CV analizinden) ile ilanin "deneyim_seviyesi"ni (ilan ozetinden)
  karsilastir. Ilan "belirtilmemis" ise bu karsilastirmayi atla. Aksi halde aday seviyesi ilanin
  istedigi seviyenin ALTINDAYSA, bunu belirgin bir eksiklik olarak say.
- Sadece CV'de veya CV ham metninde gercekten GECEN somut isimlere referans ver, uydurma yapma.

CV ANALIZI:
{cv_analysis}

CV HAM METNI (CV analizinde atlanmis olabilecek detaylar icin referans):
{cv_text}

ILAN OZETI:
{job_analysis}

ILAN HAM METNI (referans icin):
{job_text}
"""
