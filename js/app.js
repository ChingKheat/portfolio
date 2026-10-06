/**
 * User View Application Logic: Interactive Demo Arena, Device Simulators, and Project Showcase
 */

const App = {
  allProjects: [],
  filteredProjects: [],
  currentConfig: null,
  activeDemoProject: null,
  activeDeviceMode: 'mobile', // 'mobile' or 'desktop'

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

    // Arena Device Switcher
    document.getElementById('device-mobile-btn')?.addEventListener('click', () => this.setDeviceMode('mobile'));
    document.getElementById('device-desktop-btn')?.addEventListener('click', () => this.setDeviceMode('desktop'));

    // Arena Action Buttons
    document.getElementById('arena-reload-btn')?.addEventListener('click', () => this.reloadActiveDemo());
    document.getElementById('arena-fullscreen-btn')?.addEventListener('click', () => this.toggleArenaFullscreen());
    document.getElementById('arena-newtab-btn')?.addEventListener('click', () => {
      if (this.activeDemoProject && this.activeDemoProject.demoUrl) {
        window.open(this.activeDemoProject.demoUrl, '_blank', 'noopener');
      }
    });

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
      const username = this.currentConfig.settings.githubUsername || 'ChingKheat';

      // Update titles
      document.getElementById('page-title').textContent = this.currentConfig.settings.dashboardTitle || `${username}'s Project Demos`;
      document.getElementById('nav-brand-title').textContent = `${username} | Live Project Demos`;

      // Fetch GitHub data
      const [profile, ghRepos] = await Promise.all([
        GitHubAPI.getUserProfile(username).catch(() => ({
          login: username, name: username, bio: 'Developer & Creator', public_repos: 7
        })),
        GitHubAPI.getUserRepositories(username).catch(() => [])
      ]);

      this.renderProfile(profile, username);

      // Merge GitHub repos with our live demo configs
      const merged = ConfigManager.mergeReposWithConfig(ghRepos, this.currentConfig);
      this.allProjects = merged.filter(p => p.visible !== false);
      this.filteredProjects = [...this.allProjects];

      // Populate filter dropdowns
      this.populateFilterOptions();

      // Standby mode on initial load: only show screen when user selects a project!
      this.activeDemoProject = null;
      this.renderDemoArenaTabs();
      this.renderStandbyScreen();

      // Render cards
      this.renderProjectsGrid();

    } catch (err) {
      console.error('Initialization error:', err);
      this.showToast('Could not load repositories from GitHub API.', 'error');
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
    if (totalReposEl) totalReposEl.textContent = `${totalLiveDemos} Live Demos`;
  },

  /**
   * INTERACTIVE DEMO ARENA CONTROLS
   */
  renderDemoArenaTabs() {
    const container = document.getElementById('demo-selector-tabs');
    if (!container) return;

    // Show highlighted projects with demos or top pinned
    const showcaseProjects = this.allProjects.slice(0, 5);

    container.innerHTML = showcaseProjects.map(p => {
      const icon = p.demoType === 'mobile' ? '📱' : '💻';
      return `
        <button class="demo-tab-btn ${p === this.activeDemoProject ? 'active' : ''}" data-repo="${p.name}">
          <span>${icon}</span>
          <span>${p.customTitle.split(' - ')[0]}</span>
          ${p.hasLiveDemo ? '<span class="pulse-dot" style="margin-left:4px;"></span>' : ''}
        </button>
      `;
    }).join('');

    container.querySelectorAll('.demo-tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const repoName = e.currentTarget.getAttribute('data-repo');
        this.selectProjectByName(repoName);
      });
    });
  },

  selectProjectByName(repoName) {
    const project = this.allProjects.find(p => p.name === repoName);
    if (project) {
      this.loadDemoIntoArena(project);
    }
  },

  renderStandbyScreen() {
    this.activeDemoProject = null;
    document.querySelectorAll('.demo-tab-btn').forEach(btn => btn.classList.remove('active'));

    // Hide controls toolbar when no project is selected
    const controls = document.getElementById('arena-controls-bar');
    if (controls) controls.style.display = 'none';

    // Reset info footer
    document.getElementById('arena-project-title').textContent = 'Live Interactive Demo Arena';
    document.getElementById('arena-project-desc').textContent = 'Click any project tab above or "Play Demo" on a card below to launch the live screen.';

    const tagsContainer = document.getElementById('arena-project-tags');
    if (tagsContainer) tagsContainer.innerHTML = '';

    const githubLink = document.getElementById('arena-github-link');
    if (githubLink) githubLink.style.display = 'none';

    // Render Standby Card in the Stage
    const stage = document.getElementById('demo-viewport-stage');
    if (!stage) return;

    stage.innerHTML = `
      <div class="demo-standby-screen">
        <div class="standby-icon-badge">✨</div>
        <h3 style="font-size:1.5rem; font-weight:800; margin-bottom:0.6rem; color:var(--text-main);">
          Select a Project to Launch the Screen
        </h3>
        <p style="color:var(--text-muted); font-size:0.95rem; line-height:1.6; max-width:520px; margin-bottom:1.75rem;">
          Click any project tab above to open its live interactive simulator.
        </p>
        <div style="display:flex; flex-wrap:wrap; justify-content:center; gap:0.75rem;">
          <button class="btn-primary" onclick="App.selectProjectByName('banana-dashboard')">
            💻 Launch Banana Dashboard (Desktop)
          </button>
          <button class="btn-secondary" onclick="App.selectProjectByName('Malaysia-Travel-Apps')">
            📱 Launch Malaysia Travel App (Phone)
          </button>
        </div>
      </div>
    `;
  },

  loadDemoIntoArena(project, defaultMode = null) {
    this.activeDemoProject = project;

    // Reveal controls toolbar
    const controls = document.getElementById('arena-controls-bar');
    if (controls) controls.style.display = 'flex';

    // Reveal GitHub link
    const githubLink = document.getElementById('arena-github-link');
    if (githubLink) {
      githubLink.href = project.htmlUrl;
      githubLink.style.display = 'inline-flex';
    }

    // Set device mode
    if (defaultMode) {
      this.activeDeviceMode = defaultMode;
    } else if (project.demoType) {
      this.activeDeviceMode = project.demoType;
    }

    this.updateDeviceButtons();

    // Update active tab styling
    document.querySelectorAll('.demo-tab-btn').forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-repo') === project.name);
    });

    // Update arena info footer
    document.getElementById('arena-project-title').textContent = project.customTitle;
    document.getElementById('arena-project-desc').textContent = project.demoNote || project.customDescription;

    const tagsContainer = document.getElementById('arena-project-tags');
    if (tagsContainer) {
      tagsContainer.innerHTML = (project.tags || []).slice(0, 4).map(t => `<span class="tag-pill">${t}</span>`).join('');
    }

    const demoUrlPill = document.getElementById('arena-url-display');
    if (demoUrlPill) {
      demoUrlPill.textContent = project.demoUrl || `simulated://${project.name}.app`;
    }

    // Render simulator frame
    this.renderSimulatorFrame();

    // Smoothly scroll to arena if needed
    document.getElementById('demo-arena-section')?.scrollIntoView({ behavior: 'smooth' });
  },

  updateDeviceButtons() {
    document.getElementById('device-mobile-btn')?.classList.toggle('active', this.activeDeviceMode === 'mobile');
    document.getElementById('device-desktop-btn')?.classList.toggle('active', this.activeDeviceMode === 'desktop');
  },

  setDeviceMode(mode) {
    this.activeDeviceMode = mode;
    this.updateDeviceButtons();
    this.renderSimulatorFrame();
    this.showToast(`Switched to ${mode === 'desktop' ? 'Desktop View' : 'Phone View'}`, 'info');
  },

  renderSimulatorFrame() {
    const stage = document.getElementById('demo-viewport-stage');
    const project = this.activeDemoProject;
    if (!stage || !project) return;

    if (project.demoUrl) {
      // Live iframe preview
      if (this.activeDeviceMode === 'mobile') {
        stage.innerHTML = `
          <div class="phone-simulator-frame" id="simulator-frame">
            <div class="phone-notch"><span class="phone-camera-lens"></span></div>
            <div class="phone-screen">
              <iframe id="active-demo-iframe" src="${project.demoUrl}" title="${project.customTitle}" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope;" sandbox="allow-scripts allow-same-origin allow-forms allow-popups"></iframe>
            </div>
          </div>
        `;
      } else {
        stage.innerHTML = `
          <div class="desktop-simulator-frame" id="simulator-frame">
            <div class="desktop-browser-bar">
              <div class="browser-dots">
                <span class="dot-red"></span>
                <span class="dot-yellow"></span>
                <span class="dot-green"></span>
              </div>
              <div class="browser-url-pill">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                  <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                </svg>
                <span>${project.demoUrl}</span>
              </div>
            </div>
            <div class="desktop-screen">
              <iframe id="active-demo-iframe" src="${project.demoUrl}" title="${project.customTitle}" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope;" sandbox="allow-scripts allow-same-origin allow-forms allow-popups"></iframe>
            </div>
          </div>
        `;
      }
    } else {
      // Simulated preview card for projects without a live hosted URL
      stage.innerHTML = `
        <div class="desktop-simulator-frame" id="simulator-frame" style="max-width:750px; min-height:450px;">
          <div class="desktop-browser-bar">
            <div class="browser-dots">
              <span class="dot-red"></span>
              <span class="dot-yellow"></span>
              <span class="dot-green"></span>
            </div>
            <div class="browser-url-pill">
              <span>preview://${project.name}</span>
            </div>
          </div>
          <div class="simulator-mock-view">
            <div style="font-size:3rem; margin-bottom:1rem;">🚀</div>
            <h3 style="font-size:1.4rem; font-weight:700; margin-bottom:0.5rem;">${project.customTitle}</h3>
            <p style="color:var(--text-muted); max-width:500px; margin-bottom:1.5rem; line-height:1.6;">
              ${project.customDescription}
            </p>
            <div style="display:flex; gap:0.75rem;">
              <a href="${project.htmlUrl}" target="_blank" rel="noopener" class="btn-primary">
                View Source Code on GitHub &rarr;
              </a>
            </div>
          </div>
        </div>
      `;
    }
  },

  reloadActiveDemo() {
    const iframe = document.getElementById('active-demo-iframe');
    if (iframe && this.activeDemoProject && this.activeDemoProject.demoUrl) {
      iframe.src = this.activeDemoProject.demoUrl;
      this.showToast('Reloaded live demo session', 'info');
    }
  },

  toggleArenaFullscreen() {
    const stage = document.getElementById('simulator-frame');
    if (!stage) return;
    if (!document.fullscreenElement) {
      stage.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen().catch(() => {});
    }
  },

  /**
   * PROJECTS GRID (DEMO-FIRST CARDS)
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

    // Attach card action listeners
    container.querySelectorAll('.launch-demo-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const repoName = e.currentTarget.getAttribute('data-repo');
        const project = this.allProjects.find(p => p.name === repoName);
        if (project) {
          // Load directly into top Arena and scroll smoothly to it
          this.loadDemoIntoArena(project);
          document.getElementById('demo-arena-section')?.scrollIntoView({ behavior: 'smooth' });
          this.showToast(`Loaded "${project.customTitle}" into Live Arena!`, 'success');
        }
      });
    });

    container.querySelectorAll('.view-details-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const repoName = e.currentTarget.getAttribute('data-repo');
        this.openProjectModal(repoName);
      });
    });
  },

  createDemoCardHTML(project) {
    const liveIndicator = project.hasLiveDemo
      ? `<span class="live-pill banner-live-indicator"><span class="pulse-dot"></span> Live Demo Ready</span>`
      : '';

    const badgeHTML = project.badge
      ? `<span class="banner-overlay-badge">${project.badge}</span>`
      : '';

    const coverHTML = project.coverImage
      ? `<img src="${project.coverImage}" alt="${project.customTitle}" loading="lazy">`
      : `<div style="width:100%; height:100%; display:flex; align-items:center; justify-content:center; background:linear-gradient(135deg, rgba(56,139,253,0.15), rgba(188,140,255,0.15)); font-weight:700; color:var(--text-muted);">${project.language || 'Code'}</div>`;

    const tagsHTML = (project.tags || []).slice(0, 3).map(t => `<span class="tag-pill">${t}</span>`).join('');

    const primaryActionBtn = project.hasLiveDemo
      ? `<button class="btn-primary launch-demo-btn" data-repo="${project.name}">
           <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
           Play Demo
         </button>`
      : `<button class="btn-primary launch-demo-btn" data-repo="${project.name}" style="background:var(--bg-surface-elevated); color:var(--text-main); border:1px solid var(--border-color);">
           Interactive Preview
         </button>`;

    return `
      <div class="demo-card" data-repo="${project.name}">
        <div class="card-banner-wrapper">
          ${coverHTML}
          ${liveIndicator}
          ${badgeHTML}
        </div>
        <div class="card-body">
          <div class="card-title-row">
            <h3 class="card-title">${project.customTitle}</h3>
          </div>
          <p class="card-desc">${project.customDescription}</p>
          <div class="tags-row">${tagsHTML}</div>
          <div class="card-footer-actions">
            ${primaryActionBtn}
            <button class="btn-secondary view-details-btn" data-repo="${project.name}">
              Details &amp; Code
            </button>
          </div>
        </div>
      </div>
    `;
  },

  applyFilters() {
    const searchVal = document.getElementById('search-input')?.value.toLowerCase().trim() || '';
    const langVal = document.getElementById('language-filter')?.value || 'all';
    const demoOnly = document.getElementById('demo-filter')?.value === 'demo_only';

    this.filteredProjects = this.allProjects.filter(p => {
      const matchSearch = !searchVal ||
        p.customTitle.toLowerCase().includes(searchVal) ||
        p.name.toLowerCase().includes(searchVal) ||
        p.customDescription.toLowerCase().includes(searchVal) ||
        (p.tags && p.tags.some(t => t.toLowerCase().includes(searchVal)));

      const matchLang = langVal === 'all' || p.language === langVal;
      const matchDemo = !demoOnly || p.hasLiveDemo;

      return matchSearch && matchLang && matchDemo;
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
        demoBtn.onclick = () => {
          this.closeModal();
          this.loadDemoIntoArena(project);
          document.getElementById('demo-arena-section')?.scrollIntoView({ behavior: 'smooth' });
        };
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
  }
};

window.App = App;

document.addEventListener('DOMContentLoaded', () => App.init());
