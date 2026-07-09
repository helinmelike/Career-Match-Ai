// Aday tarafi: giris, CV yukleme/guncelleme, profil, eslesmeler, favoriler.
import { state, showView } from './state.js';
import { renderReqList } from './render-helpers.js';

export async function doLogin() {
  const email = document.getElementById('loginEmail').value.trim();
  const password = document.getElementById('loginPassword').value;
  if (!email || !password) {
    alert('E-posta ve şifre gerekli');
    return;
  }

  document.getElementById('loginStatus').innerHTML = '<span class="spinner"></span>Kontrol ediliyor...';

  const res = await fetch('/candidates/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (res.ok) {
    const data = await res.json();
    state.currentCandidate = data;
    document.getElementById('loginStatus').innerText = '';
    showJobsView();
  } else {
    const err = await res.json().catch(() => ({}));
    document.getElementById('loginStatus').innerHTML =
      `<span style="color:var(--danger-text);">${err.detail || 'Giriş başarısız'}</span> <a onclick="showView('seekerRegister')" style="color:var(--secondary); cursor:pointer; font-weight:600;">Kayıt Ol</a>`;
  }
}
window.doLogin = doLogin;

export async function doSeekerPasswordReset() {
  const name = document.getElementById('seekerResetName').value.trim();
  const email = document.getElementById('seekerResetEmail').value.trim();
  const new_password = document.getElementById('seekerResetNewPassword').value;
  if (!name || !email || !new_password) {
    alert('Tüm alanlar gerekli');
    return;
  }
  document.getElementById('seekerResetStatus').innerHTML = '<span class="spinner"></span>Kontrol ediliyor...';

  const res = await fetch('/candidates/reset-password', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, email, new_password }),
  });
  if (res.ok) {
    document.getElementById('seekerResetStatus').innerHTML =
      '<span style="color:var(--success-text); font-weight:600;">Şifren güncellendi, şimdi giriş yapabilirsin.</span>';
    document.getElementById('loginEmail').value = email;
  } else {
    const err = await res.json().catch(() => ({}));
    document.getElementById('seekerResetStatus').innerHTML =
      `<span style="color:var(--danger-text);">${err.detail || 'Sıfırlama başarısız'}</span>`;
  }
}
window.doSeekerPasswordReset = doSeekerPasswordReset;

export async function uploadCv() {
  const fileInput = document.getElementById('cvFile');
  if (!fileInput.files.length) {
    alert('Önce bir PDF seç');
    return;
  }
  const password = document.getElementById('candPassword').value;
  if (password.length < 6) {
    alert('Şifre en az 6 karakter olmalı');
    return;
  }

  document.getElementById('uploadStatus').innerHTML = '<span class="spinner"></span>CV analiz ediliyor, bu biraz sürebilir...';

  const formData = new FormData();
  formData.append('name', document.getElementById('candName').value.trim());
  formData.append('email', document.getElementById('candEmail').value.trim());
  formData.append('password', password);
  formData.append('file', fileInput.files[0]);

  const res = await fetch('/candidates', { method: 'POST', body: formData });
  if (res.ok) {
    const data = await res.json();
    state.currentCandidate = data;
    document.getElementById('uploadStatus').innerText = '';
    showJobsView();
  } else {
    const err = await res.json().catch(() => ({}));
    document.getElementById('uploadStatus').innerHTML =
      `<span style="color:var(--danger-text);">${err.detail || 'Kayıt başarısız'}</span>`;
  }
}
window.uploadCv = uploadCv;

export function toggleCvUpdateForm() {
  const form = document.getElementById('cvUpdateForm');
  form.style.display = form.style.display === 'none' ? 'block' : 'none';
}
window.toggleCvUpdateForm = toggleCvUpdateForm;

export async function submitCvUpdate() {
  const fileInput = document.getElementById('cvUpdateFile');
  if (!fileInput.files.length) {
    alert('Önce bir PDF seç');
    return;
  }

  document.getElementById('cvUpdateStatus').innerHTML =
    '<span class="spinner"></span>CV yeniden analiz ediliyor, bu biraz sürebilir...';

  const formData = new FormData();
  formData.append('file', fileInput.files[0]);

  const res = await fetch('/candidates/' + state.currentCandidate.id + '/cv', { method: 'PUT', body: formData });
  const data = await res.json();
  state.currentCandidate.cv_analysis = data.cv_analysis;

  document.getElementById('cvUpdateStatus').innerText = 'CV güncellendi, ilanlar yeniden değerlendiriliyor...';
  document.getElementById('matchesContainer').innerHTML =
    '<div class="empty-state"><span class="spinner"></span>İlanlar eşleştiriliyor...</div>';

  const matchRes = await fetch('/candidates/' + state.currentCandidate.id + '/matches');
  const matchData = await matchRes.json();
  state.lastMatchesData = matchData;
  renderMatches(matchData);

  document.getElementById('cvUpdateStatus').innerText = 'CV güncellendi.';
  document.getElementById('cvUpdateFile').value = '';
}
window.submitCvUpdate = submitCvUpdate;

export async function saveProfile() {
  const payload = {
    phone: document.getElementById('profilePhone').value.trim(),
    linkedin: document.getElementById('profileLinkedin').value.trim(),
    github: document.getElementById('profileGithub').value.trim(),
    location: document.getElementById('profileLocation').value.trim(),
  };
  document.getElementById('profileStatus').innerHTML = '<span class="spinner"></span>Kaydediliyor...';

  const res = await fetch('/candidates/' + state.currentCandidate.id + '/profile', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  state.currentCandidate.phone = data.phone;
  state.currentCandidate.linkedin = data.linkedin;
  state.currentCandidate.github = data.github;
  state.currentCandidate.location = data.location;

  document.getElementById('profileStatus').innerHTML = '<span class="profile-saved-msg">✓ Kaydedildi</span>';
}
window.saveProfile = saveProfile;

function populateSidebar() {
  const c = state.currentCandidate;
  document.getElementById('sidebarName').innerText = c.name;
  document.getElementById('profilePhone').value = c.phone || '';
  document.getElementById('profileLinkedin').value = c.linkedin || '';
  document.getElementById('profileGithub').value = c.github || '';
  document.getElementById('profileLocation').value = c.location || '';
  document.getElementById('profileStatus').innerText = '';

  const summaryEl = document.getElementById('sidebarCvSummary');
  const analysis = c.cv_analysis;
  if (analysis && analysis.teknik_beceriler && analysis.teknik_beceriler.length > 0) {
    const levelLabel = { junior: 'Junior', mid: 'Mid', senior: 'Senior' }[analysis.deneyim_seviyesi] || analysis.deneyim_seviyesi || '';
    summaryEl.innerHTML = `
      ${levelLabel ? `<div class="sidebar-level">Deneyim: <strong style="color:var(--primary);">${levelLabel}</strong></div>` : ''}
      <div>${analysis.teknik_beceriler.slice(0, 8).map((s) => `<span class="tag">${s}</span>`).join('')}</div>
    `;
  } else {
    summaryEl.innerHTML = '';
  }
}

export async function showJobsView() {
  showView('jobsView');
  populateSidebar();
  document.getElementById('matchesContainer').innerHTML =
    '<div class="empty-state"><span class="spinner"></span>İlanlar eşleştiriliyor...</div>';
  document.getElementById('favFilterCheckbox').checked = false;

  const res = await fetch('/candidates/' + state.currentCandidate.id + '/matches');
  const data = await res.json();
  state.lastMatchesData = data;
  renderMatches(data);
}
window.showJobsView = showJobsView;

export function toggleFavoritesFilter() {
  if (state.lastMatchesData) renderMatches(state.lastMatchesData);
}
window.toggleFavoritesFilter = toggleFavoritesFilter;

export async function toggleFavorite(jobId, btnEl) {
  const isFav = btnEl.classList.contains('active');
  if (isFav) {
    await fetch('/candidates/' + state.currentCandidate.id + '/favorites/' + jobId, { method: 'DELETE' });
    btnEl.classList.remove('active');
    btnEl.innerText = '☆';
  } else {
    await fetch('/candidates/' + state.currentCandidate.id + '/favorites/' + jobId, { method: 'POST' });
    btnEl.classList.add('active');
    btnEl.innerText = '★';
  }
  if (state.lastMatchesData) {
    ['suitable', 'others'].forEach((key) => {
      const entry = (state.lastMatchesData[key] || []).find((e) => e.job_id === jobId);
      if (entry) entry.is_favorite = !isFav;
    });
  }
}
window.toggleFavorite = toggleFavorite;

function renderMatches(data) {
  const container = document.getElementById('matchesContainer');
  const onlyFav = document.getElementById('favFilterCheckbox').checked;

  const suitable = onlyFav ? data.suitable.filter((r) => r.is_favorite) : data.suitable;
  const others = onlyFav ? data.others.filter((r) => r.is_favorite) : data.others;

  if (data.suitable.length === 0 && data.others.length === 0) {
    container.innerHTML = '<div class="empty-state">Sistemde henüz ilan yok.</div>';
    return;
  }
  if (onlyFav && suitable.length === 0 && others.length === 0) {
    container.innerHTML =
      '<div class="empty-state">Henüz favori ilanın yok. Bir ilanı favorilemek için ★ ikonuna tıkla.</div>';
    return;
  }

  let html = '';

  if (suitable.length > 0) {
    html += '<div class="section-label">Sana Uygun İlanlar</div>';
    suitable.forEach((r) => {
      html += `
        <div class="card match-card">
          <div style="display:flex; justify-content:space-between; align-items:flex-start;">
            <div><span class="score-badge">%${r.similarity_score}</span><strong>${r.job_title}</strong> ${r.company ? '<span style="color:var(--muted); font-size:13px;">— ' + r.company + '</span>' : ''}</div>
            <button class="fav-btn ${r.is_favorite ? 'active' : ''}" onclick="toggleFavorite('${r.job_id}', this)" title="Favorile">${r.is_favorite ? '★' : '☆'}</button>
          </div>
          <p style="font-size:14px; margin:10px 0;">${r.kisa_degerlendirme}</p>
          <div style="margin-bottom:6px;">${r.eslesen_beceriler.map((s) => `<span class="tag">${s}</span>`).join('')}</div>
          <div style="margin-bottom:8px;">${r.eksik_beceriler.map((s) => `<span class="tag missing">${s}</span>`).join('')}</div>
          <span class="recommend ${r.tavsiye_edilir_mi}">${r.tavsiye_edilir_mi === 'evet' ? 'Tavsiye edilir' : r.tavsiye_edilir_mi === 'kismen' ? 'Kısmen uygun' : 'Uygun değil'}</span>
          <div>
            <button id="toggle-${r.job_id}" class="detail-toggle" onclick="toggleReqList('${r.job_id}')">
              <span class="arrow">▶</span><span class="label">Detaylı değerlendirmeyi gör</span>
            </button>
          </div>
          <div id="req-${r.job_id}" class="req-list">${renderReqList(r.gereksinim_degerlendirmesi)}</div>
        </div>
      `;
    });
  }

  if (others.length > 0) {
    html += '<div class="section-label">Diğer İlanlar</div>';
    others.forEach((r) => {
      html += `
        <div class="other-job-card">
          <div class="other-job-row" onclick="toggleOtherDetail('${r.job_id}')">
            <div><strong>${r.job_title}</strong> ${r.company ? '<span style="color:var(--muted);"> — ' + r.company + '</span>' : ''}</div>
            <div style="display:flex; align-items:center; gap:10px;">
              <button class="fav-btn ${r.is_favorite ? 'active' : ''}" onclick="event.stopPropagation(); toggleFavorite('${r.job_id}', this)" title="Favorile">${r.is_favorite ? '★' : '☆'}</button>
              <div class="score">%${r.similarity_score}</div>
            </div>
          </div>
          <div id="other-detail-${r.job_id}" class="other-job-detail">
            ${r.kisa_degerlendirme ? `<div class="other-job-eval">${r.kisa_degerlendirme}</div>` : ''}
            ${renderReqList(r.gereksinim_degerlendirmesi)}
          </div>
        </div>
      `;
    });
  }

  container.innerHTML = html;
}
