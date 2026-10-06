/**
 * Configuration Manager: Manages projects-config.json, custom overrides, and merges with GitHub API data
 */

const ConfigManager = {
  storageKey: 'projects_config_custom',
  activeConfig: null,

  /**
   * Load base configuration from projects-config.json or localStorage overrides
   */
  async loadConfig() {
    // 1. Check local storage overrides first
    const custom = localStorage.getItem(this.storageKey);
    if (custom) {
      try {
        this.activeConfig = JSON.parse(custom);
        return this.activeConfig;
      } catch (e) {
        console.warn('Failed parsing local custom config, falling back to file:', e);
      }
    }

    // 2. Fetch projects-config.json from project root
    try {
      const res = await fetch('projects-config.json?v=' + Date.now());
      if (res.ok) {
        this.activeConfig = await res.json();
        return this.activeConfig;
      }
    } catch (e) {
      console.warn('Could not load projects-config.json from server:', e);
    }

    // 3. Fallback default
    this.activeConfig = {
      settings: {
        githubUsername: 'ChingKheat',
        dashboardTitle: "ChingKheat | Interactive Project Showcase & Live Demos",
        dashboardSubtitle: 'Test and explore live interactive web applications and mobile apps directly in your browser',
        adminPin: 'admin123',
        cacheTtlMinutes: 60
      },
      projects: {}
    };
    return this.activeConfig;
  },

  /**
   * Save active configuration to local storage
   */
  saveConfig(newConfig) {
    this.activeConfig = newConfig;
    localStorage.setItem(this.storageKey, JSON.stringify(newConfig));
  },

  /**
   * Merge GitHub API repository array with user configuration
   */
  mergeReposWithConfig(ghRepos, config) {
    const projectConfigs = (config && config.projects) ? config.projects : {};
    
    // Convert array of GH repos to merged objects
    const mergedList = ghRepos.map(repo => {
      const custom = projectConfigs[repo.name] || {};

      const isVisible = custom.visible !== undefined ? custom.visible : true;
      const isPinned = custom.pinned !== undefined ? custom.pinned : false;
      const priority = custom.priority !== undefined ? custom.priority : 99;
      
      const title = custom.customTitle || repo.name;
      const description = custom.customDescription || repo.description || 'No description provided.';
      const tags = (custom.tags && custom.tags.length > 0) 
        ? custom.tags 
        : (repo.topics && repo.topics.length > 0)
          ? repo.topics
          : (repo.language ? [repo.language] : ['Software']);

      const demoUrl = custom.demoUrl || repo.homepage || '';
      const hasLiveDemo = custom.hasLiveDemo !== undefined ? custom.hasLiveDemo : Boolean(demoUrl);
      const demoType = custom.demoType || (repo.language === 'Dart' ? 'mobile' : 'desktop');

      return {
        // GitHub raw fields
        id: repo.id,
        name: repo.name,
        fullName: repo.full_name,
        htmlUrl: repo.html_url,
        language: repo.language || 'Code',
        stars: repo.stargazers_count || 0,
        forks: repo.forks_count || 0,
        watchers: repo.watchers_count || 0,
        openIssues: repo.open_issues_count || 0,
        updatedAt: repo.updated_at,
        createdAt: repo.created_at,
        pushedAt: repo.pushed_at,
        defaultBranch: repo.default_branch || 'main',
        isFork: repo.fork,
        license: repo.license ? repo.license.spdx_id || repo.license.name : null,
        sizeKb: repo.size || 0,
        topics: repo.topics || [],

        // Custom config & Live Demo fields
        visible: isVisible,
        pinned: isPinned,
        priority: priority,
        customTitle: title,
        customDescription: description,
        tags: tags,
        demoUrl: demoUrl,
        hasLiveDemo: hasLiveDemo,
        demoType: demoType,
        demoNote: custom.demoNote || '',
        coverImage: custom.coverImage || '',
        badge: custom.badge || (hasLiveDemo ? 'Live Demo' : (isPinned ? 'Featured' : ''))
      };
    });

    // Also include any custom config projects that might not be in ghRepos yet
    Object.keys(projectConfigs).forEach(key => {
      const exists = mergedList.some(p => p.name === key);
      if (!exists) {
        const custom = projectConfigs[key];
        mergedList.push({
          id: key,
          name: key,
          fullName: `ChingKheat/${key}`,
          htmlUrl: `https://github.com/ChingKheat/${key}`,
          language: custom.tags && custom.tags[0] ? custom.tags[0] : 'App',
          stars: 0,
          forks: 0,
          watchers: 0,
          openIssues: 0,
          updatedAt: new Date().toISOString(),
          createdAt: new Date().toISOString(),
          defaultBranch: 'main',
          visible: custom.visible !== undefined ? custom.visible : true,
          pinned: custom.pinned !== undefined ? custom.pinned : false,
          priority: custom.priority || 99,
          customTitle: custom.customTitle || key,
          customDescription: custom.customDescription || '',
          tags: custom.tags || [],
          demoUrl: custom.demoUrl || '',
          hasLiveDemo: custom.hasLiveDemo || Boolean(custom.demoUrl),
          demoType: custom.demoType || 'desktop',
          demoNote: custom.demoNote || '',
          coverImage: custom.coverImage || '',
          badge: custom.badge || ''
        });
      }
    });

    // Sort by priority first, then updated date
    mergedList.sort((a, b) => {
      if (a.priority !== b.priority) {
        return a.priority - b.priority;
      }
      return new Date(b.updatedAt) - new Date(a.updatedAt);
    });

    return mergedList;
  },

  /**
   * Export config as downloadable JSON file
   */
  exportConfigAsJSON(config) {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(config, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', 'projects-config.json');
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  },

  /**
   * Reset local configuration back to original projects-config.json
   */
  resetToDefault() {
    localStorage.removeItem(this.storageKey);
  }
};
