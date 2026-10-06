/**
 * GitHub API Client with Smart Caching, Rate Limit Tracking, and GitHub Cloud Commit
 */

const GitHubAPI = {
  // Store rate limit telemetry
  rateLimit: {
    limit: 60,
    remaining: 60,
    resetTime: null
  },

  /**
   * Helper to retrieve headers, attaching PAT if configured
   */
  getHeaders(customHeaders = {}) {
    const headers = {
      'Accept': 'application/vnd.github.v3+json',
      ...customHeaders
    };
    
    // Check if token is saved in localStorage
    const token = localStorage.getItem('gh_admin_pat');
    if (token) {
      headers['Authorization'] = `token ${token.trim()}`;
    }
    return headers;
  },

  /**
   * Update internal rate limit info from response headers
   */
  updateRateLimit(response) {
    const limit = response.headers.get('x-ratelimit-limit');
    const remaining = response.headers.get('x-ratelimit-remaining');
    const reset = response.headers.get('x-ratelimit-reset');

    if (limit) this.rateLimit.limit = parseInt(limit, 10);
    if (remaining) this.rateLimit.remaining = parseInt(remaining, 10);
    if (reset) this.rateLimit.resetTime = new Date(parseInt(reset, 10) * 1000);

    // Save rate limit to session
    sessionStorage.setItem('gh_rate_limit', JSON.stringify({
      limit: this.rateLimit.limit,
      remaining: this.rateLimit.remaining,
      resetTime: this.rateLimit.resetTime ? this.rateLimit.resetTime.toISOString() : null
    }));
  },

  /**
   * Get cached data with TTL check
   */
  getFromCache(key, ttlMinutes = 60) {
    try {
      const cached = localStorage.getItem(key);
      if (!cached) return null;

      const record = JSON.parse(cached);
      const now = Date.now();
      const expiresAt = record.timestamp + (ttlMinutes * 60 * 1000);

      if (now > expiresAt) {
        localStorage.removeItem(key);
        return null;
      }
      return record.data;
    } catch (e) {
      console.warn('Error reading from cache:', e);
      return null;
    }
  },

  /**
   * Save data to cache with timestamp
   */
  saveToCache(key, data) {
    try {
      localStorage.setItem(key, JSON.stringify({
        timestamp: Date.now(),
        data: data
      }));
    } catch (e) {
      console.warn('Error saving to cache:', e);
    }
  },

  /**
   * Fetch User Profile
   */
  async getUserProfile(username, forceRefresh = false, ttlMinutes = 60) {
    const cacheKey = `gh_cache_profile_${username}`;
    if (!forceRefresh) {
      const cached = this.getFromCache(cacheKey, ttlMinutes);
      if (cached) return cached;
    }

    try {
      const res = await fetch(`https://api.github.com/users/${encodeURIComponent(username)}`, {
        headers: this.getHeaders()
      });
      this.updateRateLimit(res);

      if (!res.ok) {
        throw new Error(`GitHub Profile API returned ${res.status}: ${res.statusText}`);
      }

      const data = await res.json();
      this.saveToCache(cacheKey, data);
      return data;
    } catch (err) {
      console.error('Fetch profile failed:', err);
      // Fallback to expired cache if available
      const fallback = localStorage.getItem(cacheKey);
      if (fallback) {
        return JSON.parse(fallback).data;
      }
      throw err;
    }
  },

  /**
   * Fetch Repositories for a user
   */
  async getUserRepositories(username, forceRefresh = false, ttlMinutes = 60) {
    const cacheKey = `gh_cache_repos_${username}`;
    if (!forceRefresh) {
      const cached = this.getFromCache(cacheKey, ttlMinutes);
      if (cached) return cached;
    }

      // If a token is provided, fetch both public and private repos using /user/repos
      const token = localStorage.getItem('gh_admin_pat');
      const apiUrl = token 
        ? `https://api.github.com/user/repos?per_page=100&sort=updated&affiliation=owner,collaborator`
        : `https://api.github.com/users/${encodeURIComponent(username)}/repos?per_page=100&sort=updated`;

      const res = await fetch(apiUrl, {
        headers: this.getHeaders()
      });
      this.updateRateLimit(res);

      if (!res.ok) {
        throw new Error(`GitHub Repos API returned ${res.status}: ${res.statusText}`);
      }

      const repos = await res.json();
      this.saveToCache(cacheKey, repos);
      return repos;
    } catch (err) {
      console.error('Fetch repos failed:', err);
      const fallback = localStorage.getItem(cacheKey);
      if (fallback) {
        return JSON.parse(fallback).data;
      }
      throw err;
    }
  },

  /**
   * Fetch README raw content for a repository
   */
  async getRepoReadme(owner, repo) {
    const cacheKey = `gh_cache_readme_${owner}_${repo}`;
    const cached = this.getFromCache(cacheKey, 120);
    if (cached) return cached;

    try {
      const res = await fetch(`https://api.github.com/repos/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/readme`, {
        headers: this.getHeaders({
          'Accept': 'application/vnd.github.raw+json'
        })
      });
      this.updateRateLimit(res);

      if (!res.ok) {
        return null;
      }

      const readmeText = await res.text();
      this.saveToCache(cacheKey, readmeText);
      return readmeText;
    } catch (err) {
      console.warn(`README not found or failed for ${repo}:`, err);
      return null;
    }
  },

  /**
   * Commit updated projects-config.json directly to GitHub Repository (GitHub Cloud integration)
   * Requires GitHub Personal Access Token with 'repo' scope.
   */
  async commitConfigFileToGitHub(owner, repo, newConfigObject, commitMessage = 'Update project showcase configuration') {
    const token = localStorage.getItem('gh_admin_pat');
    if (!token) {
      throw new Error('A GitHub Personal Access Token (PAT) is required to push changes directly to GitHub.');
    }

    const path = 'projects-config.json';
    const apiUrl = `https://api.github.com/repos/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/contents/${path}`;

    // 1. Get current file sha
    let currentSha = null;
    try {
      const getRes = await fetch(apiUrl, {
        headers: this.getHeaders()
      });
      if (getRes.ok) {
        const fileInfo = await getRes.json();
        currentSha = fileInfo.sha;
      }
    } catch (e) {
      console.log('File does not exist yet or error checking sha, creating new file.');
    }

    // 2. Prepare payload
    const contentString = JSON.stringify(newConfigObject, null, 2);
    // Base64 encode for GitHub API (UTF-8 safe)
    const encodedContent = btoa(unescape(encodeURIComponent(contentString)));

    const body = {
      message: commitMessage,
      content: encodedContent
    };
    if (currentSha) {
      body.sha = currentSha;
    }

    const putRes = await fetch(apiUrl, {
      method: 'PUT',
      headers: this.getHeaders({
        'Content-Type': 'application/json'
      }),
      body: JSON.stringify(body)
    });
    this.updateRateLimit(putRes);

    if (!putRes.ok) {
      const errJson = await putRes.json().catch(() => ({}));
      throw new Error(`Failed to commit to GitHub (${putRes.status}): ${errJson.message || putRes.statusText}`);
    }

    return await putRes.json();
  },

  /**
   * Clear all GitHub API local storage caches
   */
  clearCache() {
    const keysToRemove = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith('gh_cache_')) {
        keysToRemove.push(key);
      }
    }
    keysToRemove.forEach(k => localStorage.removeItem(k));
  }
};
