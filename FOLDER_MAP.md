# 📂 Folder Guide: What is in this directory?

This folder (`GitHub Projects`) contains your **Personal Developer Portfolio Website** as well as your local standalone projects. Here is a clear breakdown of everything in this folder.

---

## 🌐 1. Portfolio & Showcase Dashboard (Main Website)

This is your public developer portfolio hosted on **GitHub Pages** ([portfolio](https://github.com/ChingKheat/portfolio)):

| File / Folder | What It Is & How to Use It |
| :--- | :--- |
| **`start-dashboard.bat`** | **👉 Double-click this anytime** to launch and preview your portfolio website on your computer! |
| **`index.html`** | Your public portfolio website (shows your projects, skills, and live demos to visitors). |
| **`admin.html`** | Your secret Admin Portal (log in with `admin123` to manage projects, edit descriptions, and toggle visibility). |
| **`demo.html`** | Interactive app simulator (runs mobile app phone frames and desktop previews). |
| **`projects-config.json`** | The database file storing your project titles, tags, demo links, and descriptions. |
| **`serve.py`** | The Python script that runs the local preview server when you click `start-dashboard.bat`. |
| **`demos/`** | Contains live runnable web applications: <br>• `demos/aureus-wealth/` (Luxury Wealth Management demo) <br>• `demos/geo_heritage/` (Flutter web mobile build) <br>• `demos/malaysia-internships/` (Malaysia IT Internship search tool) |
| **`css/` & `js/`** | Visual styling and JavaScript code that power your portfolio. |
| **`assets/`** | Cover photos, screenshots, and icons used on your portfolio. |
| **`scripts/`** | `sync-repos.py` script that automatically syncs newly created repositories from your GitHub account. |
| **`.github/`** | GitHub Actions workflows that automatically publish your website to GitHub Pages. |

---

## 🛠️ 2. Standalone Coding Projects (Kept locally)

These are independent projects stored here on your computer:

| Project Folder | Description |
| :--- | :--- |
| **`auto-clicker/`** | Python auto-clicker tool with a graphical interface. Double-click `run.bat` inside that folder to start it. |
| **`geo_heritage/`** | Full source code for your GeoHeritage Flutter mobile application (Assignment Edition). |
| **`geo_heritage_personal/`** | Full source code for your GeoHeritage Flutter mobile application (Personal Edition). |

---

## 💡 Quick Tips
- To test your portfolio website locally: Double-click **`start-dashboard.bat`**.
- To update your projects or hide/show a project: Go to **`admin.html`** in your browser.
- Git status is clean and ready. Standalone folders (`auto-clicker`, `geo_heritage`, etc.) are ignored by Git so they will not interfere with your portfolio website.
