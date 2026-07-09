// Paylasilan uygulama durumu ve gorunum (view) gecisleri.
// Diger tum modullerin ortak referans noktasi burasi - "currentCandidate"
// gibi bagimsiz global degiskenler yerine tek bir `state` nesnesi kullaniliyor,
// cunku ES module import'lari salt-okunur baglama yapiyor (bir modulden
// import edilen bir `let` degiskenine baska bir moduldenn deger atanamiyor).
// Nesne mutasyonu bu kisitlamayi asiyor.
export const state = {
  currentCandidate: null,
  currentEmployer: null,
  lastMatchesData: null,
  allJobs: [],
  editingJobId: null,
};

export const VIEW_MAP = {
  landing: 'landing',
  employer: 'employerEntry',
  employerEntry: 'employerEntry',
  employerLogin: 'employerLogin',
  employerRegister: 'employerRegister',
  employerForgotPassword: 'employerForgotPassword',
  employerView: 'employerView',
  seeker: 'seekerEntry',
  seekerEntry: 'seekerEntry',
  seekerLogin: 'seekerLogin',
  seekerRegister: 'seekerRegister',
  seekerForgotPassword: 'seekerForgotPassword',
  jobsView: 'jobsView',
  jobCandidatesView: 'jobCandidatesView',
};

export const ALL_VIEWS = [
  'landing', 'employerEntry', 'employerLogin', 'employerRegister', 'employerForgotPassword', 'employerView',
  'seekerEntry', 'seekerLogin', 'seekerRegister', 'seekerForgotPassword', 'jobsView', 'jobCandidatesView',
];

export function showView(view) {
  const targetId = VIEW_MAP[view] || view;
  ALL_VIEWS.forEach((v) => {
    document.getElementById(v).style.display = v === targetId ? 'block' : 'none';
  });
  if (targetId === 'employerView') {
    // employer.js zaten bu dosyayi (state.js) statik olarak import ediyor,
    // dairesel bagimliliktan kacinmak icin burada dinamik import kullaniliyor.
    import('./employer.js').then((m) => m.loadJobs());
  }
  updateNav();
}

// index.html'deki inline onclick="showView(...)" cagirilarinin calismasi
// icin fonksiyon global (window) kapsamina da eklenmeli - ES module'lerde
// top-level fonksiyonlar otomatik global olmuyor.
window.showView = showView;

export function updateNav() {
  const linksEl = document.getElementById('navLinks');
  const userEl = document.getElementById('navUser');
  if (!linksEl || !userEl) return;

  if (state.currentCandidate) {
    linksEl.innerHTML = `<a class="nav-link" onclick="showJobsView()">İlanlar</a>`;
    userEl.innerHTML = `<span class="nav-username">${state.currentCandidate.name}</span><button class="ghost nav-logout" onclick="logout()">Çıkış</button>`;
  } else if (state.currentEmployer) {
    linksEl.innerHTML = `<a class="nav-link" onclick="showView('employerView')">İlanlarım</a><a class="nav-link" onclick="goToNewJob()">Yeni İlan</a>`;
    userEl.innerHTML = `<span class="nav-username">${state.currentEmployer.company_name}</span><button class="ghost nav-logout" onclick="logout()">Çıkış</button>`;
  } else {
    linksEl.innerHTML = '';
    userEl.innerHTML = '';
  }
}
window.updateNav = updateNav;

export function logout() {
  state.currentCandidate = null;
  state.currentEmployer = null;
  state.lastMatchesData = null;
  showView('landing');
}
window.logout = logout;

export function goHome() {
  showView('landing');
}
window.goHome = goHome;

export async function uploadLogo() {
  const fileInput = document.getElementById('logoUploadInput');
  if (!fileInput.files.length) return;
  const formData = new FormData();
  formData.append('file', fileInput.files[0]);
  const res = await fetch('/site/logo', { method: 'POST', body: formData });
  if (res.ok) {
    document.getElementById('siteLogoImg').src = '/uploads/logo.png?t=' + Date.now();
  }
}
window.uploadLogo = uploadLogo;

// Sayfa her acildiginda: varsayilan logo.svg zaten aninda gorunuyor (stabil,
// yanip sonme yok). Eger daha once ozel bir logo yuklenmisse, onu SESSIZCE
// (goruntude bir "kirik resim" anI yaratmadan) arka planda kontrol edip
// varsa degistiriyoruz.
(async function checkUploadedLogo() {
  try {
    const res = await fetch('/uploads/logo.png', { method: 'HEAD' });
    if (res.ok) {
      document.getElementById('siteLogoImg').src = '/uploads/logo.png?t=' + Date.now();
    }
  } catch (e) {
    // sessizce yut - logo.svg zaten gorunuyor
  }
})();
