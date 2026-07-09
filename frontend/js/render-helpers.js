// Aday ve isveren tarafinin ikisinin de kullandigi ortak render yardimcilari:
// gereksinim checklist'i, favori/detay toggle'lari, iletisim chip'leri.

export const DURUM_ICON = { karsilaniyor: '✅', kismen: '🟡', karsilanmiyor: '❌' };
export const DURUM_LABEL = {
  karsilaniyor: 'Karşılıyor',
  kismen: 'Kısmen karşılıyor',
  karsilanmiyor: 'Karşılamıyor',
};

export function renderReqList(gereksinimler) {
  if (!gereksinimler || gereksinimler.length === 0) {
    return '<div style="color:var(--muted); font-size:12px;">Detaylı değerlendirme mevcut değil.</div>';
  }
  return gereksinimler
    .map((g) => {
      const icon = DURUM_ICON[g.durum] || '•';
      const label = DURUM_LABEL[g.durum] || g.durum || '';
      const tur = g.tur === 'tercih' ? 'Tercih' : 'Zorunlu';
      const kanit = g.kanit && g.kanit !== 'kanit yok' ? g.kanit : "CV'de kanıt bulunamadı";
      return `
      <div class="req-row">
        <div class="req-icon">${icon}</div>
        <div class="req-body">
          <span class="req-name">${g.gereksinim || ''}</span><span class="req-tur">${tur} · ${label}</span>
          <div class="req-kanit">${kanit}</div>
        </div>
      </div>
    `;
    })
    .join('');
}

export function toggleReqList(id) {
  const list = document.getElementById('req-' + id);
  const btn = document.getElementById('toggle-' + id);
  if (!list) return;
  const isOpen = list.classList.toggle('open');
  if (btn) {
    btn.classList.toggle('open', isOpen);
    btn.querySelector('.label').innerText = isOpen ? 'Detaylı değerlendirmeyi gizle' : 'Detaylı değerlendirmeyi gör';
  }
}
window.toggleReqList = toggleReqList;

export function toggleOtherDetail(id) {
  const detail = document.getElementById('other-detail-' + id);
  if (!detail) return;
  detail.classList.toggle('open');
}
window.toggleOtherDetail = toggleOtherDetail;

export function renderContactChips(c) {
  const chips = [];
  if (c.location) chips.push(`<span class="contact-chip">📍 ${c.location}</span>`);
  if (c.phone) chips.push(`<span class="contact-chip">📞 ${c.phone}</span>`);
  if (c.linkedin) {
    const href = c.linkedin.startsWith('http') ? c.linkedin : 'https://' + c.linkedin;
    chips.push(`<span class="contact-chip">🔗 <a href="${href}" target="_blank" rel="noopener">LinkedIn</a></span>`);
  }
  if (c.github) {
    const href = c.github.startsWith('http') ? c.github : 'https://' + c.github;
    chips.push(`<span class="contact-chip">💻 <a href="${href}" target="_blank" rel="noopener">GitHub</a></span>`);
  }
  if (chips.length === 0) return '';
  return `<div class="contact-row">${chips.join('')}</div>`;
}
