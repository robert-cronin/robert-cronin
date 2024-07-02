# Copyright 2024 Robert Cronin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import re
import requests
from datetime import datetime, timezone


def format_pr(pr):
    # Format the date
    updated_at = datetime.strptime(
        pr['updated_at'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    formatted_date = updated_at.strftime("%Y-%m-%d")

    # Determine the status and corresponding emoji
    if pr['state'] == 'open':
        status_emoji = "🟢"
    elif pr.get('pull_request', {}).get('merged_at'):
        status_emoji = "🟣"  # Merged
    else:
        return None  # Skip closed but unmerged PRs

    return f"{status_emoji} [{pr['title']}]({pr['html_url']}) - {formatted_date}<br>"


def update_recent_prs(prs):
    pr_section = "## 🔄 Latest Pull Requests\n\n"
    pr_section += "🟢 Open | 🟣 Merged\n\n"
    for pr in prs:
        formatted_pr = format_pr(pr)
        if formatted_pr:
            pr_section += formatted_pr + "\n"

    with open('README.md', 'r') as file:
        content = file.read()

    new_content = re.sub(
        r'(<!-- START_SECTION:prs -->).*?(<!-- END_SECTION:prs -->)',
        f'\\1\n{pr_section}\\2',
        content,
        flags=re.DOTALL
    )

    with open('README.md', 'w') as file:
        file.write(new_content)


def get_latest_prs(username):
    headers = {
        'Accept': 'application/vnd.github.v3+json',
    }
    url = f'https://api.github.com/search/issues?q=author:{
        username}+is:pr+is:public+sort:updated-desc'
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    all_prs = response.json()['items']

    # Filter to include only open and merged PRs
    filtered_prs = [pr for pr in all_prs if pr['state'] ==
                    'open' or pr.get('pull_request', {}).get('merged_at')]
    return filtered_prs[:5]


def get_latest_gists(username):
    headers = {
        'Accept': 'application/vnd.github.v3+json',
    }
    url = f'https://api.github.com/users/{username}/gists'
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()[:5]


def format_gist(gist):
    created_at = datetime.strptime(
        gist['created_at'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    formatted_date = created_at.strftime("%Y-%m-%d")

    # Get the first file name as the gist title
    first_file = next(iter(gist['files'].values()))
    gist_title = first_file['filename']

    return f"📜 [{gist_title}]({gist['html_url']}) - {formatted_date}<br>"


def update_readme(prs, gists):
    # Update PRs section
    pr_section = "## 🔄 Latest Pull Requests\n\n"
    pr_section += "🟢 Open | 🟣 Merged\n\n"
    for pr in prs:
        formatted_pr = format_pr(pr)
        if formatted_pr:
            pr_section += formatted_pr + "\n"

    # Create gists section
    gist_section = "## 📜 Latest Gists\n\n"
    for gist in gists:
        formatted_gist = format_gist(gist)
        if formatted_gist:
            gist_section += formatted_gist + "\n"

    with open('README.md', 'r') as file:
        content = file.read()

    # Update PRs
    content = re.sub(
        r'(<!-- START_SECTION:prs -->).*?(<!-- END_SECTION:prs -->)',
        f'\\1\n{pr_section}\\2',
        content,
        flags=re.DOTALL
    )

    # Update Gists
    content = re.sub(
        r'(<!-- START_SECTION:gists -->).*?(<!-- END_SECTION:gists -->)',
        f'\\1\n{gist_section}\\2',
        content,
        flags=re.DOTALL
    )

    with open('README.md', 'w') as file:
        file.write(content)


if __name__ == "__main__":
    username = 'robert-cronin'
    latest_prs = get_latest_prs(username)
    latest_gists = get_latest_gists(username)
    update_readme(latest_prs, latest_gists)
