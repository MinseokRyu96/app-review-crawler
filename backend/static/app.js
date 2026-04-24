'use strict';

/* ── 상태 ── */
let currentReviews  = [];
let currentStore    = '';
let currentUrl      = '';
let currentArticles = [];
let currentKeyword  = '';
let activeTab       = 'review';

/* ── 탭 전환 ── */
function switchTab(tab) {
  activeTab = tab;
  document.getElementById('tab-review').classList.toggle('active', tab === 'review');
  document.getElementById('tab-news').classList.toggle('active',   tab === 'news');
  document.getElementById('review-input').classList.toggle('hidden', tab !== 'review');
  document.getElementById('news-input').classList.toggle('hidden',   tab !== 'news');
  document.getElementById('reviews-sec').classList.add('hidden');
  document.getElementById('news-sec').classList.add('hidden');
  document.getElementById('insights-sec').classList.add('hidden');
  document.getElementById('loading-sec').classList.add('hidden');
}

/* ── URL 감지 ── */
document.getElementById('url').addEventListener('input', function () {
  const tag = document.getElementById('store-tag');
  const v   = this.value;
  if (v.includes('apps.apple.com') || v.includes('itunes.apple.com')) {
    tag.textContent = 'App Store';  tag.className = 'store-tag appstore';
  } else if (v.includes('play.google.com')) {
    tag.textContent = 'Play Store'; tag.className = 'store-tag playstore';
  } else {
    tag.textContent = ''; tag.className = 'store-tag';
  }
});

/* ── 앱 리뷰 개수 버튼 ── */
document.querySelectorAll('.cnt-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.cnt-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('review-count').value = btn.dataset.v;
  });
});
document.getElementById('review-count').addEventListener('input', () => {
  document.querySelectorAll('.cnt-btn').forEach(b => b.classList.remove('active'));
});

/* ── 뉴스 개수 버튼 ── */
document.querySelectorAll('.news-cnt-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.news-cnt-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('news-count').value = btn.dataset.v;
  });
});
document.getElementById('news-count').addEventListener('input', () => {
  document.querySelectorAll('.news-cnt-btn').forEach(b => b.classList.remove('active'));
});

/* ════════════════════════════════════════════════════════
   앱 리뷰
════════════════════════════════════════════════════════ */
async function startCrawl() {
  const url   = document.getElementById('url').value.trim();
  const count = parseInt(document.getElementById('review-count').value, 10);
  const btn   = document.getElementById('review-start-btn');

  if (!url)   return alert('URL을 입력해주세요.');
  if (!count || count < 1 || count > 500) return alert('크롤링 개수는 1~500 사이로 입력해주세요.');

  btn.disabled = true; btn.textContent = '수집 중...';
  showLoading('리뷰를 수집하고 있습니다...');
  document.getElementById('reviews-sec').classList.add('hidden');
  document.getElementById('insights-sec').classList.add('hidden');
  document.getElementById('rating-filter').value = '0';

  try {
    const res  = await fetch('/api/crawl', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, count }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || '요청 실패');
    currentReviews = data.reviews; currentStore = data.store; currentUrl = url;
    hideLoading();
    renderReviews(currentReviews);
  } catch (e) {
    hideLoading(); alert('오류: ' + e.message);
  } finally {
    btn.disabled = false; btn.textContent = '크롤링 시작';
  }
}

function renderRatingChart(reviews) {
  const total = reviews.length;
  if (!total) { document.getElementById('rating-chart').innerHTML = ''; return; }

  const counts = [5, 4, 3, 2, 1].map(star => ({
    star,
    count: reviews.filter(r => r.rating === star).length,
  }));
  const max = Math.max(...counts.map(c => c.count), 1);

  const colors = { 5: '#22c55e', 4: '#86efac', 3: '#fbbf24', 2: '#fb923c', 1: '#ef4444' };

  document.getElementById('rating-chart').innerHTML = `
    <div class="chart-wrap">
      <div class="chart-title">별점 분포</div>
      ${counts.map(({ star, count }) => {
        const pct  = Math.round((count / total) * 100);
        const barW = Math.round((count / max) * 100);
        return `
          <div class="chart-row">
            <div class="chart-label">
              <span class="chart-star" style="color:${colors[star]}">★</span>
              <span>${star}</span>
            </div>
            <div class="chart-bar-wrap">
              <div class="chart-bar" style="width:${barW}%; background:${colors[star]}"></div>
            </div>
            <div class="chart-count">${count.toLocaleString()}<span class="chart-pct">${pct}%</span></div>
          </div>`;
      }).join('')}
    </div>`;
}

function renderReviews(reviews) {
  const sec   = document.getElementById('reviews-sec');
  const list  = document.getElementById('reviews-list');
  const badge = document.getElementById('rev-count');
  sec.classList.remove('hidden');
  badge.textContent = reviews.length.toLocaleString();
  renderRatingChart(currentReviews);

  if (!reviews.length) { list.innerHTML = '<p class="no-data">수집된 리뷰가 없습니다.</p>'; return; }

  list.innerHTML = reviews.map(r => {
    const stars = '★'.repeat(r.rating) + '☆'.repeat(5 - r.rating);
    const title = r.title   ? `<div class="r-title">${esc(r.title)}</div>`         : '';
    const ver   = r.version ? `<div class="r-version">버전 ${esc(r.version)}</div>` : '';
    return `<div class="review-item" data-rating="${r.rating}">
      <div class="r-meta">
        <span class="r-author">${esc(r.author || 'Unknown')}</span>
        <span class="r-stars">${stars}</span>
        <span class="r-date">${esc(r.review_date)}</span>
      </div>
      ${title}<div class="r-body">${esc(r.content)}</div>${ver}
    </div>`;
  }).join('');
}

function filterReviews() {
  const rating   = parseInt(document.getElementById('rating-filter').value, 10);
  const filtered = rating === 0 ? currentReviews : currentReviews.filter(r => r.rating === rating);
  renderReviews(filtered);
}

function downloadReviews() {
  if (!currentReviews.length) return;
  const storeName = currentStore === 'appstore' ? '앱스토어' : '플레이스토어';
  const lines = [
    '='.repeat(60), '  앱 리뷰 크롤링 결과', '='.repeat(60),
    `스토어  : ${storeName}`, `URL     : ${currentUrl}`,
    `수집 수 : ${currentReviews.length}개`,
    `수집 일 : ${new Date().toLocaleString('ko-KR')}`,
    '='.repeat(60), '',
  ];
  currentReviews.forEach((r, i) => {
    const stars = '★'.repeat(r.rating) + '☆'.repeat(5 - r.rating);
    lines.push(`[${String(i+1).padStart(3,' ')}] ${r.author || 'Unknown'}`);
    lines.push(`      ${stars}  ${r.review_date}`);
    if (r.title)   lines.push(`      제목 : ${r.title}`);
    if (r.version) lines.push(`      버전 : ${r.version}`);
    lines.push(`      ${r.content}`, `      ${'-'.repeat(50)}`, '');
  });
  download(lines.join('\n'), `reviews_${currentStore}_${Date.now()}.txt`);
}

async function requestInsights() {
  if (!currentReviews.length) return;
  const btn = document.getElementById('insights-btn');
  btn.disabled = true; btn.textContent = '분석 중...';
  showInsightsLoading();
  try {
    const res  = await fetch('/api/insights', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reviews: currentReviews, store: currentStore }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || '인사이트 분석 실패');
    showInsightsDone(data.insights);
  } catch (e) {
    showInsightsFail(e.message);
  } finally {
    btn.disabled = false; btn.textContent = '✨ AI 인사이트 분석';
  }
}

/* ════════════════════════════════════════════════════════
   뉴스 기사
════════════════════════════════════════════════════════ */
async function startNewsCrawl() {
  const keyword = document.getElementById('keyword').value.trim();
  const count   = parseInt(document.getElementById('news-count').value, 10);
  const btn     = document.getElementById('news-start-btn');

  if (!keyword) return alert('키워드를 입력해주세요.');
  if (!count || count < 1 || count > 100) return alert('수집 개수는 1~100 사이로 입력해주세요.');

  btn.disabled = true; btn.textContent = '수집 중...';
  showLoading('뉴스 기사를 수집하고 있습니다...');
  document.getElementById('news-sec').classList.add('hidden');
  document.getElementById('insights-sec').classList.add('hidden');

  try {
    const res  = await fetch('/api/news/crawl', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ keyword, count }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || '요청 실패');
    currentArticles = data.articles; currentKeyword = keyword;
    hideLoading();
    renderNews(currentArticles);
  } catch (e) {
    hideLoading(); alert('오류: ' + e.message);
  } finally {
    btn.disabled = false; btn.textContent = '뉴스 수집 시작';
  }
}

function renderNews(articles) {
  const sec   = document.getElementById('news-sec');
  const list  = document.getElementById('news-list');
  const badge = document.getElementById('news-count-badge');
  sec.classList.remove('hidden');
  badge.textContent = articles.length.toLocaleString();

  if (!articles.length) { list.innerHTML = '<p class="no-data">수집된 기사가 없습니다.</p>'; return; }

  list.innerHTML = articles.map((a, i) => `
    <div class="news-item">
      <div class="news-num">${i + 1}</div>
      <div class="news-body">
        <a class="news-title" href="${esc(a.link)}" target="_blank" rel="noopener">${esc(a.title)}</a>
        <div class="news-meta">
          <span class="news-source">${esc(a.source)}</span>
          <span class="news-date">${esc(a.pub_date)}</span>
        </div>
        ${a.description ? `<div class="news-desc">${esc(a.description)}</div>` : ''}
      </div>
    </div>`
  ).join('');
}

function downloadNews() {
  if (!currentArticles.length) return;
  const lines = [
    '='.repeat(60), `  뉴스 기사 수집 결과`, '='.repeat(60),
    `키워드  : ${currentKeyword}`,
    `수집 수 : ${currentArticles.length}개`,
    `수집 일 : ${new Date().toLocaleString('ko-KR')}`,
    '='.repeat(60), '',
  ];
  currentArticles.forEach((a, i) => {
    lines.push(`[${String(i+1).padStart(3,' ')}] ${a.title}`);
    lines.push(`      출처 : ${a.source}  |  ${a.pub_date}`);
    lines.push(`      URL  : ${a.link}`);
    if (a.description) lines.push(`      내용 : ${a.description}`);
    lines.push(`      ${'-'.repeat(50)}`, '');
  });
  download(lines.join('\n'), `news_${currentKeyword}_${Date.now()}.txt`);
}

async function requestNewsInsights() {
  if (!currentArticles.length) return;
  const btn = document.getElementById('news-insights-btn');
  btn.disabled = true; btn.textContent = '분석 중...';
  showInsightsLoading();
  try {
    const res  = await fetch('/api/news/insights', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ articles: currentArticles, keyword: currentKeyword }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || '인사이트 분석 실패');
    showInsightsDone(data.insights);
  } catch (e) {
    showInsightsFail(e.message);
  } finally {
    btn.disabled = false; btn.textContent = '✨ AI 인사이트 분석';
  }
}

/* ════════════════════════════════════════════════════════
   공통 UI 헬퍼
════════════════════════════════════════════════════════ */
function showLoading(msg) {
  document.getElementById('loading-msg').textContent = msg;
  document.getElementById('loading-sec').classList.remove('hidden');
}
function hideLoading() {
  document.getElementById('loading-sec').classList.add('hidden');
}

function showInsightsLoading() {
  const sec = document.getElementById('insights-sec');
  sec.classList.remove('hidden');
  document.getElementById('insights-loading').classList.remove('hidden');
  document.getElementById('insights-body').innerHTML = '';
  document.getElementById('insights-badge').textContent = '분석 중';
  document.getElementById('insights-badge').className  = 'badge running';
  sec.scrollIntoView({ behavior: 'smooth', block: 'start' });
}
function showInsightsDone(text) {
  document.getElementById('insights-loading').classList.add('hidden');
  document.getElementById('insights-badge').textContent = '분석 완료';
  document.getElementById('insights-badge').className  = 'badge done';
  document.getElementById('insights-body').innerHTML   = marked.parse(text);
}
function showInsightsFail(msg) {
  document.getElementById('insights-loading').classList.add('hidden');
  document.getElementById('insights-badge').textContent = '분석 실패';
  document.getElementById('insights-badge').className  = 'badge failed';
  document.getElementById('insights-body').innerHTML   = `<p class="no-data">${esc(msg)}</p>`;
}

function download(content, filename) {
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = filename; a.click();
}

function esc(str) {
  if (!str) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
