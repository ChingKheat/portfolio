/**
 * User View Application Logic: Project Showcase, Search, Filtering, and Modals
 */

const App = {
  allProjects: [],
  filteredProjects: [],
  currentConfig: null,
  activeView: 'grid',
  activeProject: null,

  // Language color mappings matching GitHub's standard colors
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
    'C++': '#f34b7d',
    'C': '#555555',
    'C#': '#178600',
    'PHP': '#4F5D95',
    'Go': '#00ADD8',
    'Rust': '#dea584',
    'Kotlin': '#A97BFF',
    'Swift': '#F05138',
    'Shell': '#89e051',
    'Code': '#8b949e'
  },

  async init() {
    this.initTheme();
    this.bindEvents();
    await this.loadData();
  },

  /**
   * Initialize and restore Dark/Light theme
   */
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

  /**
   * Bind DOM event listeners
   */
  bindEvents() {
    // Theme toggle
    document.getElementById('theme-toggle-btn')?.addEventListener('click', () => this.toggleTheme());

    // Search and filters
    document.getElementById('search-input')?.addEventListener('input', () => this.applyFilters());
    document.getElementById('language-filter')?.addEventListener('change', () => this.applyFilters());
    document.getElementById('tag-filter')?.addEventListener('change', () => this.applyFilters());
    document.getElementById('sort-select')?.addEventListener('change', () => this.applyFilters());

    // View toggle buttons
    document.getElementById('view-grid-btn')?.addEventListener('click', () => this.setView('grid'));
    document.getElementById('view-list-btn')?.addEventListener('click', () => this.setView('list'));

    // Modal Close
    document.getElementById('modal-close-btn')?.addEventListener('click', () => this.closeModal());
    document.getElementById('project-modal')?.addEventListener('click', (e) => {
      if (e.target.id === 'project-modal') this.closeModal();
    });

    // Modal Tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const tab = e.currentTarget.getAttribute('data-tab');
        this.switchModalTab(tab);
      });
    });

    // Keyboard ESC to close modal
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') this.closeModal();
    });
  },

  /**
   * Load all GitHub data and configuration
   */
  async loadData() {
    try {
      this.currentConfig = await ConfigManager.loadConfig();
      const username = this.currentConfig.settings.githubUsername || 'ChingKheat';

      // Update basic texts from config
      document.getElementById('page-title').textContent = this.currentConfig.settings.dashboardTitle || `${username}'s Project Showcase`;
      document.getElementById('header-subtitle').textContent = this.currentConfig.settings.dashboardSubtitle || 'GitHub Projects Dashboard';
      document.getElementById('nav-brand-title').textContent = this.currentConfig.settings.dashboardTitle || `${username} Projects`;

      // Fetch GitHub profile & repos concurrently
      const [profile, ghRepos] = await Promise.all([
        GitHubAPI.getUserProfile(username).catch(err => {
          console.warn('Profile fetch warning:', err);
          return { login: username, name: username, bio: 'Developer & Creator', public_repos: 0 };
        }),
        GitHubAPI.getUserRepositories(username).catch(err => {
          console.warn('Repositories fetch warning:', err);
          return [];
        })
      ]);

      // Render profile header
      this.renderProfile(profile, username);

      // Merge and filter
      const merged = ConfigManager.mergeReposWithConfig(ghRepos, this.currentConfig);
      // Keep only visible projects for public view
      this.allProjects = merged.filter(p => p.visible !== false);

      // Populate filter dropdowns
      this.populateFilterOptions();

      // Render language summary
      this.renderLanguageSummary();

      // Render projects
      this.applyFilters();
      this.renderFeaturedProjects();

    } catch (err) {
      console.error('Initialization error:', err);
      this.showToast('Failed to load GitHub data. Please check connection.', 'error');
    }
  },

  /**
   * Render User Profile Header
   */
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
      bioEl.textContent = this.currentConfig.settings.bioOverride || profile.bio || 'Showcasing open-source projects, applications, and experiments.';
    }

    // Stats
    const totalReposEl = document.getElementById('stat-total-repos');
    if (totalReposEl) totalReposEl.textContent = profile.public_repos || this.allProjects.length;

    const githubLinkEl = document.getElementById('user-github-link');
    if (githubLinkEl) githubLinkEl.href = profile.html_url || `https://github.com/${username}`;
  },

  /**
   * Render Featured / Pinned Projects Spotlight
   */
  renderFeaturedProjects() {
    const container = document.getElementById('featured-grid');
    if (!container) return;

    const featured = this.allProjects.filter(p => p.pinned);
    const featuredSection = document.getElementById('featured-section');

    if (featured.length === 0) {
      if (featuredSection) featuredSection.style.display = 'none';
      return;
    }

    if (featuredSection) featuredSection.style.display = 'block';
    container.innerHTML = featured.map(p => this.createFeaturedCardHTML(p)).join('');

    // Attach card click handlers
    container.querySelectorAll('.featured-card').forEach(card => {
      card.addEventListener('click', (e) => {
        // Prevent opening modal if clicking direct links
        if (e.target.closest('a')) return;
        const repoName = card.getAttribute('data-repo');
        this.openProjectModal(repoName);
      });
    });
  },

  createFeaturedCardHTML(project) {
    const langColor = this.languageColors[project.language] || '#8b949e';
    const coverHTML = project.coverImage
      ? `<div class="featured-cover"><img src="${project.coverImage}" alt="${project.customTitle}" loading="lazy"></div>`
      : `<div class="featured-cover"><div class="featured-cover-placeholder"><span>No Preview Cover</span></div></div>`;

    const badgeHTML = project.badge ? `<div class="featured-badge">${project.badge}</div>` : '';

    const tagsHTML = (project.tags || []).slice(0, 4).map(t => `<span class="tag-pill">${t}</span>`).join('');

    const demoBtn = project.demoUrl
      ? `<a href="${project.demoUrl}" target="_blank" rel="noopener" class="btn-primary" title="Live Demo">Live Demo</a>`
      : '';

    return `
      <div class="featured-card" data-repo="${project.name}">
        ${coverHTML}
        ${badgeHTML}
        <div class="featured-body">
          <div class="featured-title">
            <span>${project.customTitle}</span>
            <span style="display:inline-flex; align-items:center; gap:4px; font-size:0.8rem; font-weight:normal; color:var(--text-muted);">
              <span class="lang-dot" style="background:${langColor};"></span>
              ${project.language}
            </span>
          </div>
          <p class="featured-desc">${project.customDescription}</p>
          <div class="tags-row">${tagsHTML}</div>
          <div class="card-actions">
            ${demoBtn}
            <a href="${project.htmlUrl}" target="_blank" rel="noopener" class="btn-secondary" title="View Source">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
              </svg>
              GitHub
            </a>
          </div>
        </div>
      </div>
    `;
  },

  /**
   * Render All Repositories Grid
   */
  renderProjectsGrid() {
    const container = document.getElementById('projects-grid');
    const countEl = document.getElementById('project-results-count');
    if (!container) return;

    if (countEl) {
      countEl.textContent = `Showing ${this.filteredProjects.length} of ${this.allProjects.length} projects`;
    }

    if (this.filteredProjects.length === 0) {
      container.innerHTML = `
        <div class="empty-state" style="grid-column: 1 / -1;">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
          <h3>No projects match your filter</h3>
          <p>Try searching for a different keyword or reset filters.</p>
        </div>
      `;
      return;
    }

    container.className = `projects-grid ${this.activeView === 'list' ? 'list-view' : ''}`;
    container.innerHTML = this.filteredProjects.map(p => this.createRepoCardHTML(p)).join('');

    // Attach card click handlers
    container.querySelectorAll('.repo-card').forEach(card => {
      card.addEventListener('click', (e) => {
        if (e.target.closest('a')) return;
        const repoName = card.getAttribute('data-repo');
        this.openProjectModal(repoName);
      });
    });
  },

  createRepoCardHTML(project) {
    const langColor = this.languageColors[project.language] || '#8b949e';
    const updatedDate = new Date(project.updatedAt).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
    const isPinnedBadge = project.pinned ? `<span class="badge-pill pinned">★ Pinned</span>` : '';

    return `
      <div class="repo-card" data-repo="${project.name}">
        <div>
          <div class="repo-header">
            <h3 class="repo-title">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path d="M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5v-9zm10.5-1V9h-8c-.356 0-.694.074-1 .208V2.5a1 1 0 0 1 1-1h8zM5 12.25v3.25a.25.25 0 0 0 .4.2l1.45-1.087a.25.25 0 0 1 .3 0L8.6 15.7a.25.25 0 0 0 .4-.2v-3.25a.25.25 0 0 0-.25-.25h-3.5a.25.25 0 0 0-.25.25z"/>
              </svg>
              ${project.customTitle}
            </h3>
            <div class="repo-badges">
              ${isPinnedBadge}
            </div>
          </div>
          <p class="repo-desc">${project.customDescription}</p>
        </div>
        <div class="repo-meta">
          <span class="meta-item">
            <span class="lang-dot" style="background:${langColor};"></span>
            ${project.language}
          </span>
          <span class="meta-item">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
              <path d="M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.75.75 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25z"/>
            </svg>
            ${project.stars}
          </span>
          <span class="meta-item">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
              <path d="M5 3.25a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0zm0 2.122a2.25 2.25 0 1 0-1.5 0v.878A2.25 2.25 0 0 0 5.75 8.5h4.5A2.25 2.25 0 0 0 12.5 6.25v-.878a2.25 2.25 0 1 0-1.5 0V6.25a.75.75 0 0 1-.75.75h-4.5A.75.75 0 0 1 5 6.25v-.878zM12.5 3.25a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0zM5 12.75a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0zm0 2.122a2.25 2.25 0 1 0-1.5 0V11a2.25 2.25 0 0 0 2.25-2.25h.5a.75.75 0 0 1 0 1.5h-.5A.75.75 0 0 0 5 11v3.872z"/>
            </svg>
            ${project.forks}
          </span>
          <span class="meta-item" style="margin-left: auto;">Updated ${updatedDate}</span>
        </div>
      </div>
    `;
  },

  /**
   * Filter and Sort Logic
   */
  applyFilters() {
    const searchVal = document.getElementById('search-input')?.value.toLowerCase().trim() || '';
    const langVal = document.getElementById('language-filter')?.value || 'all';
    const tagVal = document.getElementById('tag-filter')?.value || 'all';
    const sortVal = document.getElementById('sort-select')?.value || 'updated';

    this.filteredProjects = this.allProjects.filter(p => {
      // Text search
      const matchesSearch = !searchVal || 
        p.customTitle.toLowerCase().includes(searchVal) ||
        p.name.toLowerCase().includes(searchVal) ||
        p.customDescription.toLowerCase().includes(searchVal) ||
        (p.tags && p.tags.some(t => t.toLowerCase().includes(searchVal)));

      // Language filter
      const matchesLang = langVal === 'all' || p.language === langVal;

      // Tag filter
      const matchesTag = tagVal === 'all' || (p.tags && p.tags.includes(tagVal));

      return matchesSearch && matchesLang && matchesTag;
    });

    // Sort
    this.filteredProjects.sort((a, b) => {
      if (sortVal === 'stars') return b.stars - a.stars;
      if (sortVal === 'name') return a.customTitle.localeCompare(b.customTitle);
      if (sortVal === 'size') return b.sizeKb - a.sizeKb;
      // Default: updated
      return new Date(b.updatedAt) - new Date(a.updatedAt);
    });

    this.renderProjectsGrid();
  },

  /**
   * Switch View Mode (Grid vs List)
   */
  setView(mode) {
    this.activeView = mode;
    document.getElementById('view-grid-btn')?.classList.toggle('active', mode === 'grid');
    document.getElementById('view-list-btn')?.classList.toggle('active', mode === 'list');
    this.renderProjectsGrid();
  },

  /**
   * Populate Language & Tag Filter Dropdowns
   */
  populateFilterOptions() {
    const langSelect = document.getElementById('language-filter');
    const tagSelect = document.getElementById('tag-filter');

    if (langSelect) {
      const languages = Array.from(new Set(this.allProjects.map(p => p.language).filter(Boolean))).sort();
      langSelect.innerHTML = '<option value="all">All Languages</option>' +
        languages.map(l => `<option value="${l}">${l}</option>`).join('');
    }

    if (tagSelect) {
      const tags = Array.from(new Set(this.allProjects.flatMap(p => p.tags || []).filter(Boolean))).sort();
      tagSelect.innerHTML = '<option value="all">All Tags</option>' +
        tags.map(t => `<option value="${t}">${t}</option>`).join('');
    }
  },

  /**
   * Render Language Distribution Summary Bar
   */
  renderLanguageSummary() {
    const bar = document.getElementById('lang-progress-bar');
    const legend = document.getElementById('lang-legend');
    if (!bar || !legend) return;

    const counts = {};
    let total = 0;
    this.allProjects.forEach(p => {
      if (p.language) {
        counts[p.language] = (counts[p.language] || 0) + 1;
        total++;
      }
    });

    if (total === 0) return;

    const sortedLangs = Object.entries(counts).sort((a, b) => b[1] - a[1]);

    // Progress Bar
    bar.innerHTML = sortedLangs.map(([lang, count]) => {
      const pct = ((count / total) * 100).toFixed(1);
      const color = this.languageColors[lang] || '#8b949e';
      return `<div class="lang-progress-segment" style="width: ${pct}%; background: ${color};" title="${lang}: ${pct}%"></div>`;
    }).join('');

    // Legend
    legend.innerHTML = sortedLangs.map(([lang, count]) => {
      const pct = ((count / total) * 100).toFixed(1);
      const color = this.languageColors[lang] || '#8b949e';
      return `
        <div class="lang-legend-item">
          <span class="lang-dot" style="background:${color};"></span>
          <span><strong>${lang}</strong> ${pct}%</span>
        </div>
      `;
    }).join('');
  },

  /**
   * Open Project Detail Modal
   */
  async openProjectModal(repoName) {
    const project = this.allProjects.find(p => p.name === repoName);
    if (!project) return;
    this.activeProject = project;

    const modal = document.getElementById('project-modal');
    if (!modal) return;

    // Header info
    document.getElementById('modal-repo-name').textContent = project.customTitle;
    const githubLink = document.getElementById('modal-github-link');
    if (githubLink) githubLink.href = project.htmlUrl;

    const demoLink = document.getElementById('modal-demo-link');
    if (demoLink) {
      if (project.demoUrl) {
        demoLink.href = project.demoUrl;
        demoLink.style.display = 'inline-flex';
      } else {
        demoLink.style.display = 'none';
      }
    }

    // Clone command
    const cloneCode = document.getElementById('modal-clone-code');
    if (cloneCode) {
      cloneCode.textContent = `git clone ${project.htmlUrl}.git`;
    }
    const copyBtn = document.getElementById('modal-copy-clone-btn');
    if (copyBtn) {
      copyBtn.onclick = () => {
        navigator.clipboard.writeText(`git clone ${project.htmlUrl}.git`);
        this.showToast('Clone command copied to clipboard!', 'success');
      };
    }

    // Populate Overview Tab
    document.getElementById('modal-desc').textContent = project.customDescription;
    const tagsContainer = document.getElementById('modal-tags');
    if (tagsContainer) {
      tagsContainer.innerHTML = (project.tags || []).map(t => `<span class="tag-pill">${t}</span>`).join('');
    }

    document.getElementById('modal-stat-stars').textContent = project.stars;
    document.getElementById('modal-stat-forks').textContent = project.forks;
    document.getElementById('modal-stat-watchers').textContent = project.watchers;
    document.getElementById('modal-stat-branch').textContent = project.defaultBranch;
    document.getElementById('modal-stat-updated').textContent = new Date(project.updatedAt).toLocaleDateString();

    // Default to overview tab
    this.switchModalTab('overview');

    // Show modal
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';

    // Lazy load README in the background
    this.loadModalReadme(project);
  },

  closeModal() {
    const modal = document.getElementById('project-modal');
    if (modal) modal.classList.remove('active');
    document.body.style.overflow = '';
    this.activeProject = null;
  },

  switchModalTab(tabId) {
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-tab') === tabId);
    });
    document.querySelectorAll('.tab-pane').forEach(pane => {
      pane.style.display = pane.id === `tab-${tabId}` ? 'block' : 'none';
    });
  },

  async loadModalReadme(project) {
    const readmeContainer = document.getElementById('modal-readme-content');
    if (!readmeContainer) return;

    readmeContainer.innerHTML = '<p style="color:var(--text-muted);">Fetching README documentation from GitHub...</p>';

    const username = this.currentConfig.settings.githubUsername || 'ChingKheat';
    const readmeText = await GitHubAPI.getRepoReadme(username, project.name);

    if (readmeText && window.marked) {
      readmeContainer.innerHTML = window.marked.parse(readmeText);
    } else if (readmeText) {
      readmeContainer.innerText = readmeText;
    } else {
      readmeContainer.innerHTML = '<p style="color:var(--text-dim); font-style:italic;">No README.md found in this repository.</p>';
    }
  },

  /**
   * Toast notification helper
   */
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
    }, 3500);
  }
};

document.addEventListener('DOMContentLoaded', () => App.init());
