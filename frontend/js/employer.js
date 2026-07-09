// Isveren tarafi: sirket kayit/giris, ilan CRUD, arama/filtre, aday havuzu + istatistikler.
import { state, showView } from './state.js';
import { renderReqList, renderContactChips } from './render-helpers.js';

export async function doEmployerLogin() {
  const email = document.getElementById('employerLoginEmail').value.trim();
  const password = document.getElementById('employerLoginPassword').value;
  if (!email || !password) {
    alert('E-posta ve şifre gerekli');
    return;
  }
  document.getElementById('employerLoginStatus').innerHTML = '<span class="spinner"></span>Kontrol ediliyor...';

  const res = await fetch('/employers/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (res.ok) {
    const data = await res.json();
    state.currentEmployer = data;
    document.getElementById('employerLoginStatus').innerText = '';
    showView('employerView');
    document.getElementById('jobCompany').value = data.company_name;
  } else {
    const err = await res.json().catch(() => ({}));
    document.getElementById('employerLoginStatus').innerHTML =
      `<span style="color:var(--danger-text);">${err.detail || 'Giriş başarısız'}</span>`;
  }
}
window.doEmployerLogin = doEmployerLogin;

export async function doEmployerPasswordReset() {
  const company_name = document.getElementById('employerResetCompany').value.trim();
  const email = document.getElementById('employerResetEmail').value.trim();
  const new_password = document.getElementById('employerResetNewPassword').value;
  if (!company_name || !email || !new_password) {
    alert('Tüm alanlar gerekli');
    return;
  }
  document.getElementById('employerResetStatus').innerHTML = '<span class="spinner"></span>Kontrol ediliyor...';

  const res = await fetch('/employers/reset-password', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ company_name, email, new_password }),
  });
  if (res.ok) {
    document.getElementById('employerResetStatus').innerHTML =
      '<span style="color:var(--success-text); font-weight:600;">Şifreniz güncellendi, şimdi giriş yapabilirsiniz.</span>';
    document.getElementById('employerLoginEmail').value = email;
  } else {
    const err = await res.json().catch(() => ({}));
    document.getElementById('employerResetStatus').innerHTML =
      `<span style="color:var(--danger-text);">${err.detail || 'Sıfırlama başarısız'}</span>`;
  }
}
window.doEmployerPasswordReset = doEmployerPasswordReset;

export async function doEmployerRegister() {
  const company_name = document.getElementById('employerCompany').value.trim();
  const email = document.getElementById('employerRegisterEmail').value.trim();
  const password = document.getElementById('employerRegisterPassword').value;
  if (!company_name || !email || !password) {
    alert('Tüm alanlar gerekli');
    return;
  }
  document.getElementById('employerRegisterStatus').innerHTML = '<span class="spinner"></span>Hesap oluşturuluyor...';

  const res = await fetch('/employers/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ company_name, email, password }),
  });
  if (res.ok) {
    const data = await res.json();
    state.currentEmployer = data;
    document.getElementById('employerRegisterStatus').innerText = '';
    showView('employerView');
    document.getElementById('jobCompany').value = data.company_name;
  } else {
    const err = await res.json().catch(() => ({}));
    document.getElementById('employerRegisterStatus').innerHTML =
      `<span style="color:var(--danger-text);">${err.detail || 'Kayıt başarısız'}</span>`;
  }
}
window.doEmployerRegister = doEmployerRegister;

export async function loadJobs() {
  if (!state.currentEmployer) return;
  const res = await fetch('/jobs?employer_id=' + encodeURIComponent(state.currentEmployer.id));
  const data = await res.json();
  state.allJobs = data.jobs;
  const searchInput = document.getElementById('jobSearchInput');
  if (searchInput) searchInput.value = '';
  renderJobsList(state.allJobs);
}
window.loadJobs = loadJobs;

export function filterJobs() {
  const q = document.getElementById('jobSearchInput').value.trim().toLowerCase();
  if (!q) {
    renderJobsList(state.allJobs);
    return;
  }
  const filtered = state.allJobs.filter(
    (j) =>
      j.title.toLowerCase().includes(q) ||
      (j.company || '').toLowerCase().includes(q) ||
      j.text.toLowerCase().includes(q)
  );
  renderJobsList(filtered);
}
window.filterJobs = filterJobs;

function renderJobsList(jobs) {
  const container = document.getElementById('jobsList');
  if (jobs.length === 0) {
    container.innerHTML = '<div class="empty-state">Henüz ilan yayınlamadınız.</div>';
    return;
  }
  container.innerHTML = jobs
    .map(
      (j) => `
    <div class="job-row">
      <div>
        <div class="job-row-title">${j.title} ${j.company ? '<span class="job-row-company">— ' + j.company + '</span>' : ''}</div>
        <div class="job-row-preview">${j.text.slice(0, 130)}...</div>
      </div>
      <div style="display:flex; gap:8px; align-items:center;">
        <button class="ghost" onclick="showJobCandidates('${j.id}')">Adayları Gör</button>
        <button class="edit-btn" onclick="startEditJob('${j.id}')">Düzenle</button>
        <button class="del-btn" onclick="deleteJob('${j.id}')">Sil</button>
      </div>
    </div>
  `
    )
    .join('');
}

export function startEditJob(jobId) {
  const job = state.allJobs.find((j) => j.id === jobId);
  if (!job) return;
  state.editingJobId = jobId;
  document.getElementById('jobTitle').value = job.title;
  document.getElementById('jobCompany').value = job.company || '';
  document.getElementById('jobText').value = job.text;
  document.getElementById('jobFormTitle').innerText = 'İlanı Düzenle';
  document.getElementById('jobSubmitBtn').innerText = 'İlanı Güncelle';
  document.getElementById('jobCancelEditBtn').style.display = 'inline';
  document.getElementById('employerStatus').innerText = '';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}
window.startEditJob = startEditJob;

export function cancelEditJob() {
  state.editingJobId = null;
  document.getElementById('jobTitle').value = '';
  document.getElementById('jobCompany').value = state.currentEmployer ? state.currentEmployer.company_name : '';
  document.getElementById('jobText').value = '';
  document.getElementById('jobFormTitle').innerText = 'Yeni İlan';
  document.getElementById('jobSubmitBtn').innerText = 'İlanı Yayınla';
  document.getElementById('jobCancelEditBtn').style.display = 'none';
}
window.cancelEditJob = cancelEditJob;

export function goToNewJob() {
  cancelEditJob();
  showView('employerView');
  window.scrollTo({ top: 0, behavior: 'smooth' });
}
window.goToNewJob = goToNewJob;

export async function showJobCandidates(jobId) {
  showView('jobCandidatesView');
  document.getElementById('jobCandidatesHeader').innerText = 'Yükleniyor...';
  document.getElementById('jobCandidatesStats').style.display = 'none';
  document.getElementById('jobCandidatesContainer').innerHTML =
    '<div class="empty-state"><span class="spinner"></span>Adaylar eşleştiriliyor...</div>';

  const res = await fetch('/jobs/' + jobId + '/candidates');
  const data = await res.json();
  document.getElementById('jobCandidatesHeader').innerText = (data.job_title || 'İlan') + ' — Aday Havuzu';
  renderJobCandidatesStats(data.candidates || []);
  renderJobCandidates(data);
}
window.showJobCandidates = showJobCandidates;

function renderJobCandidatesStats(candidates) {
  const statsEl = document.getElementById('jobCandidatesStats');
  if (candidates.length === 0) {
    statsEl.style.display = 'none';
    return;
  }

  const total = candidates.length;
  const avg = (candidates.reduce((s, c) => s + c.similarity_score, 0) / total).toFixed(1);
  const evet = candidates.filter((c) => c.tavsiye_edilir_mi === 'evet').length;
  const kismen = candidates.filter((c) => c.tavsiye_edilir_mi === 'kismen').length;
  const hayir = candidates.filter((c) => c.tavsiye_edilir_mi === 'hayir').length;

  statsEl.style.display = 'block';
  statsEl.innerHTML = `
    <div class="stats-row">
      <div><div class="stats-num">${total}</div><div class="stats-label">Toplam Aday</div></div>
      <div><div class="stats-num" style="color:var(--secondary);">%${avg}</div><div class="stats-label">Ortalama Uyum</div></div>
      <div><div class="stats-num" style="color:var(--success-text);">${evet}</div><div class="stats-label">Tavsiye Edilir</div></div>
      <div><div class="stats-num" style="color:#B26A00;">${kismen}</div><div class="stats-label">Kısmen Uygun</div></div>
      <div><div class="stats-num" style="color:var(--danger-text);">${hayir}</div><div class="stats-label">Uygun Değil</div></div>
    </div>
  `;
}

function renderJobCandidates(data) {
  const container = document.getElementById('jobCandidatesContainer');
  if (!data.candidates || data.candidates.length === 0) {
    container.innerHTML = '<div class="empty-state">Sistemde henüz aday yok.</div>';
    return;
  }

  container.innerHTML = data.candidates
    .map(
      (c) => `
    <div class="card match-card">
      <div>
        <span class="score-badge">%${c.similarity_score}</span><strong>${c.name}</strong>
        <span style="color:var(--muted); font-size:13px;"> — ${c.email}</span>
      </div>
      ${renderContactChips(c)}
      <p style="font-size:14px; margin:10px 0;">${c.kisa_degerlendirme}</p>
      <div style="margin-bottom:6px;">${c.eslesen_beceriler.map((s) => `<span class="tag">${s}</span>`).join('')}</div>
      <div style="margin-bottom:8px;">${c.eksik_beceriler.map((s) => `<span class="tag missing">${s}</span>`).join('')}</div>
      <span class="recommend ${c.tavsiye_edilir_mi}">${c.tavsiye_edilir_mi === 'evet' ? 'Tavsiye edilir' : c.tavsiye_edilir_mi === 'kismen' ? 'Kısmen uygun' : 'Uygun değil'}</span>
      <div>
        <button id="toggle-cand-${c.candidate_id}" class="detail-toggle" onclick="toggleReqList('cand-${c.candidate_id}')">
          <span class="arrow">▶</span><span class="label">Detaylı değerlendirmeyi gör</span>
        </button>
      </div>
      <div id="req-cand-${c.candidate_id}" class="req-list">${renderReqList(c.gereksinim_degerlendirmesi)}</div>
    </div>
  `
    )
    .join('');
}

export async function deleteJob(id) {
  const employerId = state.currentEmployer ? state.currentEmployer.id : '';
  await fetch('/jobs/' + id + '?employer_id=' + encodeURIComponent(employerId), { method: 'DELETE' });
  loadJobs();
}
window.deleteJob = deleteJob;

export async function submitJob() {
  const title = document.getElementById('jobTitle').value.trim();
  const company = document.getElementById('jobCompany').value.trim();
  const text = document.getElementById('jobText').value.trim();
  if (!title || !text) {
    alert('Pozisyon adı ve ilan metni zorunlu');
    return;
  }
  const employer_id = state.currentEmployer ? state.currentEmployer.id : '';

  if (state.editingJobId) {
    document.getElementById('employerStatus').innerText = 'Güncelleniyor...';
    await fetch('/jobs/' + state.editingJobId, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ employer_id, title, company, text }),
    });
    document.getElementById('employerStatus').innerText = 'İlan güncellendi.';
    cancelEditJob();
  } else {
    document.getElementById('employerStatus').innerText = 'Kaydediliyor...';
    await fetch('/jobs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ employer_id, title, company, text }),
    });
    document.getElementById('jobTitle').value = '';
    document.getElementById('jobCompany').value = state.currentEmployer ? state.currentEmployer.company_name : '';
    document.getElementById('jobText').value = '';
    document.getElementById('employerStatus').innerText = 'İlan yayınlandı.';
  }
  loadJobs();
}
window.submitJob = submitJob;
