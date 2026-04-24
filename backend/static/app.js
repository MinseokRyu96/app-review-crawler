'use strict';

let currentJobId = null;
let pollTimer    = null;
let allReviews   = [];

/* ── URL 감지 ── */
document.getElementById('url').addEventListener('input', function () {
  const tag = document.getElementById('store-tag');
  const v   = this.value;
  if (v.includes('apps.apple.com') || v.includes('itunes.apple.com')) {
    tag.textContent  = 'App Store';
    tag.className    = 'store-tag appstore';
  } else if (v.includes('play.google.com')) {
    tag.textContent  = 'Play Store';
    tag.className    = 'store-tag playstore';
  } else {
    tag.textContent  = '';
    tag.className    = 'store-tag';
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

  if (!url) return alert('URL을 입력해주세요.');
  if (!count || count < 1 || count > 500) return alert('크롤링 개수는 1~500 사이로 입력해주세요.');

  btn.disabled    = true;
  btn.textContent = '요청 중...';

  try {
    const res = await fetch('/api/crawl', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ url, count }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || '요청 실패');

    currentJobId = data.id;
    allReviews   = [];
    document.getElementById('reviews-sec').classList.add('hidden');
    document.getElementById('rating-filter').value = '0';

    showStatus(data);
    startPoll(data.id);
  } catch (e) {
    alert(e.message);
    btn.disabled    = false;
    btn.textContent = '크롤링 시작';
  }
}

/* ── 상태 카드 ── */
function showStatus(job) {
  document.getElementById('status-sec').classList.remove('hidden');
  updateStatus(job);
}

function updateStatus(job) {
  const badge = document.getElementById('status-badge');
  const fill  = document.getElementById('progress-fill');
  const msg   = document.getElementById('status-msg');
  const dlRow = document.getElementById('dl-row');
  const btn   = document.getElementById('start-btn');

  const labelMap = { pending: '대기 중', running: '크롤링 중', done: '완료', failed: '실패' };
  badge.textContent = labelMap[job.status] ?? job.status;
  badge.className   = `badge ${job.status}`;

  dlRow.classList.add('hidden');
  fill.className = 'progress-fill';

  if (job.status === 'pending') {
    fill.style.width = '15%';
    msg.textContent  = '크롤링 대기 중...';
  } else if (job.status === 'running') {
    fill.style.width = '60%';
    fill.classList.add('pulse');
    msg.textContent  = '리뷰를 수집하고 있습니다...';
  } else if (job.status === 'done') {
    fill.style.width = '100%';
    msg.textContent  = `${job.total_reviews.toLocaleString()}개 리뷰 수집 완료`;
    dlRow.classList.remove('hidden');
    btn.disabled    = false;
    btn.textContent = '크롤링 시작';
    updateInsights(job);
  } else if (job.status === 'failed') {
    fill.style.width = '100%';
    fill.classList.add('fail');
    msg.textContent  = `오류: ${job.error_message || '알 수 없는 오류'}`;
    btn.disabled    = false;
    btn.textContent = '크롤링 시작';
  }
}

/* ── 폴링 ── */
function startPoll(jobId) {
  if (pollTimer) clearInterval(pollTimer);

  pollTimer = setInterval(async () => {
    try {
      const res = await fetch(`/api/jobs/${jobId}`);
      const job = await res.json();
      updateStatus(job);

      if (job.status === 'done') {
        clearInterval(pollTimer);
        loadReviews(jobId);
        loadJobs();
        updateInsights(job);
      } else if (job.status === 'failed') {
        clearInterval(pollTimer);
        loadJobs();
      }
    } catch { /* ignore */ }
  }, 2000);
}

/* ── 리뷰 로드 & 렌더 ── */
async function loadReviews(jobId) {
  const res = await fetch(`/api/jobs/${jobId}/reviews`);
  allReviews = await res.json();
  renderReviews(allReviews);
}

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
    const stars  = '★'.repeat(r.rating) + '☆'.repeat(5 - r.rating);
    const title  = r.title  ? `<div class="r-title">${esc(r.title)}</div>` : '';
    const ver    = r.version? `<div class="r-version">버전 ${esc(r.version)}</div>` : '';
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

function filterReviews() {
  const rating   = parseInt(document.getElementById('rating-filter').value, 10);
  const filtered = rating === 0 ? allReviews : allReviews.filter(r => r.rating === rating);
  renderReviews(filtered);
}

/* ── 다운로드 ── */
function downloadFile() {
  if (currentJobId) window.location.href = `/api/jobs/${currentJobId}/download`;
}

/* ── 인사이트 ── */
let insightsPollTimer = null;

async function requestInsights() {
  if (!currentJobId) return;
  const btn = document.getElementById('insights-btn');
  btn.disabled = true;

  try {
    const res = await fetch(`/api/jobs/${currentJobId}/insights`, { method: 'POST' });
    if (!res.ok) {
      const err = await res.json();
      alert(err.detail || '인사이트 요청 실패');
      btn.disabled = false;
      return;
    }
    showInsightsLoading();
    startInsightsPoll(currentJobId);
  } catch {
    btn.disabled = false;
  }
}

function showInsightsLoading() {
  const sec = document.getElementById('insights-sec');
  sec.classList.remove('hidden');
  document.getElementById('insights-loading').classList.remove('hidden');
  document.getElementById('insights-body').innerHTML = '';
  document.getElementById('insights-badge').textContent = '분석 중';
  document.getElementById('insights-badge').className = 'badge running';
  sec.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function updateInsights(job) {
  const sec    = document.getElementById('insights-sec');
  const body   = document.getElementById('insights-body');
  const badge  = document.getElementById('insights-badge');
  const loading= document.getElementById('insights-loading');
  const btn    = document.getElementById('insights-btn');

  if (job.insights_status === 'none') return;

  sec.classList.remove('hidden');

  if (job.insights_status === 'running' || job.insights_status === 'pending') {
    loading.classList.remove('hidden');
    badge.textContent = '분석 중';
    badge.className   = 'badge running';
  } else if (job.insights_status === 'done') {
    loading.classList.add('hidden');
    badge.textContent = '분석 완료';
    badge.className   = 'badge done';
    btn.disabled      = false;
    btn.textContent   = '✨ 재분석';
    body.innerHTML    = marked.parse(job.insights || '');
  } else if (job.insights_status === 'failed') {
    loading.classList.add('hidden');
    badge.textContent = '분석 실패';
    badge.className   = 'badge failed';
    btn.disabled      = false;
    body.innerHTML    = '<p class="no-data">인사이트 분석에 실패했습니다. ANTHROPIC_API_KEY를 확인해주세요.</p>';
  }
}

function startInsightsPoll(jobId) {
  if (insightsPollTimer) clearInterval(insightsPollTimer);

  insightsPollTimer = setInterval(async () => {
    try {
      const res = await fetch(`/api/jobs/${jobId}`);
      const job = await res.json();
      updateInsights(job);

      if (job.insights_status === 'done' || job.insights_status === 'failed') {
        clearInterval(insightsPollTimer);
      }
    } catch { /* ignore */ }
  }, 2500);
}

/* ── 최근 기록 ── */
async function loadJobs() {
  const res  = await fetch('/api/jobs');
  const jobs = await res.json();
  const list = document.getElementById('jobs-list');
  const statusLabel = { pending: '대기', running: '진행중', done: '완료', failed: '실패' };

  if (!jobs.length) {
    list.innerHTML = '<p class="no-data">아직 크롤링 기록이 없습니다.</p>';
    return;
  }

  list.innerHTML = jobs.map(job => {
    const storeLabel = job.store === 'appstore' ? '앱스토어' : '플레이스토어';
    const date       = new Date(job.created_at + 'Z').toLocaleString('ko-KR');
    return `
      <div class="job-card" onclick="loadJobDetail('${job.id}')">
        <div>
          <div class="job-url">${esc(job.url)}</div>
          <div class="job-meta">
            <span>${storeLabel}</span>
            <span>수집 ${job.total_reviews.toLocaleString()}개</span>
            <span>${date}</span>
          </div>
        </div>
        <div class="job-right">
          <span class="badge ${job.status}">${statusLabel[job.status] ?? job.status}</span>
        </div>
      </div>`;
  }).join('');
}

async function loadJobDetail(jobId) {
  currentJobId = jobId;
  document.getElementById('rating-filter').value = '0';

  const res = await fetch(`/api/jobs/${jobId}`);
  const job = await res.json();
  showStatus(job);
  window.scrollTo({ top: 0, behavior: 'smooth' });

  if (job.status === 'done') {
    loadReviews(jobId);
    updateInsights(job);
    if (job.insights_status === 'running' || job.insights_status === 'pending') {
      startInsightsPoll(jobId);
    }
  } else if (job.status === 'running' || job.status === 'pending') {
    startPoll(jobId);
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

/* 초기 로드 */
loadJobs();
