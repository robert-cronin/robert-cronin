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

    return {
        'formatted': f"{status_emoji} [{pr['title']}]({pr['html_url']}) - {formatted_date}<br>",
        'updated_at': updated_at,
        'state': pr['state']
    }


def add_updated_timestamp():
    now = datetime.now(timezone.utc)
    return f"*Last updated: {now.strftime('%Y-%m-%d %H:%M')} UTC*"


def update_readme(prs, gists):
    # Update PRs section
    pr_section = "## 🔄 Latest Pull Requests\n\n"
    pr_section += "🟢 Open | 🟣 Merged\n\n"
    for pr in prs:
        pr_section += pr['formatted'] + "\n"

    # Create gists section
    gist_section = "## 📜 Latest Gists\n\n"
    for gist in gists:
        formatted_gist = format_gist(gist)
        if formatted_gist:
            gist_section += formatted_gist + "\n"

    # Add updated timestamp
    updated_timestamp = add_updated_timestamp()

    with open('README.md', 'r') as file:
        content = file.read()

    # Update PRs
    content = re.sub(
        r'(<!-- START_SECTION:prs -->).*?(<!-- END_SECTION:prs -->)',
        f'\\1\n{pr_section}\n{updated_timestamp}\\2',
        content,
        flags=re.DOTALL
    )

    # Update Gists
    content = re.sub(
        r'(<!-- START_SECTION:gists -->).*?(<!-- END_SECTION:gists -->)',
        f'\\1\n{gist_section}\n{updated_timestamp}\\2',
        content,
        flags=re.DOTALL
    )

    with open('README.md', 'w') as file:
        file.write(content)


def get_latest_prs(username):
    headers = {
        'Accept': 'application/vnd.github.v3+json',
    }

    # Get open PRs
    open_url = f'https://api.github.com/search/issues?q=author:{
        username}+is:pr+is:public+is:open+sort:updated-desc&per_page=5'
    open_response = requests.get(open_url, headers=headers)
    open_response.raise_for_status()
    open_prs = open_response.json()['items']

    # Get merged PRs
    merged_url = f'https://api.github.com/search/issues?q=author:{
        username}+is:pr+is:public+is:merged+sort:updated-desc&per_page=10'
    merged_response = requests.get(merged_url, headers=headers)
    merged_response.raise_for_status()
    merged_prs = merged_response.json()['items']

    # Combine, format, and sort PRs
    all_prs = open_prs + merged_prs
    formatted_prs = [format_pr(pr) for pr in all_prs if format_pr(pr)]
    sorted_prs = sorted(
        formatted_prs, key=lambda x: x['updated_at'], reverse=True)

    # Ensure we have at most 5 open PRs and fill the rest with merged PRs
    open_prs = [pr for pr in sorted_prs if pr['state'] == 'open'][:5]
    merged_prs = [pr for pr in sorted_prs if pr['state'] != 'open']

    final_prs = open_prs + merged_prs[:10-len(open_prs)]
    return sorted(final_prs, key=lambda x: x['updated_at'], reverse=True)


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


if __name__ == "__main__":
    username = 'robert-cronin'
    latest_prs = get_latest_prs(username)
    latest_gists = get_latest_gists(username)
    update_readme(latest_prs, latest_gists)
