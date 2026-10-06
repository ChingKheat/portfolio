/**
 * User View Application Logic: Clean Projects Explorer & Showcase
 */

const App = {
  allProjects: [],
  filteredProjects: [],
  currentConfig: null,

  languageColors: {
    'Dart': '#00B4AB',
    'Flutter': '#02569B',
    'Vue': '#41B883',
    'HTML': '#e34c26',
    'CSS': '#563d7c',
    'JavaScript': '#f1e05a',
    'TypeScript': '#3178c6',
    'Python': '#3572A5',
    'Java': '#b07219',
    'Mobile App': '#00B4AB',
    'Code': '#8b99ad'
  },

  async init() {
    this.initTheme();
    this.bindEvents();
    await this.loadData();
    this.initAutoSync();
  },

  initTheme() {
    const savedTheme = localStorage.getItem('theme_preference') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    this.updateThemeIcon(savedTheme);
  },

  toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('theme_preference', next);
    this.updateThemeIcon(next);
  },

  updateThemeIcon(theme) {
    const themeBtn = document.getElementById('theme-toggle-btn');
    if (!themeBtn) return;
    if (theme === 'dark') {
      themeBtn.innerHTML = `
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="5"></circle>
          <line x1="12" y1="1" x2="12" y2="3"></line>
          <line x1="12" y1="21" x2="12" y2="23"></line>
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
          <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
          <line x1="1" y1="12" x2="3" y2="12"></line>
          <line x1="21" y1="12" x2="23" y2="12"></line>
          <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
          <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
        </svg>
      `;
      themeBtn.setAttribute('title', 'Switch to Light Mode');
    } else {
      themeBtn.innerHTML = `
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
        </svg>
      `;
      themeBtn.setAttribute('title', 'Switch to Dark Mode');
    }
  },

  bindEvents() {
    // Theme toggle
    document.getElementById('theme-toggle-btn')?.addEventListener('click', () => this.toggleTheme());

    // Search and filters
    document.getElementById('search-input')?.addEventListener('input', () => this.applyFilters());
    document.getElementById('language-filter')?.addEventListener('change', () => this.applyFilters());
    document.getElementById('demo-filter')?.addEventListener('change', () => this.applyFilters());

    // Modal Close
    document.getElementById('modal-close-btn')?.addEventListener('click', () => this.closeModal());
    document.getElementById('project-modal')?.addEventListener('click', (e) => {
      if (e.target.id === 'project-modal') this.closeModal();
    });

    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') this.closeModal();
    });
  },

  async loadData() {
    try {
      this.currentConfig = await ConfigManager.loadConfig();
      const username = (this.currentConfig && this.currentConfig.settings && this.currentConfig.settings.githubUsername) || 'ChingKheat';

      // Update titles
      const pageTitle = document.getElementById('page-title');
      if (pageTitle) pageTitle.textContent = this.currentConfig.settings.dashboardTitle || `${username}'s Project Showcase`;
      const brandTitle = document.getElementById('nav-brand-title');
      if (brandTitle) brandTitle.textContent = `${username} | Project Showcase`;

      // Fetch GitHub data with safe fallbacks
      let profile = { login: username, name: username, bio: 'Full-Stack & Mobile Developer specializing in Flutter, Vue/Nuxt, and intelligent data-driven dashboards.', public_repos: 8 };
      let ghRepos = [];

      try {
        if (typeof GitHubAPI !== 'undefined' && GitHubAPI.getUserProfile) {
          const results = await Promise.all([
            GitHubAPI.getUserProfile(username).catch(() => profile),
            GitHubAPI.getUserRepositories(username).catch(() => [])
          ]);
          profile = results[0] || profile;
          ghRepos = results[1] || [];
        }
      } catch (ghErr) {
        console.warn('GitHub API fetch failed or rate limited; using local configuration:', ghErr);
      }

      this.renderProfile(profile, username);

      // Merge GitHub repos with our configs
      const merged = ConfigManager.mergeReposWithConfig(ghRepos, this.currentConfig);
      this.allProjects = merged.filter(p => p.visible !== false);
      this.filteredProjects = [...this.allProjects];

      // Populate filter dropdowns
      this.populateFilterOptions();

      // Render project cards
      this.renderProjectsGrid();

    } catch (err) {
      console.error('Initialization error:', err);
      // Fallback: render from config immediately so user is never blocked
      if (this.currentConfig && this.currentConfig.projects) {
        try {
          const fallbackMerged = ConfigManager.mergeReposWithConfig([], this.currentConfig);
          this.allProjects = fallbackMerged.filter(p => p.visible !== false);
          this.filteredProjects = [...this.allProjects];
          this.populateFilterOptions();
          this.renderProjectsGrid();
        } catch (e2) {
          console.error('Fallback render error:', e2);
        }
      }
    }
  },

  renderProfile(profile, username) {
    const avatarEl = document.getElementById('user-avatar');
    if (avatarEl) {
      avatarEl.src = this.currentConfig.settings.avatarUrl || profile.avatar_url || `https://github.com/${username}.png`;
      avatarEl.alt = profile.name || username;
    }

    const nameEl = document.getElementById('user-name');
    if (nameEl) nameEl.textContent = profile.name || username;

    const handleEl = document.getElementById('user-handle');
    if (handleEl) {
      handleEl.textContent = `@${profile.login || username}`;
      handleEl.href = profile.html_url || `https://github.com/${username}`;
    }

    const bioEl = document.getElementById('user-bio');
    if (bioEl) {
      bioEl.textContent = this.currentConfig.settings.bioOverride || profile.bio || 'Interactive project portfolio featuring live web applications and mobile apps.';
    }

    const totalLiveDemos = this.allProjects.filter(p => p.hasLiveDemo).length;
    const totalReposEl = document.getElementById('stat-total-repos');
    if (totalReposEl) totalReposEl.textContent = `${totalLiveDemos} Live Demos Available`;
  },

  /**
   * PROJECTS GRID (EXPLORER CARDS)
   */
  renderProjectsGrid() {
    const container = document.getElementById('projects-grid');
    const countEl = document.getElementById('project-results-count');
    if (!container) return;

    if (countEl) {
      countEl.textContent = `Showing ${this.filteredProjects.length} projects`;
    }

    if (this.filteredProjects.length === 0) {
      container.innerHTML = `
        <div style="grid-column: 1 / -1; text-align:center; padding:3rem 1rem; color:var(--text-muted);">
          <h3>No matching projects found</h3>
          <p>Try searching for a different keyword or resetting filters.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = this.filteredProjects.map(p => this.createDemoCardHTML(p)).join('');

    // Attach details modal click
    container.querySelectorAll('.view-details-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        const repoName = e.currentTarget.getAttribute('data-repo');
        this.openProjectModal(repoName);
      });
    });
  },

  createDemoCardHTML(project) {
    const liveIndicator = project.hasLiveDemo
      ? `<span class="live-pill banner-live-indicator"><span class="pulse-dot"></span> Live Demo</span>`
      : '';

    const privateIndicator = project.isPrivate
      ? `<span class="banner-private-indicator" style="position:absolute; top:12px; left:12px; background:rgba(20,24,33,0.85); backdrop-filter:blur(6px); color:#ff7b72; border:1px solid rgba(255,123,114,0.4); font-size:0.75rem; padding:3px 9px; border-radius:999px; font-weight:700; display:inline-flex; align-items:center; gap:4px; z-index:2;">
           <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
           Private
         </span>`
      : '';

    const badgeHTML = project.badge
      ? `<span class="banner-overlay-badge">${project.badge}</span>`
      : '';

    const coverHTML = project.coverImage
      ? `<img src="${project.coverImage}" alt="${project.customTitle}" loading="lazy">`
      : `<div style="width:100%; height:100%; display:flex; align-items:center; justify-content:center; background:linear-gradient(135deg, rgba(56,139,253,0.15), rgba(188,140,255,0.15)); font-weight:700; color:var(--text-muted);">${project.language || 'Code'}</div>`;

    const tagsHTML = (project.tags || []).slice(0, 3).map(t => `<span class="tag-pill">${t}</span>`).join('');

    // Go to dedicated demo page when chosen!
    const demoLink = `demo.html?project=${encodeURIComponent(project.name)}`;

    const primaryActionBtn = project.hasLiveDemo
      ? `<a href="${demoLink}" class="btn-primary" style="text-decoration:none;">
           <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
           Play Demo
         </a>`
      : `<a href="${demoLink}" class="btn-primary" style="background:var(--bg-surface-elevated); color:var(--text-main); border:1px solid var(--border-color); text-decoration:none;">
           View Overview
         </a>`;

    const githubBtnText = project.isPrivate ? '🔒 Private Code' : 'GitHub Code';

    return `
      <div class="demo-card" data-repo="${project.name}">
        <a href="${demoLink}" class="card-banner-wrapper" style="display:block; position:relative;">
          ${coverHTML}
          ${privateIndicator}
          ${liveIndicator}
          ${badgeHTML}
        </a>
        <div class="card-body">
          <div class="card-title-row">
            <h3 class="card-title">
              <a href="${demoLink}" style="color:inherit;">${project.customTitle}</a>
            </h3>
          </div>
          <p class="card-desc">${project.customDescription}</p>
          <div class="tags-row">${tagsHTML}</div>
          <div class="card-footer-actions">
            ${primaryActionBtn}
            <a href="${project.htmlUrl}" target="_blank" rel="noopener" class="btn-secondary" style="text-decoration:none;" title="${project.isPrivate ? 'Private repository on GitHub' : 'Open repository on GitHub'}">
              ${githubBtnText}
            </a>
          </div>
        </div>
      </div>
    `;
  },

  applyFilters() {
    const searchVal = document.getElementById('search-input')?.value.toLowerCase().trim() || '';
    const langVal = document.getElementById('language-filter')?.value || 'all';
    const filterVal = document.getElementById('demo-filter')?.value || 'all';

    this.filteredProjects = this.allProjects.filter(p => {
      const matchSearch = !searchVal ||
        p.customTitle.toLowerCase().includes(searchVal) ||
        p.name.toLowerCase().includes(searchVal) ||
        p.customDescription.toLowerCase().includes(searchVal) ||
        (p.tags && p.tags.some(t => t.toLowerCase().includes(searchVal)));

      const matchLang = langVal === 'all' || p.language === langVal;
      
      let matchFilter = true;
      if (filterVal === 'demo_only') matchFilter = p.hasLiveDemo === true;
      if (filterVal === 'private_only') matchFilter = p.isPrivate === true;
      if (filterVal === 'public_only') matchFilter = p.isPrivate !== true;

      return matchSearch && matchLang && matchFilter;
    });

    this.renderProjectsGrid();
  },

  populateFilterOptions() {
    const langSelect = document.getElementById('language-filter');
    if (langSelect) {
      const languages = Array.from(new Set(this.allProjects.map(p => p.language).filter(Boolean))).sort();
      langSelect.innerHTML = '<option value="all">All Tech Stacks</option>' +
        languages.map(l => `<option value="${l}">${l}</option>`).join('');
    }
  },

  openProjectModal(repoName) {
    const project = this.allProjects.find(p => p.name === repoName);
    if (!project) return;

    const modal = document.getElementById('project-modal');
    if (!modal) return;

    document.getElementById('modal-title-text').textContent = project.customTitle;
    document.getElementById('modal-desc').textContent = project.customDescription;

    const tagsContainer = document.getElementById('modal-tags');
    if (tagsContainer) {
      tagsContainer.innerHTML = (project.tags || []).map(t => `<span class="tag-pill">${t}</span>`).join('');
    }

    const githubLink = document.getElementById('modal-github-link');
    if (githubLink) githubLink.href = project.htmlUrl;

    const demoBtn = document.getElementById('modal-demo-btn');
    if (demoBtn) {
      if (project.demoUrl) {
        demoBtn.style.display = 'inline-flex';
        demoBtn.href = `demo.html?project=${encodeURIComponent(project.name)}`;
      } else {
        demoBtn.style.display = 'none';
      }
    }

    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
  },

  closeModal() {
    const modal = document.getElementById('project-modal');
    if (modal) modal.classList.remove('active');
    document.body.style.overflow = '';
  },

  showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 3200);
  },

  lastSyncTime: Date.now(),

  initAutoSync() {
    const chip = document.getElementById('auto-sync-chip');
    if (chip) {
      chip.addEventListener('click', () => this.syncFromGitHub(true));
    }

    // Auto-sync when user returns to tab after > 3 minutes
    window.addEventListener('focus', () => {
      const now = Date.now();
      if (now - this.lastSyncTime > 3 * 60 * 1000) {
        this.syncFromGitHub(false);
      }
    });

    // Periodic background sync every 10 minutes
    setInterval(() => {
      this.syncFromGitHub(false);
    }, 10 * 60 * 1000);
  },

  async syncFromGitHub(isManual = false) {
    const dot = document.getElementById('sync-dot');
    const label = document.getElementById('sync-label');

    if (dot) {
      dot.style.background = '#e3b341';
      dot.style.boxShadow = '0 0 8px #e3b341';
    }
    if (label) label.textContent = 'Syncing...';

    try {
      const username = (this.currentConfig && this.currentConfig.settings && this.currentConfig.settings.githubUsername) || 'ChingKheat';
      
      // Fetch fresh repos with forceRefresh=true
      if (typeof GitHubAPI !== 'undefined' && GitHubAPI.getUserRepositories) {
        const freshRepos = await GitHubAPI.getUserRepositories(username, true, 0).catch(() => []);
        
        if (freshRepos && freshRepos.length > 0) {
          const merged = ConfigManager.mergeReposWithConfig(freshRepos, this.currentConfig);
          this.allProjects = merged.filter(p => p.visible !== false);
          this.applyFilters();
        }
      }

      this.lastSyncTime = Date.now();
      const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

      if (dot) {
        dot.style.background = '#3fb950';
        dot.style.boxShadow = '0 0 8px rgba(63, 185, 80, 0.4)';
      }
      if (label) label.textContent = `Synced ${timeStr}`;

      if (isManual) {
        this.showToast('Synchronized with GitHub successfully!', 'success');
      }
    } catch (e) {
      console.warn('Auto-sync background check failed:', e);
      if (dot) {
        dot.style.background = '#3fb950';
        dot.style.boxShadow = '';
      }
      if (label) label.textContent = 'Auto-Sync Active';
    }
  }
};

window.App = App;

document.addEventListener('DOMContentLoaded', () => App.init());
