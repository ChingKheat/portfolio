#!/usr/bin/env python3
"""
Automated GitHub Repository Sync Script
Synchronizes GitHub repositories directly into projects-config.json.
Preserves existing manual customizations (customTitle, demoUrl, etc.) while auto-registering new repos.
"""

import os
import sys
import json
import urllib.request
import urllib.error

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'projects-config.json')

def load_config():
    if not os.path.exists(CONFIG_PATH):
        print(f"Error: {CONFIG_PATH} not found.")
        sys.exit(1)
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
        f.write('\n')

def fetch_repositories(username, token=None):
    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'Portfolio-Auto-Sync/1.0'
    }
    
    if token:
        headers['Authorization'] = f"token {token.strip()}"
        # When authenticated, use /user/repos to capture private repositories as well
        url = 'https://api.github.com/user/repos?per_page=100&sort=updated&affiliation=owner'
        print(f"Fetching authenticated repositories for user via {url}...")
    else:
        url = f'https://api.github.com/users/{username}/repos?per_page=100&sort=updated'
        print(f"Fetching public repositories for @{username} via {url}...")

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print(f"Retrieved {len(data)} repositories from GitHub API.")
            return data
    except urllib.error.HTTPError as e:
        print(f"GitHub API HTTP error {e.code}: {e.reason}")
        return []
    except Exception as e:
        print(f"Failed to fetch repositories: {e}")
        return []

def title_case_name(name):
    # Convert 'geo_heritage_personal' or 'banana-dashboard' to 'Geo Heritage Personal'
    clean = name.replace('-', ' ').replace('_', ' ')
    words = clean.split()
    return ' '.join(w.capitalize() if w.lower() not in ['and', 'for', 'of', 'the', 'in', 'on', 'ai'] else w.upper() if w.lower() == 'ai' else w.lower() for w in words)

def sync():
    config = load_config()
    settings = config.get('settings', {})
    username = settings.get('githubUsername', 'ChingKheat')
    
    token = os.environ.get('SYNC_PAT') or os.environ.get('GITHUB_TOKEN')
    repos = fetch_repositories(username, token)
    
    if not repos:
        print("No repositories returned or network unavailable. Exiting without modifying config.")
        return False

    existing_projects = config.get('projects', {})
    added_count = 0
    updated_count = 0

    for r in repos:
        name = r['name']
        is_private = r.get('private', False)
        homepage = r.get('homepage') or ''
        language = r.get('language') or 'Code'
        topics = r.get('topics') or []

        if name not in existing_projects:
            # Auto-register new project
            tags = topics if topics else ([language] if language else ['Software'])
            demo_type = 'mobile' if language.lower() in ['dart', 'flutter'] else 'desktop'
            has_demo = bool(homepage)
            badge = '🔒 Private Project' if is_private else ('Live Demo' if has_demo else '')

            existing_projects[name] = {
                'visible': True,
                'pinned': False,
                'priority': 50,
                'isPrivate': is_private,
                'customTitle': title_case_name(name),
                'customDescription': r.get('description') or f"Interactive {name} project.",
                'tags': tags,
                'demoUrl': homepage,
                'demoType': demo_type,
                'hasLiveDemo': has_demo,
                'coverImage': '',
                'badge': badge,
                'demoNote': ''
            }
            print(f"+ Added new project: {name} (isPrivate={is_private})")
            added_count += 1
        else:
            # Keep manual customizations, but update isPrivate if GitHub reports it
            proj = existing_projects[name]
            if proj.get('isPrivate') != is_private:
                proj['isPrivate'] = is_private
                if is_private and not proj.get('badge'):
                    proj['badge'] = '🔒 Private Project'
                updated_count += 1

    config['projects'] = existing_projects
    save_config(config)
    print(f"Auto-sync completed. Added {added_count} new projects, updated {updated_count}.")
    return True

if __name__ == '__main__':
    sync()
