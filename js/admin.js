/**
 * Admin Portal Application Logic: Authentication, Live Demo Management, and GitHub Cloud Sync
 */

const Admin = {
  config: null,
  allRepos: [],
  mergedProjects: [],
  filteredProjects: [],
  selectedProjectName: null,
  isAuthenticated: false,

  async init() {
    this.initTheme();
    this.bindEvents();
    this.checkAuth();
  },

  initTheme() {
    const savedTheme = localStorage.getItem('theme_preference') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
  },

  checkAuth() {
    const authSession = sessionStorage.getItem('admin_authenticated');
    if (authSession === 'true') {
      this.isAuthenticated = true;
      document.getElementById('auth-overlay').style.display = 'none';
      document.getElementById('admin-app').style.display = 'block';
      this.loadAdminData();
    } else {
      document.getElementById('auth-overlay').style.display = 'flex';
      document.getElementById('admin-app').style.display = 'none';
    }
  },

  login(pin) {
    const defaultPin = (this.config && this.config.settings && this.config.settings.adminPin) || 'admin123';
    if (pin === defaultPin || pin === 'admin123') {
      sessionStorage.setItem('admin_authenticated', 'true');
      this.isAuthenticated = true;
      document.getElementById('auth-overlay').style.display = 'none';
      document.getElementById('admin-app').style.display = 'block';
      this.showToast('Authentication successful!', 'success');
      this.loadAdminData();
    } else {
      this.showToast('Invalid passcode. Default is: admin123', 'error');
    }
  },

  logout() {
    sessionStorage.removeItem('admin_authenticated');
    this.isAuthenticated = false;
    window.location.reload();
  },

  bindEvents() {
    document.getElementById('login-form')?.addEventListener('submit', (e) => {
      e.preventDefault();
      const pin = document.getElementById('admin-pin-input')?.value;
      this.login(pin);
    });

    document.getElementById('logout-btn')?.addEventListener('click', () => this.logout());

    document.getElementById('admin-search')?.addEventListener('input', () => this.filterProjects());
    document.getElementById('admin-filter-status')?.addEventListener('change', () => this.filterProjects());

    document.getElementById('save-config-btn')?.addEventListener('click', () => this.saveChanges());
    document.getElementById('download-config-btn')?.addEventListener('click', () => this.downloadConfig());
    document.getElementById('add-project-btn')?.addEventListener('click', () => this.promptAddProject());
    document.getElementById('refresh-github-btn')?.addEventListener('click', () => this.refreshGitHubData());
    document.getElementById('push-github-btn')?.addEventListener('click', () => this.pushToGitHubCloud());

    document.getElementById('edit-modal-close')?.addEventListener('click', () => this.closeEditModal());
    document.getElementById('cancel-edit-btn')?.addEventListener('click', () => this.closeEditModal());
    document.getElementById('save-project-btn')?.addEventListener('click', () => this.saveProjectDetails());

    document.getElementById('toggle-token-visibility')?.addEventListener('click', () => {
      const input = document.getElementById('github-pat-input');
      input.type = input.type === 'password' ? 'text' : 'password';
    });

    document.getElementById('save-settings-btn')?.addEventListener('click', () => this.saveGeneralSettings());
  },

  async loadAdminData() {
    try {
      this.config = await ConfigManager.loadConfig();
      const username = this.config.settings.githubUsername || 'ChingKheat';

      document.getElementById('settings-username').value = username;
      document.getElementById('settings-title').value = this.config.settings.dashboardTitle || '';
      document.getElementById('settings-subtitle').value = this.config.settings.dashboardSubtitle || '';
      document.getElementById('settings-pin').value = this.config.settings.adminPin || 'admin123';

      const savedPat = localStorage.getItem('gh_admin_pat') || '';
      document.getElementById('github-pat-input').value = savedPat;

      this.allRepos = await GitHubAPI.getUserRepositories(username, false, this.config.settings.cacheTtlMinutes || 60);
      this.mergedProjects = ConfigManager.mergeReposWithConfig(this.allRepos, this.config);
      this.filteredProjects = [...this.mergedProjects];

      this.updateStats();
      this.renderTable();
      this.updateRateLimitDisplay();

    } catch (err) {
      console.error('Admin load error:', err);
      this.showToast('Failed to load GitHub repositories: ' + err.message, 'error');
    }
  },

  updateStats() {
    const totalCount = this.mergedProjects.length;
    const demoCount = this.mergedProjects.filter(p => p.hasLiveDemo).length;
    const hiddenCount = this.mergedProjects.filter(p => !p.visible).length;
    const privateCount = this.mergedProjects.filter(p => p.isPrivate).length;

    document.getElementById('stat-admin-total').textContent = totalCount;
    document.getElementById('stat-admin-pinned').textContent = demoCount;
    document.getElementById('stat-admin-hidden').textContent = hiddenCount;
    const privEl = document.getElementById('stat-admin-private');
    if (privEl) privEl.textContent = privateCount;
  },

  updateRateLimitDisplay() {
    const el = document.getElementById('stat-admin-ratelimit');
    if (!el) return;
    const rl = GitHubAPI.rateLimit;
    el.textContent = `${rl.remaining} / ${rl.limit}`;
  },

  filterProjects() {
    const search = document.getElementById('admin-search')?.value.toLowerCase().trim() || '';
    const status = document.getElementById('admin-filter-status')?.value || 'all';

    this.filteredProjects = this.mergedProjects.filter(p => {
      const matchSearch = !search ||
        p.name.toLowerCase().includes(search) ||
        p.customTitle.toLowerCase().includes(search) ||
        p.customDescription.toLowerCase().includes(search);

      let matchStatus = true;
      if (status === 'demos') matchStatus = p.hasLiveDemo === true;
      if (status === 'hidden') matchStatus = p.visible === false;
      if (status === 'visible') matchStatus = p.visible === true;
      if (status === 'private') matchStatus = p.isPrivate === true;

      return matchSearch && matchStatus;
    });

    this.renderTable();
  },

  renderTable() {
    const tbody = document.getElementById('projects-table-body');
    if (!tbody) return;

    if (this.filteredProjects.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2rem;">
            No repositories found matching current criteria.
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = this.filteredProjects.map(p => `
      <tr data-repo="${p.name}">
        <td>
          <div style="display:flex; align-items:center; gap:6px;">
            <span style="font-weight: 600; color: var(--text-main);">${p.customTitle}</span>
            ${p.isPrivate ? `<span style="font-size:0.7rem; padding:1px 6px; border-radius:999px; background:rgba(255,123,114,0.15); color:#ff7b72; border:1px solid rgba(255,123,114,0.3); font-weight:700;">🔒 Private</span>` : ''}
          </div>
          <div style="font-size: 0.8rem; color: var(--text-dim); font-family: var(--font-mono);">${p.name}</div>
        </td>
        <td>
          <span style="font-size: 0.85rem; color: var(--text-muted);">${p.language || 'Code'}</span>
        </td>
        <td>
          <label class="switch" title="Toggle visibility in public view">
            <input type="checkbox" class="toggle-visibility" data-repo="${p.name}" ${p.visible ? 'checked' : ''}>
            <span class="slider"></span>
          </label>
        </td>
        <td>
          ${p.hasLiveDemo 
            ? `<span class="live-pill"><span class="pulse-dot"></span> Live Ready</span>` 
            : `<span style="font-size:0.75rem; color:var(--text-dim);">No Demo URL</span>`}
        </td>
        <td>
          <span style="font-size: 0.82rem; font-weight:600; color:var(--text-muted);">
            ${p.demoType === 'mobile' ? '📱 Phone (390px)' : '💻 Desktop View'}
          </span>
        </td>
        <td>
          <button class="btn-secondary edit-details-btn" data-repo="${p.name}" style="padding: 0.35rem 0.75rem; font-size: 0.82rem;">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
            </svg>
            Edit Demo
          </button>
        </td>
      </tr>
    `).join('');

    tbody.querySelectorAll('.toggle-visibility').forEach(input => {
      input.addEventListener('change', (e) => {
        const repo = e.target.getAttribute('data-repo');
        this.toggleVisibility(repo, e.target.checked);
      });
    });

    tbody.querySelectorAll('.edit-details-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const repo = e.currentTarget.getAttribute('data-repo');
        this.openEditModal(repo);
      });
    });
  },

  toggleVisibility(repoName, isVisible) {
    if (!this.config.projects[repoName]) this.config.projects[repoName] = {};
    this.config.projects[repoName].visible = isVisible;

    const proj = this.mergedProjects.find(p => p.name === repoName);
    if (proj) proj.visible = isVisible;

    this.updateStats();
    this.showToast(`Updated visibility for ${repoName}`, 'info');
  },

  openEditModal(repoName) {
    const project = this.mergedProjects.find(p => p.name === repoName);
    if (!project) return;

    this.selectedProjectName = repoName;

    document.getElementById('edit-repo-name-label').textContent = project.name;
    document.getElementById('edit-title').value = project.customTitle || project.name;
    document.getElementById('edit-desc').value = project.customDescription || '';
    document.getElementById('edit-tags').value = (project.tags || []).join(', ');
    document.getElementById('edit-demo').value = project.demoUrl || '';
    document.getElementById('edit-demo-type').value = project.demoType || 'mobile';
    document.getElementById('edit-cover').value = project.coverImage || '';
    document.getElementById('edit-badge').value = project.badge || '';
    document.getElementById('edit-priority').value = project.priority || 10;
    document.getElementById('edit-is-private').checked = Boolean(project.isPrivate);

    const modal = document.getElementById('project-edit-modal');
    modal.classList.add('active');
  },

  promptAddProject() {
    const name = prompt('Enter the repository name (e.g. geo_heritage_personal):');
    if (!name || !name.trim()) return;
    const cleanName = name.trim();

    if (!this.config.projects[cleanName]) {
      this.config.projects[cleanName] = {
        visible: true,
        pinned: true,
        priority: 3,
        isPrivate: true,
        customTitle: cleanName,
        customDescription: 'Private project repository.',
        tags: ['App'],
        badge: '🔒 Private',
        hasLiveDemo: false
      };
    }

    this.mergedProjects = ConfigManager.mergeReposWithConfig(this.allRepos, this.config);
    this.filterProjects();
    this.updateStats();
    this.openEditModal(cleanName);
  },

  closeEditModal() {
    const modal = document.getElementById('project-edit-modal');
    modal.classList.remove('active');
    this.selectedProjectName = null;
  },

  saveProjectDetails() {
    if (!this.selectedProjectName) return;
    const name = this.selectedProjectName;

    if (!this.config.projects[name]) this.config.projects[name] = {};

    const rawTags = document.getElementById('edit-tags').value;
    const tagsArray = rawTags.split(',').map(t => t.trim()).filter(Boolean);
    const demoUrl = document.getElementById('edit-demo').value.trim();
    const demoType = document.getElementById('edit-demo-type').value;
    const isPrivate = document.getElementById('edit-is-private').checked;

    let badge = document.getElementById('edit-badge').value.trim();
    if (isPrivate && !badge) {
      badge = '🔒 Private';
    }

    this.config.projects[name].customTitle = document.getElementById('edit-title').value.trim();
    this.config.projects[name].customDescription = document.getElementById('edit-desc').value.trim();
    this.config.projects[name].tags = tagsArray;
    this.config.projects[name].demoUrl = demoUrl;
    this.config.projects[name].demoType = demoType;
    this.config.projects[name].hasLiveDemo = Boolean(demoUrl);
    this.config.projects[name].isPrivate = isPrivate;
    this.config.projects[name].coverImage = document.getElementById('edit-cover').value.trim();
    this.config.projects[name].badge = badge;
    this.config.projects[name].priority = parseInt(document.getElementById('edit-priority').value, 10) || 10;

    // Refresh merged array
    this.mergedProjects = ConfigManager.mergeReposWithConfig(this.allRepos, this.config);
    this.filterProjects();
    this.updateStats();
    this.closeEditModal();

    this.showToast(`Saved demo settings for ${name}!`, 'success');
  },

  saveGeneralSettings() {
    const username = document.getElementById('settings-username').value.trim();
    const title = document.getElementById('settings-title').value.trim();
    const subtitle = document.getElementById('settings-subtitle').value.trim();
    const pin = document.getElementById('settings-pin').value.trim();
    const pat = document.getElementById('github-pat-input').value.trim();

    this.config.settings.githubUsername = username || 'ChingKheat';
    this.config.settings.dashboardTitle = title;
    this.config.settings.dashboardSubtitle = subtitle;
    if (pin) this.config.settings.adminPin = pin;

    if (pat) {
      localStorage.setItem('gh_admin_pat', pat);
    } else {
      localStorage.removeItem('gh_admin_pat');
    }

    ConfigManager.saveConfig(this.config);
    this.showToast('Global settings updated and saved!', 'success');
  },

  saveChanges() {
    ConfigManager.saveConfig(this.config);
    this.showToast('All changes saved successfully to local storage!', 'success');
  },

  downloadConfig() {
    ConfigManager.exportConfigAsJSON(this.config);
    this.showToast('Downloaded projects-config.json. Keep it in your repository root!', 'success');
  },

  async refreshGitHubData() {
    const username = this.config.settings.githubUsername || 'ChingKheat';
    this.showToast('Refreshing data from GitHub API...', 'info');

    GitHubAPI.clearCache();
    try {
      this.allRepos = await GitHubAPI.getUserRepositories(username, true);
      this.mergedProjects = ConfigManager.mergeReposWithConfig(this.allRepos, this.config);
      this.filterProjects();
      this.updateStats();
      this.updateRateLimitDisplay();
      this.showToast('GitHub data refreshed successfully!', 'success');
    } catch (e) {
      this.showToast('Failed refreshing GitHub data: ' + e.message, 'error');
    }
  },

  async pushToGitHubCloud() {
    const username = this.config.settings.githubUsername || 'ChingKheat';
    const repo = prompt('Enter your repository name (e.g., portfolio):', 'portfolio');
    if (!repo) return;

    const pat = localStorage.getItem('gh_admin_pat');
    if (!pat) {
      alert('Please enter and save your GitHub Personal Access Token in the settings below first to enable cloud pushing.');
      return;
    }

    this.showToast('Pushing configuration directly to GitHub Cloud...', 'info');

    try {
      await GitHubAPI.commitConfigFileToGitHub(username, repo, this.config);
      this.showToast('Successfully committed configuration to GitHub Cloud!', 'success');
    } catch (err) {
      console.error('Push error:', err);
      this.showToast('GitHub Cloud push failed: ' + err.message, 'error');
    }
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

document.addEventListener('DOMContentLoaded', () => Admin.init());
