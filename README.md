# 🚀 GitHub Projects Showcase & Admin Dashboard

A modern, responsive, high-performance web dashboard to showcase your projects directly from GitHub. Features a public visitor portfolio view and a password-protected admin portal to manage showcase highlights, visibility, tags, demo links, and cloud synchronization.

Built to run **100% free on GitHub Cloud (GitHub Pages)** with zero backend server costs and direct GitHub REST API synchronization.

---

## ✨ Features

### 🌐 1. Public User View (`index.html`)
- **Real-Time GitHub Sync**: Automatically fetches your public repositories, star counts, forks, watchers, and commit updates from the GitHub REST API.
- **Featured / Spotlight Section**: Eye-catching cards for your best projects with cover banners, custom badges, live demo buttons, and GitHub source links.
- **Interactive Project Explorer**:
  - **Live Search**: Instant search by repository name, description keywords, or custom tags.
  - **Language Filter**: Filter by Dart, Vue, Java, HTML, etc.
  - **Tag & Category Filter**: Filter by tags (e.g., *Mobile*, *AI*, *Web*, *Travel*).
  - **Sorting**: Sort by Most Stars, Recently Updated, Alphabetical, or Repository Size.
  - **Layout Toggle**: Switch seamlessly between Grid View and Compact List View.
- **In-Depth Project Modal**:
  - Quick clone command with 1-click clipboard copy (`git clone https://...`).
  - **Live README.md Viewer**: Fetches and renders your repository's actual documentation using formatted Markdown.
  - Repository metrics (branch, open issues, stars, last updated date).
- **Tech Stack Analytics Bar**: Visual breakdown showing percentage of top programming languages used across your repositories.
- **Theme Switcher**: Dark Mode and Light Mode support with saved preferences.
- **Smart Client-side Caching**: Local caching with configurable TTL to load instantly and prevent hitting GitHub rate limits.

---

### 🛡️ 2. Admin Management Site (`admin.html`)
- **Passcode Protected**: Secure admin entry gate (Default passcode: `admin123`, customizable).
- **Project Visibility Controls**: One-click switch to show or hide specific repositories (e.g., hide test or unfinished repositories from public view).
- **Pin / Spotlight Toggle**: Toggle which repositories appear in the top hero spotlight.
- **Custom Metadata Editor**:
  - Custom display title & informative summary (perfect if your GitHub description is short or empty).
  - Custom category tags (e.g., `Flutter, Mobile, Booking System`).
  - Live Demo / Homepage URL.
  - Cover screenshot / banner URL.
  - Custom highlight badges (e.g., `Mobile`, `AI & Web`, `Featured`).
  - Priority ordering (control which projects appear first).
- **GitHub Cloud Integration**:
  - **Direct Push to GitHub Cloud**: Directly commit changes to `projects-config.json` in your GitHub repository using the GitHub Contents API when a Personal Access Token (PAT) is entered.
  - **Download JSON**: Export updated configuration with 1 click to save into your local repository.
  - **Rate Limit Monitor**: Live counter displaying remaining GitHub API requests and reset time.

---

## 📁 Project Architecture

```
GitHub Projects/
├── index.html                   # Public User View (Portfolio & Project Showcase)
├── admin.html                   # Admin Management Portal
├── projects-config.json         # Source-of-truth configuration & project overrides
├── serve.py                     # Local lightweight testing server (Python)
├── start-dashboard.bat          # 1-Click Windows launcher
├── css/
│   └── style.css                # Glassmorphic, modern responsive styles
├── js/
│   ├── github-api.js            # GitHub API client, cache & cloud commit helper
│   ├── config-manager.js        # Config loader, storage & repo merger
│   ├── app.js                   # Public user view logic & modal interactions
│   └── admin.js                 # Admin management & cloud push logic
└── .github/
    └── workflows/
        └── deploy.yml           # Automated GitHub Pages CI/CD workflow
```

---

## 🏃 Quick Start (Local Testing)

1. Double-click **`start-dashboard.bat`** (or run `python serve.py` in PowerShell).
2. The dashboard will automatically launch in your default browser at:
   - **Public View:** `http://localhost:8000/index.html`
   - **Admin Portal:** `http://localhost:8000/admin.html`
3. Enter `admin123` to log in to the Admin Portal.

---

## ☁️ Deploy to GitHub Cloud (GitHub Pages)

### Step 1: Initialize Git and Commit
Open PowerShell in this folder and run:
```powershell
git init
git add .
git commit -m "Initial commit of GitHub project dashboard"
```

### Step 2: Create a Repository on GitHub
1. Go to [github.com/new](https://github.com/new).
2. Name your repository (for example: `github-projects` or `portfolio`, or `<your-username>.github.io` for your root portfolio).
3. Set visibility to **Public** and leave initialization options unchecked.

### Step 3: Link and Push
```powershell
git remote add origin https://github.com/ChingKheat/<your-repo-name>.git
git branch -M main
git push -u origin main
```

### Step 4: Activate GitHub Pages
1. On your GitHub repository page, go to **Settings** &rarr; **Pages**.
2. Under **Build and deployment**:
   - **Option A (Automated)**: Select **Source: GitHub Actions**. The included `.github/workflows/deploy.yml` workflow will automatically deploy your site!
   - **Option B (Standard)**: Select **Source: Deploy from a branch**, choose `main` branch and `/ (root)` folder, then click **Save**.
3. Your dashboard is now live on GitHub Cloud at:
   `https://<your-username>.github.io/<your-repo-name>/`

---

## 🔐 Admin Passcode & GitHub Token Guide

- **Default Admin Passcode:** `admin123`
  - You can change this passcode in the **Settings & GitHub Cloud Credentials** section inside `admin.html`.
- **GitHub Personal Access Token (Optional):**
  - Unauthenticated requests to GitHub are limited to **60 requests/hour**.
  - If you generate a Personal Access Token with `public_repo` (or `repo`) scope at [github.com/settings/tokens](https://github.com/settings/tokens) and paste it into the admin settings:
    1. Your rate limit increases to **5,000 requests/hour**.
    2. You can use the **Push to GitHub Cloud** button to commit changes directly to your repository from the web browser!
