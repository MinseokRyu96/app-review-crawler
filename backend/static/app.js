'use strict';

let currentReviews = [];
let currentStore   = '';
let currentUrl     = '';

/* ── URL 감지 ── */
document.getElementById('url').addEventListener('input', function () {
  const tag = document.getElementById('store-tag');
  const v   = this.value;
  if (v.includes('apps.apple.com') || v.includes('itunes.apple.com')) {
    tag.textContent = 'App Store';
    tag.className   = 'store-tag appstore';
  } else if (v.includes('play.google.com')) {
    tag.textContent = 'Play Store';
    tag.className   = 'store-tag playstore';
  } else {
    tag.textContent = '';
    tag.className   = 'store-tag';
  }
});

/* ── 개수 버튼 ── */
document.querySelectorAll('.cnt-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.cnt-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('count').value = btn.dataset.v;
  });
});
document.getElementById('count').addEventListener('input', () => {
  document.querySelectorAll('.cnt-btn').forEach(b => b.classList.remove('active'));
});

/* ── 크롤링 시작 ── */
async function startCrawl() {
  const url   = document.getElementById('url').value.trim();
  const count = parseInt(document.getElementById('count').value, 10);
  const btn   = document.getElementById('start-btn');

  if (!url)   return alert('URL을 입력해주세요.');
  if (!count || count < 1 || count > 500) return alert('크롤링 개수는 1~500 사이로 입력해주세요.');

  btn.disabled    = true;
  btn.textContent = '수집 중...';

  document.getElementById('reviews-sec').classList.add('hidden');
  document.getElementById('insights-sec').classList.add('hidden');
  document.getElementById('loading-sec').classList.remove('hidden');
  document.getElementById('rating-filter').value = '0';

  try {
    const res  = await fetch('/api/crawl', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ url, count }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || '요청 실패');

    currentReviews = data.reviews;
    currentStore   = data.store;
    currentUrl     = url;

    document.getElementById('loading-sec').classList.add('hidden');
    renderReviews(currentReviews);
  } catch (e) {
    document.getElementById('loading-sec').classList.add('hidden');
    alert('오류: ' + e.message);
  } finally {
    btn.disabled    = false;
    btn.textContent = '크롤링 시작';
  }
}

/* ── 리뷰 렌더 ── */
function renderReviews(reviews) {
  const sec   = document.getElementById('reviews-sec');
  const list  = document.getElementById('reviews-list');
  const badge = document.getElementById('rev-count');

  sec.classList.remove('hidden');
  badge.textContent = reviews.length.toLocaleString();

  if (!reviews.length) {
    list.innerHTML = '<p class="no-data">수집된 리뷰가 없습니다.</p>';
    return;
  }

  list.innerHTML = reviews.map(r => {
    const stars = '★'.repeat(r.rating) + '☆'.repeat(5 - r.rating);
    const title = r.title   ? `<div class="r-title">${esc(r.title)}</div>`         : '';
    const ver   = r.version ? `<div class="r-version">버전 ${esc(r.version)}</div>` : '';
    return `
      <div class="review-item" data-rating="${r.rating}">
        <div class="r-meta">
          <span class="r-author">${esc(r.author || 'Unknown')}</span>
          <span class="r-stars">${stars}</span>
          <span class="r-date">${esc(r.review_date)}</span>
        </div>
        ${title}
        <div class="r-body">${esc(r.content)}</div>
        ${ver}
      </div>`;
  }).join('');
}

/* ── 별점 필터 ── */
function filterReviews() {
  const rating   = parseInt(document.getElementById('rating-filter').value, 10);
  const filtered = rating === 0 ? currentReviews : currentReviews.filter(r => r.rating === rating);
  renderReviews(filtered);
}

/* ── 다운로드 (클라이언트 사이드) ── */
function downloadFile() {
  if (!currentReviews.length) return;

  const storeName = currentStore === 'appstore' ? '앱스토어' : '플레이스토어';
  const now = new Date().toLocaleString('ko-KR');
  const sep = '='.repeat(60);

  const lines = [
    sep,
    '  앱 리뷰 크롤링 결과',
    sep,
    `스토어  : ${storeName}`,
    `URL     : ${currentUrl}`,
    `수집 수 : ${currentReviews.length}개`,
    `수집 일 : ${now}`,
    sep,
    '',
  ];

  currentReviews.forEach((r, i) => {
    const stars = '★'.repeat(r.rating) + '☆'.repeat(5 - r.rating);
    lines.push(`[${String(i + 1).padStart(3, ' ')}] ${r.author || 'Unknown'}`);
    lines.push(`      ${stars}  ${r.review_date}`);
    if (r.title)   lines.push(`      제목 : ${r.title}`);
    if (r.version) lines.push(`      버전 : ${r.version}`);
    lines.push(`      ${r.content}`);
    lines.push(`      ${'-'.repeat(50)}`);
    lines.push('');
  });

  const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' });
  const a    = document.createElement('a');
  a.href     = URL.createObjectURL(blob);
  a.download = `reviews_${currentStore}_${Date.now()}.txt`;
  a.click();
}

/* ── 인사이트 ── */
async function requestInsights() {
  if (!currentReviews.length) return;

  const btn = document.getElementById('insights-btn');
  btn.disabled    = true;
  btn.textContent = '분석 중...';

  const sec = document.getElementById('insights-sec');
  sec.classList.remove('hidden');
  document.getElementById('insights-loading').classList.remove('hidden');
  document.getElementById('insights-body').innerHTML = '';
  document.getElementById('insights-badge').textContent = '분석 중';
  document.getElementById('insights-badge').className  = 'badge running';
  sec.scrollIntoView({ behavior: 'smooth', block: 'start' });

  try {
    const res  = await fetch('/api/insights', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ reviews: currentReviews, store: currentStore }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || '인사이트 분석 실패');

    document.getElementById('insights-loading').classList.add('hidden');
    document.getElementById('insights-badge').textContent = '분석 완료';
    document.getElementById('insights-badge').className  = 'badge done';
    document.getElementById('insights-body').innerHTML   = marked.parse(data.insights);
  } catch (e) {
    document.getElementById('insights-loading').classList.add('hidden');
    document.getElementById('insights-badge').textContent = '분석 실패';
    document.getElementById('insights-badge').className  = 'badge failed';
    document.getElementById('insights-body').innerHTML   = `<p class="no-data">${esc(e.message)}</p>`;
  } finally {
    btn.disabled    = false;
    btn.textContent = '✨ AI 인사이트 분석';
  }
}

/* ── 유틸 ── */
function esc(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
