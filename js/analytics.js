/**
 * Luxury GitHub Repository Showcase & Analytics Dashboard Script
 * Ultra-Modern Developer Luxury (Linear, Vercel & Raycast aesthetic)
 */

// Repository Profiles
const REPO_PROFILES = {
  'acme-labs/omni-flow': {
    org: 'acme-labs',
    name: 'omni-flow',
    fullName: 'acme-labs/omni-flow',
    tagline: 'High-performance distributed stream processing engine built in Rust with zero-copy architecture and real-time WebAssembly plugins.',
    license: 'Apache-2.0',
    version: 'v2.4.1',
    isPublic: true,
    stars: 34892,
    starsWeekDelta: '+842 this week',
    starsGrowthPct: '+18.4% MoM',
    forks: 4128,
    cloneHttps: 'https://github.com/acme-labs/omni-flow.git',
    cloneSsh: 'git@github.com:acme-labs/omni-flow.git',
    cloneCli: 'gh repo clone acme-labs/omni-flow',
    demoUrl: 'https://omni-flow.dev',
    medianMergeTime: '4.2h',
    ciPassingRate: '99.1%',
    ciRunsTotal: '428 runs',
    contributorsCount: 214,
    countriesCount: 32,
    newContributors: '+12 this month',
    releaseCadence: 'Bi-weekly',
    lastReleaseDays: '3 days ago',
    cycleDuration: '13.8 days',
    languages: [
      { name: 'Rust', pct: 68.2, color: '#dea584', lines: '218,490 loc' },
      { name: 'TypeScript', pct: 24.1, color: '#3178c6', lines: '77,210 loc' },
      { name: 'Python', pct: 5.4, color: '#3572A5', lines: '17,280 loc' },
      { name: 'WebAssembly', pct: 2.3, color: '#654ff0', lines: '7,360 loc' }
    ],
    milestones: [
      { label: 'Show HN Launch', value: '+4,200 ★', xPct: 22 },
      { label: 'v2.0 Architecture Rewrite', value: '+8,100 ★', xPct: 56 },
      { label: 'GitHub Trending #1', value: '+12,400 ★', xPct: 84 }
    ],
    prs: [
      {
        id: '#418',
        title: 'feat(stream): implement zero-copy ringbuffer for microsecond batching',
        type: 'feat',
        author: 'kheat-dev',
        avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&auto=format&fit=crop&q=80',
        branch: 'main ← feat/zero-copy-ring',
        checks: '18/18 checks passed',
        time: '2 hours ago',
        additions: 342,
        deletions: 89,
        files: 4,
        diff: `diff --git a/crates/engine/src/ring.rs b/crates/engine/src/ring.rs
index 4b82ca..8f21e0 100644
--- a/crates/engine/src/ring.rs
+++ b/crates/engine/src/ring.rs
@@ -14,6 +14,14 @@ pub struct RingBuffer<T> {
+    // Allocate memory-mapped circular buffer with page alignment
+    aligned_ptr: *mut T,
+    capacity_mask: usize,
+    head: AtomicUsize,
+    tail: AtomicUsize,
 }
 
+impl<T: Send + Sync> RingBuffer<T> {
+    #[inline(always)]
+    pub fn push_batch_zero_copy(&self, batch: &[T]) -> Result<(), EngineError> {`
      },
      {
        id: '#416',
        title: 'perf(parser): optimize SIMD vectorized json payload unpacking',
        type: 'perf',
        author: 'sophia-core',
        avatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&auto=format&fit=crop&q=80',
        branch: 'main ← perf/simd-unpack',
        checks: '18/18 checks passed',
        time: '6 hours ago',
        additions: 184,
        deletions: 42,
        files: 2,
        diff: `diff --git a/crates/parser/src/simd.rs b/crates/parser/src/simd.rs
@@ -48,8 +48,14 @@ pub fn parse_simd_avx2(src: &[u8]) -> Value {
+    unsafe {
+        let chunk = _mm256_loadu_si256(src.as_ptr() as *const __m256i);
+        let mask = _mm256_cmpeq_epi8(chunk, quote_pattern);
+        _mm256_movemask_epi8(mask)
+    }`
      },
      {
        id: '#414',
        title: 'fix(cluster): handle graceful partition heartbeat re-election',
        type: 'fix',
        author: 'alex-maintainer',
        avatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&auto=format&fit=crop&q=80',
        branch: 'main ← fix/partition-split',
        checks: '18/18 checks passed',
        time: 'Yesterday',
        additions: 92,
        deletions: 115,
        files: 3,
        diff: `diff --git a/crates/cluster/src/heartbeat.rs b/crates/cluster/src/heartbeat.rs
@@ -102,9 +102,6 @@ async fn check_quorum(&mut self) {
-    if !self.has_majority() {
-        self.panic_drop_leader();
-    }
+    self.enter_provisional_reconciliation().await;`
      },
      {
        id: '#409',
        title: 'docs(architecture): add interactive WebAssembly streaming telemetry guide',
        type: 'docs',
        author: 'marcus-wasm',
        avatar: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=100&auto=format&fit=crop&q=80',
        branch: 'main ← docs/wasm-guide',
        checks: '18/18 checks passed',
        time: '3 days ago',
        additions: 512,
        deletions: 14,
        files: 5,
        diff: `diff --git a/docs/wasm_streaming.md b/docs/wasm_streaming.md
@@ -1,5 +1,18 @@
+# WebAssembly Streaming Pipelines
+Plugins compiled to Wasm execute with native sandboxed memory isolation.`
      }
    ]
  },
  'ChingKheat/geo_heritage_personal': {
    org: 'ChingKheat',
    name: 'geo_heritage_personal',
    fullName: 'ChingKheat/geo_heritage_personal',
    tagline: 'Cultural exploration and preservation mobile platform with interactive GPS navigation, Geobot AI cultural guide, and gamified digital passport achievements.',
    license: 'MIT',
    version: 'v1.0.0',
    isPublic: false,
    stars: 284,
    starsWeekDelta: '+38 this week',
    starsGrowthPct: '+24.5% MoM',
    forks: 34,
    cloneHttps: 'https://github.com/ChingKheat/geo_heritage_personal.git',
    cloneSsh: 'git@github.com:ChingKheat/geo_heritage_personal.git',
    cloneCli: 'gh repo clone ChingKheat/geo_heritage_personal',
    demoUrl: 'demo.html?project=geo_heritage_personal',
    medianMergeTime: '2.8h',
    ciPassingRate: '100%',
    ciRunsTotal: '86 runs',
    contributorsCount: 4,
    countriesCount: 1,
    newContributors: '+1 this month',
    releaseCadence: 'Weekly',
    lastReleaseDays: '2 days ago',
    cycleDuration: '7.0 days',
    languages: [
      { name: 'Dart', pct: 91.5, color: '#00B4AB', lines: '24,800 loc' },
      { name: 'Kotlin', pct: 4.8, color: '#A97BFF', lines: '1,320 loc' },
      { name: 'Swift', pct: 2.5, color: '#F05138', lines: '680 loc' },
      { name: 'HTML/Web', pct: 1.2, color: '#e34c26', lines: '310 loc' }
    ],
    milestones: [
      { label: 'Initial Group Milestone', value: '+50 ★', xPct: 20 },
      { label: 'Geobot AI & Map Integration', value: '+120 ★', xPct: 55 },
      { label: 'Personal Edition v1.0 Launch', value: '+114 ★', xPct: 88 }
    ],
    prs: [
      {
        id: '#24',
        title: 'feat: add digital cultural passport XP progression & confetti achievements',
        type: 'feat',
        author: 'ChingKheat',
        avatar: 'https://github.com/ChingKheat.png',
        branch: 'main ← feat/passport-gamification',
        checks: '6/6 checks passed',
        time: '3 hours ago',
        additions: 412,
        deletions: 48,
        files: 3,
        diff: `diff --git a/lib/features/user/presentation/passport_screen.dart b/lib/features/user/presentation/passport_screen.dart
@@ -88,6 +88,12 @@ void claimStamp(String siteId) {
+  _confettiController.play();
+  _appState.addXp(50);
+  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('🎉 +50 XP Earned!')));`
      },
      {
        id: '#22',
        title: 'feat: compile CanvasKit Flutter web bundle for live browser preview',
        type: 'feat',
        author: 'ChingKheat',
        avatar: 'https://github.com/ChingKheat.png',
        branch: 'main ← feat/flutter-web',
        checks: '6/6 checks passed',
        time: 'Yesterday',
        additions: 128,
        deletions: 12,
        files: 2,
        diff: `diff --git a/web/index.html b/web/index.html
@@ -15,4 +15,6 @@
+  <base href="/portfolio/demos/geo_heritage/">
+  <script src="flutter_bootstrap.js" async></script>`
      }
    ]
  },
  'ChingKheat/banana-dashboard': {
    org: 'ChingKheat',
    name: 'banana-dashboard',
    fullName: 'ChingKheat/banana-dashboard',
    tagline: 'Machine learning and computer vision analytics master dashboard comparing 5 ripeness classification algorithms with live visual metrics.',
    license: 'MIT',
    version: 'v1.4.0',
    isPublic: true,
    stars: 842,
    starsWeekDelta: '+64 this week',
    starsGrowthPct: '+19.2% MoM',
    forks: 112,
    cloneHttps: 'https://github.com/ChingKheat/banana-dashboard.git',
    cloneSsh: 'git@github.com:ChingKheat/banana-dashboard.git',
    cloneCli: 'gh repo clone ChingKheat/banana-dashboard',
    demoUrl: 'https://chingkheat.github.io/banana-dashboard/',
    medianMergeTime: '3.5h',
    ciPassingRate: '98.5%',
    ciRunsTotal: '142 runs',
    contributorsCount: 3,
    countriesCount: 1,
    newContributors: '+1 this month',
    releaseCadence: 'Monthly',
    lastReleaseDays: '5 days ago',
    cycleDuration: '21.0 days',
    languages: [
      { name: 'JavaScript', pct: 64.5, color: '#f1e05a', lines: '12,400 loc' },
      { name: 'HTML', pct: 22.1, color: '#e34c26', lines: '4,200 loc' },
      { name: 'CSS', pct: 13.4, color: '#563d7c', lines: '2,580 loc' }
    ],
    milestones: [
      { label: '5-Model Classifier v1', value: '+200 ★', xPct: 25 },
      { label: 'Confusion Matrix Visualizer', value: '+350 ★', xPct: 60 },
      { label: 'Master Showcase Release', value: '+292 ★', xPct: 90 }
    ],
    prs: [
      {
        id: '#12',
        title: 'feat: add side-by-side computer vision accuracy curves',
        type: 'feat',
        author: 'ChingKheat',
        avatar: 'https://github.com/ChingKheat.png',
        branch: 'main ← feat/side-by-side-curves',
        checks: '8/8 checks passed',
        time: '2 days ago',
        additions: 198,
        deletions: 34,
        files: 2,
        diff: `diff --git a/js/dashboard.js b/js/dashboard.js
@@ -45,6 +45,10 @@ function renderModelAccuracyComparison() {
+  renderAccuracyLineChart(data.models);`
      }
    ]
  }
};

// Global App State
const LuxuryAnalytics = {
  activeRepoKey: 'acme-labs/omni-flow',
  activeProtocol: 'https',
  activeChartTimeframe: '1Y',
  isStarred: false,
  activeFilterType: 'all',

  init() {
    this.bindEvents();
    this.renderRepository(this.activeRepoKey);
    this.initMouseSpotlight();
    this.renderCommitHeatmap();
  },

  bindEvents() {
    // Repo Switcher dropdown
    const switcherBtn = document.getElementById('repo-switcher-btn');
    const switcherMenu = document.getElementById('repo-switcher-menu');
    switcherBtn?.addEventListener('click', (e) => {
      e.stopPropagation();
      switcherMenu.classList.toggle('active');
    });

    document.addEventListener('click', () => {
      switcherMenu?.classList.remove('active');
    });

    document.querySelectorAll('.repo-menu-item').forEach(item => {
      item.addEventListener('click', (e) => {
        const repoKey = e.currentTarget.getAttribute('data-repo');
        if (repoKey && REPO_PROFILES[repoKey]) {
          this.switchRepo(repoKey);
        }
      });
    });

    // Star Button
    const starBtn = document.getElementById('star-btn');
    starBtn?.addEventListener('click', () => this.toggleStar());

    // Protocol selector tabs
    document.querySelectorAll('.protocol-tab').forEach(tab => {
      tab.addEventListener('click', (e) => {
        const proto = e.currentTarget.getAttribute('data-proto');
        this.switchProtocol(proto);
      });
    });

    // Copy clone command
    document.getElementById('copy-clone-btn')?.addEventListener('click', () => {
      this.copyCloneCommand();
    });

    // Chart Timeframe buttons
    document.querySelectorAll('.timeframe-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        document.querySelectorAll('.timeframe-btn').forEach(b => b.classList.remove('active'));
        e.currentTarget.classList.add('active');
        this.activeChartTimeframe = e.currentTarget.getAttribute('data-tf');
        this.renderStarChart();
      });
    });

    // PR Filter Chips
    document.querySelectorAll('.filter-chip').forEach(chip => {
      chip.addEventListener('click', (e) => {
        document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
        e.currentTarget.classList.add('active');
        this.activeFilterType = e.currentTarget.getAttribute('data-filter');
        this.renderPrTable();
      });
    });

    // PR Search Input
    document.getElementById('pr-search-input')?.addEventListener('input', (e) => {
      this.searchPrs(e.target.value);
    });

    // Close diff modal
    document.getElementById('diff-close-btn')?.addEventListener('click', () => {
      this.closeDiffModal();
    });

    document.getElementById('diff-modal-backdrop')?.addEventListener('click', (e) => {
      if (e.target.id === 'diff-modal-backdrop') this.closeDiffModal();
    });
  },

  switchRepo(repoKey) {
    this.activeRepoKey = repoKey;
    document.querySelectorAll('.repo-menu-item').forEach(item => {
      item.classList.toggle('active', item.getAttribute('data-repo') === repoKey);
    });
    this.renderRepository(repoKey);
    this.showToast(`Switched repository context to ${repoKey}`);
  },

  renderRepository(repoKey) {
    const profile = REPO_PROFILES[repoKey];
    if (!profile) return;

    // Header Breadcrumbs & Details
    document.getElementById('repo-org-text').textContent = profile.org;
    document.getElementById('repo-name-text').textContent = profile.name;
    document.getElementById('repo-tagline-text').textContent = profile.tagline;
    document.getElementById('repo-license-badge').textContent = profile.license;
    document.getElementById('repo-version-badge').textContent = `${profile.version} Latest`;
    
    const visibilityBadge = document.getElementById('repo-visibility-badge');
    if (visibilityBadge) {
      visibilityBadge.textContent = profile.isPublic ? 'Public' : 'Private';
      visibilityBadge.className = `pill-badge ${profile.isPublic ? 'status-pass' : 'status-license'}`;
    }

    // Star Count
    const savedStarred = localStorage.getItem(`starred_${profile.fullName}`) === 'true';
    this.isStarred = savedStarred;
    const starBtn = document.getElementById('star-btn');
    starBtn?.classList.toggle('starred', this.isStarred);
    this.updateStarCountDisplay(profile.stars + (this.isStarred ? 1 : 0));

    // Fork count
    document.getElementById('fork-count-text').textContent = `★ Fork ${profile.forks.toLocaleString()}`;

    // Live Demo Link
    const demoBtn = document.getElementById('live-demo-link');
    if (demoBtn) {
      demoBtn.href = profile.demoUrl;
      demoBtn.style.display = profile.demoUrl ? 'inline-flex' : 'none';
    }

    // Clone URL
    this.updateCloneInput();

    // KPIs
    this.animateNumber('kpi-stars-num', profile.stars);
    document.getElementById('kpi-stars-delta').textContent = profile.starsWeekDelta;
    document.getElementById('kpi-stars-footer').textContent = `${profile.starsGrowthPct} growth trajectory`;

    document.getElementById('kpi-velocity-num').textContent = profile.medianMergeTime;
    document.getElementById('kpi-ci-rate').textContent = `${profile.ciPassingRate} CI`;
    document.getElementById('kpi-velocity-footer').textContent = `Based on ${profile.ciRunsTotal} evaluated`;

    this.animateNumber('kpi-contributors-num', profile.contributorsCount);
    document.getElementById('kpi-contributors-footer').textContent = `Across ${profile.countriesCount} countries (${profile.newContributors})`;

    document.getElementById('kpi-release-cadence').textContent = profile.releaseCadence;
    document.getElementById('kpi-release-footer').textContent = `Mean cycle: ${profile.cycleDuration} • ${profile.lastReleaseDays}`;

    // Sparklines in KPI card
    this.renderKpiSparkline();

    // Star History Chart
    this.renderStarChart();

    // Language Distribution
    this.renderLanguages(profile.languages);

    // PR Table
    this.renderPrTable();
  },

  animateNumber(elementId, targetValue) {
    const el = document.getElementById(elementId);
    if (!el) return;
    const startValue = 0;
    const duration = 750;
    const startTime = performance.now();

    function update(time) {
      const elapsed = time - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const easeProgress = 1 - Math.pow(1 - progress, 3);
      const current = Math.floor(startValue + (targetValue - startValue) * easeProgress);
      el.textContent = current.toLocaleString();
      if (progress < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
  },

  toggleStar() {
    const profile = REPO_PROFILES[this.activeRepoKey];
    this.isStarred = !this.isStarred;
    localStorage.setItem(`starred_${profile.fullName}`, this.isStarred ? 'true' : 'false');

    const starBtn = document.getElementById('star-btn');
    starBtn?.classList.toggle('starred', this.isStarred);
    this.updateStarCountDisplay(profile.stars + (this.isStarred ? 1 : 0));

    if (this.isStarred) {
      this.showToast(`Starred ${profile.fullName}! ★ Thank you for supporting open source.`);
    } else {
      this.showToast(`Unstarred ${profile.fullName}`);
    }
  },

  updateStarCountDisplay(count) {
    const countEl = document.getElementById('star-count-display');
    if (countEl) countEl.textContent = count.toLocaleString();
  },

  switchProtocol(proto) {
    this.activeProtocol = proto;
    document.querySelectorAll('.protocol-tab').forEach(tab => {
      tab.classList.toggle('active', tab.getAttribute('data-proto') === proto);
    });
    this.updateCloneInput();
  },

  updateCloneInput() {
    const profile = REPO_PROFILES[this.activeRepoKey];
    const input = document.getElementById('clone-url-input');
    if (!input || !profile) return;

    if (this.activeProtocol === 'https') {
      input.value = `git clone ${profile.cloneHttps}`;
    } else if (this.activeProtocol === 'ssh') {
      input.value = `git clone ${profile.cloneSsh}`;
    } else if (this.activeProtocol === 'cli') {
      input.value = profile.cloneCli;
    }
  },

  copyCloneCommand() {
    const input = document.getElementById('clone-url-input');
    if (!input) return;
    navigator.clipboard.writeText(input.value).then(() => {
      this.showToast(`Copied clone command to clipboard: ${input.value}`);
      const btn = document.getElementById('copy-clone-btn');
      if (btn) {
        btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
        setTimeout(() => {
          btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>`;
        }, 1800);
      }
    });
  },

  renderKpiSparkline() {
    const box = document.getElementById('kpi-sparkline-box');
    if (!box) return;
    const points = [12, 16, 14, 22, 28, 25, 36, 42, 38, 48, 54, 65];
    const width = 180;
    const height = 36;
    const max = Math.max(...points);
    const min = Math.min(...points);

    const pathData = points.map((p, i) => {
      const x = (i / (points.length - 1)) * width;
      const y = height - ((p - min) / (max - min)) * (height - 8) - 4;
      return `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
    }).join(' ');

    box.innerHTML = `
      <svg class="sparkline-svg" viewBox="0 0 ${width} ${height}">
        <defs>
          <linearGradient id="spark-grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#10b981" stop-opacity="0.3"/>
            <stop offset="100%" stop-color="#10b981" stop-opacity="0.0"/>
          </linearGradient>
        </defs>
        <path d="${pathData} L ${width} ${height} L 0 ${height} Z" fill="url(#spark-grad)"/>
        <path d="${pathData}" fill="none" stroke="#10b981" stroke-width="2" stroke-linecap="round"/>
        <circle cx="${width}" cy="${height - ((points[points.length-1] - min) / (max - min)) * (height - 8) - 4}" r="3" fill="#10b981" filter="drop-shadow(0 0 4px #10b981)"/>
      </svg>
    `;
  },

  renderStarChart() {
    const container = document.getElementById('chart-viewport-box');
    const profile = REPO_PROFILES[this.activeRepoKey];
    if (!container || !profile) return;

    // Generate dynamic curve based on timeframe
    let pointCount = 18;
    let base = profile.stars * 0.4;
    let growthFactor = 1.0;

    if (this.activeChartTimeframe === '30D') {
      pointCount = 15;
      base = profile.stars - 1200;
    } else if (this.activeChartTimeframe === '90D') {
      pointCount = 20;
      base = profile.stars - 4800;
    } else if (this.activeChartTimeframe === '1Y') {
      pointCount = 24;
      base = profile.stars * 0.35;
    } else {
      pointCount = 30;
      base = 100;
    }

    const dataPoints = [];
    for (let i = 0; i < pointCount; i++) {
      const progress = i / (pointCount - 1);
      // Exponential curve with realistic organic jitter
      const curve = Math.pow(progress, 1.8);
      const jitter = (Math.sin(i * 1.5) * 0.05 + Math.cos(i * 2.1) * 0.03) * progress;
      const val = Math.round(base + (profile.stars - base) * (curve + jitter));
      dataPoints.push(Math.min(val, profile.stars));
    }
    dataPoints[dataPoints.length - 1] = profile.stars;

    const width = 760;
    const height = 230;
    const paddingX = 20;
    const paddingY = 25;
    const chartW = width - paddingX * 2;
    const chartH = height - paddingY * 2;

    const min = Math.min(...dataPoints);
    const max = Math.max(...dataPoints);

    // Compute bezier coordinates
    const coords = dataPoints.map((val, idx) => {
      const x = paddingX + (idx / (dataPoints.length - 1)) * chartW;
      const y = height - paddingY - ((val - min) / (max - min || 1)) * chartH;
      return { x, y, val };
    });

    let pathD = `M ${coords[0].x} ${coords[0].y}`;
    for (let i = 0; i < coords.length - 1; i++) {
      const cpX = (coords[i].x + coords[i + 1].x) / 2;
      pathD += ` C ${cpX} ${coords[i].y}, ${cpX} ${coords[i + 1].y}, ${coords[i + 1].x} ${coords[i + 1].y}`;
    }

    const areaD = `${pathD} L ${coords[coords.length - 1].x} ${height} L ${coords[0].x} ${height} Z`;

    // Horizontal gridlines
    const gridY1 = paddingY + chartH * 0.25;
    const gridY2 = paddingY + chartH * 0.5;
    const gridY3 = paddingY + chartH * 0.75;

    // Milestones pins
    const milestonePins = (profile.milestones || []).map(m => {
      const pinX = paddingX + (m.xPct / 100) * chartW;
      // Interpolate y
      const closestCoord = coords.reduce((prev, curr) => Math.abs(curr.x - pinX) < Math.abs(prev.x - pinX) ? curr : prev);
      return `
        <g class="milestone-pin-marker" transform="translate(${pinX}, ${closestCoord.y})">
          <circle cx="0" cy="0" r="5" fill="#8b5cf6" stroke="#ffffff" stroke-width="2"/>
          <circle cx="0" cy="0" r="10" fill="none" stroke="#8b5cf6" stroke-opacity="0.4" stroke-width="1.5">
            <animate attributeName="r" values="6;14;6" dur="2.5s" repeatCount="indefinite"/>
            <animate attributeName="stroke-opacity" values="0.8;0;0.8" dur="2.5s" repeatCount="indefinite"/>
          </circle>
        </g>
      `;
    }).join('');

    container.innerHTML = `
      <svg class="chart-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
        <defs>
          <linearGradient id="chart-area-grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#8b5cf6" stop-opacity="0.35"/>
            <stop offset="45%" stop-color="#10b981" stop-opacity="0.15"/>
            <stop offset="100%" stop-color="#10b981" stop-opacity="0.0"/>
          </linearGradient>
          <linearGradient id="chart-stroke-grad" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stop-color="#8b5cf6"/>
            <stop offset="60%" stop-color="#06b6d4"/>
            <stop offset="100%" stop-color="#10b981"/>
          </linearGradient>
        </defs>

        <!-- Subtle Grid lines -->
        <line x1="${paddingX}" y1="${gridY1}" x2="${width - paddingX}" y2="${gridY1}" stroke="rgba(255,255,255,0.04)" stroke-dasharray="4 4"/>
        <line x1="${paddingX}" y1="${gridY2}" x2="${width - paddingX}" y2="${gridY2}" stroke="rgba(255,255,255,0.04)" stroke-dasharray="4 4"/>
        <line x1="${paddingX}" y1="${gridY3}" x2="${width - paddingX}" y2="${gridY3}" stroke="rgba(255,255,255,0.04)" stroke-dasharray="4 4"/>

        <!-- Area Fill -->
        <path d="${areaD}" fill="url(#chart-area-grad)"/>

        <!-- Main Stroke Line -->
        <path d="${pathD}" fill="none" stroke="url(#chart-stroke-grad)" stroke-width="2.5" stroke-linecap="round"/>

        <!-- Milestone Pins -->
        ${milestonePins}

        <!-- Interactive Crosshair (hidden by default) -->
        <g id="chart-crosshair" style="opacity: 0; transition: opacity 0.15s ease;">
          <line id="crosshair-line" x1="0" y1="${paddingY}" x2="0" y2="${height - paddingY}" stroke="rgba(255,255,255,0.3)" stroke-dasharray="3 3"/>
          <circle id="crosshair-dot" cx="0" cy="0" r="5" fill="#10b981" stroke="#ffffff" stroke-width="2"/>
        </g>
      </svg>
      <div id="chart-floating-tooltip" class="chart-tooltip-floating">
        <div class="tooltip-date" id="tt-date">Milestone point</div>
        <div class="tooltip-stars" id="tt-stars">0 ★</div>
        <div class="tooltip-delta" id="tt-delta">+184 daily delta</div>
      </div>
    `;

    // Milestones Row Below Chart
    const milestoneList = document.getElementById('chart-milestones-row');
    if (milestoneList && profile.milestones) {
      milestoneList.innerHTML = profile.milestones.map(m => `
        <div class="milestone-chip">
          <span class="milestone-dot"></span>
          <strong>${m.label}:</strong>
          <span class="mono">${m.value}</span>
        </div>
      `).join('');
    }

    // Attach chart hover listener
    this.bindChartInteractiveHover(container, coords);
  },

  bindChartInteractiveHover(container, coords) {
    const svg = container.querySelector('svg');
    const tooltip = document.getElementById('chart-floating-tooltip');
    const crosshair = document.getElementById('chart-crosshair');
    const crosshairLine = document.getElementById('crosshair-line');
    const crosshairDot = document.getElementById('crosshair-dot');
    if (!svg || !tooltip || !crosshair) return;

    svg.addEventListener('mousemove', (e) => {
      const rect = svg.getBoundingClientRect();
      const mouseX = ((e.clientX - rect.left) / rect.width) * 760;

      // Find closest point
      const closest = coords.reduce((prev, curr) => Math.abs(curr.x - mouseX) < Math.abs(prev.x - mouseX) ? curr : prev);

      crosshair.style.opacity = '1';
      crosshairLine.setAttribute('x1', closest.x);
      crosshairLine.setAttribute('x2', closest.x);
      crosshairDot.setAttribute('cx', closest.x);
      crosshairDot.setAttribute('cy', closest.y);

      // Tooltip position
      const clientX = (closest.x / 760) * rect.width;
      const clientY = (closest.y / 230) * rect.height;

      tooltip.style.left = `${clientX}px`;
      tooltip.style.top = `${clientY}px`;
      tooltip.style.opacity = '1';

      document.getElementById('tt-stars').textContent = `${closest.val.toLocaleString()} ★`;
      document.getElementById('tt-date').textContent = `Trajectory Milestone`;
      document.getElementById('tt-delta').textContent = `Trajectory on ${this.activeChartTimeframe}`;
    });

    svg.addEventListener('mouseleave', () => {
      crosshair.style.opacity = '0';
      tooltip.style.opacity = '0';
    });
  },

  renderCommitHeatmap() {
    const grid = document.getElementById('heatmap-grid');
    if (!grid) return;

    const weeks = 52;
    const daysPerWeek = 7;
    const cells = [];
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    let totalCommits = 0;

    for (let w = 0; w < weeks; w++) {
      for (let d = 0; d < daysPerWeek; d++) {
        // Deterministic realistic density simulation
        const rand = Math.sin(w * 0.45 + d * 0.8) * 0.5 + Math.cos(w * 0.15) * 0.5;
        let count = 0;
        let level = 0;

        if (rand > 0.6) {
          count = Math.floor(Math.random() * 12) + 8;
          level = 4;
        } else if (rand > 0.3) {
          count = Math.floor(Math.random() * 6) + 4;
          level = 3;
        } else if (rand > 0.05) {
          count = Math.floor(Math.random() * 3) + 2;
          level = 2;
        } else if (rand > -0.2) {
          count = 1;
          level = 1;
        }

        totalCommits += count;
        cells.push(`
          <div class="heatmap-cell level-${level}" 
               data-count="${count}" 
               data-week="${w}"
               data-day="${d}"
               title="${count > 0 ? `${count} commits` : 'No commits on this day'}"></div>
        `);
      }
    }

    grid.innerHTML = cells.join('');

    const commitTotalEl = document.getElementById('commit-yearly-total');
    if (commitTotalEl) commitTotalEl.textContent = `${totalCommits.toLocaleString()} commits in the last year`;
  },

  renderLanguages(languages) {
    const bar = document.getElementById('lang-segment-bar');
    const legend = document.getElementById('lang-legend-grid');
    if (!bar || !legend || !languages) return;

    bar.innerHTML = languages.map(l => `
      <div class="lang-segment" style="width: ${l.pct}%; background: ${l.color};" title="${l.name}: ${l.pct}%"></div>
    `).join('');

    legend.innerHTML = languages.map(l => `
      <div class="lang-legend-item">
        <div style="display:flex; align-items:center;">
          <span class="lang-color-dot" style="background:${l.color};"></span>
          <span style="font-weight:700; color:var(--text-primary);">${l.name}</span>
        </div>
        <div style="display:flex; align-items:baseline; gap:0.5rem;">
          <span class="mono" style="font-weight:700; color:var(--text-primary); font-size:0.85rem;">${l.pct}%</span>
          <span class="mono" style="color:var(--text-muted); font-size:0.72rem;">${l.lines}</span>
        </div>
      </div>
    `).join('');
  },

  renderPrTable() {
    const tbody = document.getElementById('pr-table-body');
    const profile = REPO_PROFILES[this.activeRepoKey];
    if (!tbody || !profile) return;

    let prs = profile.prs || [];
    if (this.activeFilterType !== 'all') {
      prs = prs.filter(p => p.type === this.activeFilterType);
    }

    tbody.innerHTML = prs.map(pr => `
      <tr onclick="LuxuryAnalytics.openDiffModal('${pr.id}')">
        <td style="font-family:var(--font-mono); font-weight:700; color:var(--text-muted);">${pr.id}</td>
        <td>
          <div class="pr-title-cell">
            <span class="pr-main-title">
              <span class="pr-type-tag tag-${pr.type}">${pr.type.toUpperCase()}</span>
              ${pr.title}
            </span>
          </div>
        </td>
        <td>
          <div class="author-cell">
            <img class="author-avatar" src="${pr.avatar}" alt="${pr.author}">
            <span class="author-handle">@${pr.author}</span>
          </div>
        </td>
        <td>
          <span class="branch-pill">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="6" y1="3" x2="6" y2="15"></line><circle cx="18" cy="6" r="3"></circle><circle cx="6" cy="18" r="3"></circle><path d="M18 9a9 9 0 0 1-9 9"></path></svg>
            ${pr.branch}
          </span>
        </td>
        <td>
          <span class="check-pass-badge">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>
            ${pr.checks}
          </span>
        </td>
        <td style="font-family:var(--font-mono); font-size:0.78rem; color:var(--text-muted);">${pr.time}</td>
        <td>
          <button class="view-diff-btn">View Diff &rarr;</button>
        </td>
      </tr>
    `).join('');
  },

  searchPrs(query) {
    const q = query.toLowerCase().trim();
    const rows = document.querySelectorAll('#pr-table-body tr');
    rows.forEach(r => {
      const text = r.textContent.toLowerCase();
      r.style.display = text.includes(q) ? '' : 'none';
    });
  },

  openDiffModal(prId) {
    const profile = REPO_PROFILES[this.activeRepoKey];
    const pr = (profile.prs || []).find(p => p.id === prId);
    if (!pr) return;

    document.getElementById('modal-pr-title').textContent = `${pr.id} — ${pr.title}`;
    document.getElementById('modal-pr-stats').innerHTML = `
      <span class="diff-stat-add">+${pr.additions}</span> additions &bull; 
      <span class="diff-stat-del">-${pr.deletions}</span> deletions &bull; 
      ${pr.files} files modified
    `;

    // Render highlighted diff lines
    const diffLines = pr.diff.split('\n').map(line => {
      let cls = 'ctx';
      if (line.startsWith('+') && !line.startsWith('+++')) cls = 'add';
      else if (line.startsWith('-') && !line.startsWith('---')) cls = 'del';
      return `<div class="diff-line ${cls}">${escapeHtml(line)}</div>`;
    }).join('');

    document.getElementById('modal-diff-content').innerHTML = `
      <div class="diff-file-block">
        <div class="diff-file-header">
          <span>${pr.branch.split('←')[1].trim()}</span>
          <span style="font-weight:400; color:var(--text-muted); font-size:0.72rem;">Commit hash: 8a4b2c1f</span>
        </div>
        ${diffLines}
      </div>
    `;

    document.getElementById('diff-modal-backdrop')?.classList.add('active');
  },

  closeDiffModal() {
    document.getElementById('diff-modal-backdrop')?.classList.remove('active');
  },

  initMouseSpotlight() {
    document.querySelectorAll('.luxury-glass-card, .repo-identity-header').forEach(card => {
      card.addEventListener('mousemove', (e) => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        card.style.setProperty('--mouse-x', `${x}px`);
        card.style.setProperty('--mouse-y', `${y}px`);
      });
    });
  },

  showToast(message) {
    const toast = document.getElementById('luxury-toast');
    if (!toast) return;
    toast.querySelector('.toast-msg').textContent = message;
    toast.classList.add('active');
    setTimeout(() => {
      toast.classList.remove('active');
    }, 3200);
  }
};

function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

document.addEventListener('DOMContentLoaded', () => {
  LuxuryAnalytics.init();
});
