/**
 * Dedicated Project Demo Viewer (demo.html) Logic
 */

const DemoViewer = {
  project: null,
  isMobileFrame: true,

  async init() {
    const params = new URLSearchParams(window.location.search);
    const repoName = params.get('project') || params.get('repo');

    if (!repoName) {
      this.renderNotFound('No project specified in URL query.');
      return;
    }

    try {
      const config = await ConfigManager.loadConfig();
      const username = config.settings.githubUsername || 'ChingKheat';
      
      const repos = await GitHubAPI.getUserRepositories(username, false);
      const merged = ConfigManager.mergeReposWithConfig(repos, config);

      this.project = merged.find(p => p.name.toLowerCase() === repoName.toLowerCase());

      if (!this.project) {
        this.renderNotFound(`Project "${repoName}" was not found.`);
        return;
      }

      this.renderProjectDemo();
    } catch (e) {
      console.error('Error loading project for demo:', e);
      this.renderNotFound('Failed to load project details: ' + e.message);
    }
  },

  renderProjectDemo() {
    const p = this.project;
    document.title = `${p.customTitle} | Live Demo`;
    document.getElementById('nav-project-title').textContent = p.customTitle;

    // Badge
    const badgeEl = document.getElementById('nav-badge');
    if (badgeEl && p.badge) {
      badgeEl.textContent = p.badge;
      badgeEl.style.display = 'inline-block';
    }

    // Direct Link
    const directBtn = document.getElementById('open-direct-link');
    if (directBtn) {
      if (p.demoUrl) {
        directBtn.href = p.demoUrl;
        directBtn.style.display = 'inline-flex';
      } else {
        directBtn.style.display = 'none';
      }
    }

    // GitHub Link
    const githubBtn = document.getElementById('view-github-link');
    if (githubBtn) githubBtn.href = p.htmlUrl;

    // Viewport
    const container = document.getElementById('demo-viewport-container');
    if (!container) return;

    if (p.demoUrl) {
      const isMobileApp = p.demoType === 'mobile' || p.language === 'Dart';
      const toggleWrapper = document.getElementById('device-toggle-wrapper');

      if (isMobileApp && toggleWrapper) {
        toggleWrapper.style.display = 'inline-flex';
        this.isMobileFrame = true;
        this.bindDeviceToggle();
        this.renderIframe(true);
      } else {
        if (toggleWrapper) toggleWrapper.style.display = 'none';
        this.renderIframe(false);
      }
    } else {
      container.innerHTML = `
        <div class="no-demo-message">
          <div style="font-size:3rem; margin-bottom:1rem;">🚀</div>
          <h2 style="font-size:1.5rem; font-weight:700; margin-bottom:0.75rem;">${p.customTitle}</h2>
          <p style="color:var(--text-muted); line-height:1.6; margin-bottom:1.5rem;">
            ${p.customDescription}
          </p>
          <div style="display:flex; justify-content:center; gap:0.75rem;">
            <a href="${p.htmlUrl}" target="_blank" rel="noopener" class="btn-primary">
              View Repository on GitHub &rarr;
            </a>
            <a href="index.html" class="btn-secondary">
              &larr; Back to Projects
            </a>
          </div>
        </div>
      `;
    }
  },

  renderIframe(asMobile) {
    const container = document.getElementById('demo-viewport-container');
    const p = this.project;
    if (!container || !p || !p.demoUrl) return;

    if (asMobile) {
      container.innerHTML = `
        <div class="mobile-frame-container">
          <iframe class="demo-iframe" src="${p.demoUrl}" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope;" sandbox="allow-scripts allow-same-origin allow-forms allow-popups"></iframe>
        </div>
      `;
    } else {
      container.innerHTML = `
        <iframe class="demo-iframe" src="${p.demoUrl}" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope;" sandbox="allow-scripts allow-same-origin allow-forms allow-popups"></iframe>
      `;
    }
  },

  bindDeviceToggle() {
    const phoneBtn = document.getElementById('toggle-phone-btn');
    const fullBtn = document.getElementById('toggle-full-btn');

    phoneBtn?.addEventListener('click', () => {
      phoneBtn.classList.add('active');
      fullBtn.classList.remove('active');
      this.renderIframe(true);
    });

    fullBtn?.addEventListener('click', () => {
      fullBtn.classList.add('active');
      phoneBtn.classList.remove('active');
      this.renderIframe(false);
    });
  },

  renderNotFound(msg) {
    const container = document.getElementById('demo-viewport-container');
    if (!container) return;
    container.innerHTML = `
      <div class="no-demo-message">
        <h2 style="font-size:1.4rem; color:var(--accent-danger); margin-bottom:0.5rem;">Project Not Found</h2>
        <p style="color:var(--text-muted); margin-bottom:1.5rem;">${msg}</p>
        <a href="index.html" class="btn-primary">&larr; Return to Projects</a>
      </div>
    `;
  }
};

document.addEventListener('DOMContentLoaded', () => DemoViewer.init());
