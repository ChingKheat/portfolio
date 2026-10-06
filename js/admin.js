/**
 * Admin Portal Application Logic: Authentication, Project Management, and GitHub Cloud Sync
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
    // Auth form submit
    document.getElementById('login-form')?.addEventListener('submit', (e) => {
      e.preventDefault();
      const pin = document.getElementById('admin-pin-input')?.value;
      this.login(pin);
    });

    document.getElementById('logout-btn')?.addEventListener('click', () => this.logout());

    // Search and filters in admin table
    document.getElementById('admin-search')?.addEventListener('input', () => this.filterProjects());
    document.getElementById('admin-filter-status')?.addEventListener('change', () => this.filterProjects());

    // Actions
    document.getElementById('save-config-btn')?.addEventListener('click', () => this.saveChanges());
    document.getElementById('download-config-btn')?.addEventListener('click', () => this.downloadConfig());
    document.getElementById('refresh-github-btn')?.addEventListener('click', () => this.refreshGitHubData());
    document.getElementById('push-github-btn')?.addEventListener('click', () => this.pushToGitHubCloud());

    // Edit modal events
    document.getElementById('edit-modal-close')?.addEventListener('click', () => this.closeEditModal());
    document.getElementById('cancel-edit-btn')?.addEventListener('click', () => this.closeEditModal());
    document.getElementById('save-project-btn')?.addEventListener('click', () => this.saveProjectDetails());

    // GitHub Token show/hide toggle
    document.getElementById('toggle-token-visibility')?.addEventListener('click', () => {
      const input = document.getElementById('github-pat-input');
      if (input.type === 'password') {
        input.type = 'text';
      } else {
        input.type = 'password';
      }
    });

    // Save Settings form
    document.getElementById('save-settings-btn')?.addEventListener('click', () => this.saveGeneralSettings());
  },

  async loadAdminData() {
    try {
      this.config = await ConfigManager.loadConfig();
      const username = this.config.settings.githubUsername || 'ChingKheat';

      // Fill settings fields
      document.getElementById('settings-username').value = username;
      document.getElementById('settings-title').value = this.config.settings.dashboardTitle || '';
      document.getElementById('settings-subtitle').value = this.config.settings.dashboardSubtitle || '';
      document.getElementById('settings-pin').value = this.config.settings.adminPin || 'admin123';

      const savedPat = localStorage.getItem('gh_admin_pat') || '';
      document.getElementById('github-pat-input').value = savedPat;

      // Fetch Repositories
      this.allRepos = await GitHubAPI.getUserRepositories(username, false, this.config.settings.cacheTtlMinutes || 60);

      // Merge with config
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
    const pinnedCount = this.mergedProjects.filter(p => p.pinned).length;
    const hiddenCount = this.mergedProjects.filter(p => !p.visible).length;

    document.getElementById('stat-admin-total').textContent = totalCount;
    document.getElementById('stat-admin-pinned').textContent = pinnedCount;
    document.getElementById('stat-admin-hidden').textContent = hiddenCount;
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
      if (status === 'pinned') matchStatus = p.pinned === true;
      if (status === 'hidden') matchStatus = p.visible === false;
      if (status === 'visible') matchStatus = p.visible === true;

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
          <div style="font-weight: 600; color: var(--text-main);">${p.customTitle}</div>
          <div style="font-size: 0.8rem; color: var(--text-dim); font-family: var(--font-mono);">${p.name}</div>
        </td>
        <td>
          <span style="display:inline-flex; align-items:center; gap:5px; font-size:0.85rem;">
            <span class="lang-dot" style="background:${this.getLangColor(p.language)};"></span>
            ${p.language}
          </span>
        </td>
        <td>
          <label class="switch" title="Toggle visibility in public view">
            <input type="checkbox" class="toggle-visibility" data-repo="${p.name}" ${p.visible ? 'checked' : ''}>
            <span class="slider"></span>
          </label>
        </td>
        <td>
          <label class="switch" title="Toggle pinned/featured spotlight">
            <input type="checkbox" class="toggle-pinned" data-repo="${p.name}" ${p.pinned ? 'checked' : ''}>
            <span class="slider"></span>
          </label>
        </td>
        <td>
          <span style="font-size: 0.85rem; color: var(--text-muted);">
            ${p.tags && p.tags.length > 0 ? p.tags.slice(0, 2).join(', ') : 'None'}
            ${p.tags && p.tags.length > 2 ? ` +${p.tags.length - 2}` : ''}
          </span>
        </td>
        <td>
          <button class="btn-secondary edit-details-btn" data-repo="${p.name}" style="padding: 0.35rem 0.75rem; font-size: 0.82rem;">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
            </svg>
            Edit
          </button>
        </td>
      </tr>
    `).join('');

    // Attach listeners
    tbody.querySelectorAll('.toggle-visibility').forEach(input => {
      input.addEventListener('change', (e) => {
        const repo = e.target.getAttribute('data-repo');
        this.toggleVisibility(repo, e.target.checked);
      });
    });

    tbody.querySelectorAll('.toggle-pinned').forEach(input => {
      input.addEventListener('change', (e) => {
        const repo = e.target.getAttribute('data-repo');
        this.togglePinned(repo, e.target.checked);
      });
    });

    tbody.querySelectorAll('.edit-details-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const repo = e.currentTarget.getAttribute('data-repo');
        this.openEditModal(repo);
      });
    });
  },

  getLangColor(lang) {
    const colors = {
      'Dart': '#00B4AB', 'Flutter': '#02569B', 'Vue': '#41B883',
      'HTML': '#e34c26', 'CSS': '#563d7c', 'JavaScript': '#f1e05a',
      'TypeScript': '#3178c6', 'Python': '#3572A5', 'Java': '#b07219'
    };
    return colors[lang] || '#8b949e';
  },

  toggleVisibility(repoName, isVisible) {
    if (!this.config.projects[repoName]) this.config.projects[repoName] = {};
    this.config.projects[repoName].visible = isVisible;

    const proj = this.mergedProjects.find(p => p.name === repoName);
    if (proj) proj.visible = isVisible;

    this.updateStats();
    this.showToast(`Updated visibility for ${repoName}`, 'info');
  },

  togglePinned(repoName, isPinned) {
    if (!this.config.projects[repoName]) this.config.projects[repoName] = {};
    this.config.projects[repoName].pinned = isPinned;

    const proj = this.mergedProjects.find(p => p.name === repoName);
    if (proj) proj.pinned = isPinned;

    this.updateStats();
    this.showToast(`Updated pinned state for ${repoName}`, 'info');
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
    document.getElementById('edit-cover').value = project.coverImage || '';
    document.getElementById('edit-badge').value = project.badge || '';
    document.getElementById('edit-priority').value = project.priority || 10;

    const modal = document.getElementById('project-edit-modal');
    modal.classList.add('active');
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

    this.config.projects[name].customTitle = document.getElementById('edit-title').value.trim();
    this.config.projects[name].customDescription = document.getElementById('edit-desc').value.trim();
    this.config.projects[name].tags = tagsArray;
    this.config.projects[name].demoUrl = document.getElementById('edit-demo').value.trim();
    this.config.projects[name].coverImage = document.getElementById('edit-cover').value.trim();
    this.config.projects[name].badge = document.getElementById('edit-badge').value.trim();
    this.config.projects[name].priority = parseInt(document.getElementById('edit-priority').value, 10) || 10;

    // Refresh merged array
    this.mergedProjects = ConfigManager.mergeReposWithConfig(this.allRepos, this.config);
    this.filterProjects();
    this.closeEditModal();

    this.showToast(`Saved details for ${name}!`, 'success');
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
    const repo = prompt('Enter your GitHub repository name (e.g., your GitHub Pages repository name):');
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
    }, 3500);
  }
};

document.addEventListener('DOMContentLoaded', () => Admin.init());
