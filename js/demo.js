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
      const privateNotice = p.isPrivate
        ? `<div style="display:inline-flex; align-items:center; gap:6px; background:rgba(255,123,114,0.15); color:#ff7b72; border:1px solid rgba(255,123,114,0.3); border-radius:999px; padding:4px 14px; font-size:0.82rem; font-weight:700; margin-bottom:1rem;">
             <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
             Private Project (Personal Source Code)
           </div>`
        : '';

      const ghBtnText = p.isPrivate ? 'Open Private Repo on GitHub (Requires Login) &rarr;' : 'View Repository on GitHub &rarr;';

      container.innerHTML = `
        <div class="no-demo-message">
          <div style="font-size:3rem; margin-bottom:0.75rem;">${p.isPrivate ? '🔒' : '🚀'}</div>
          ${privateNotice}
          <h2 style="font-size:1.5rem; font-weight:700; margin-bottom:0.75rem;">${p.customTitle}</h2>
          <p style="color:var(--text-muted); line-height:1.6; margin-bottom:1.5rem;">
            ${p.customDescription}
          </p>
          <div style="display:flex; justify-content:center; gap:0.75rem; flex-wrap:wrap;">
            <a href="${p.htmlUrl}" target="_blank" rel="noopener" class="btn-primary">
              ${ghBtnText}
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
