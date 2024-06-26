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


def get_latest_prs(username, token):
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json',
    }
    url = f'https://api.github.com/search/issues?q=author:{
        username}+is:pr+is:public+sort:updated-desc'
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()['items'][:5]


def update_readme(prs):
    with open('README.md', 'r') as file:
        content = file.read()

    pr_section = "## 🔄 Latest Pull Requests\n"
    for pr in prs:
        pr_section += f"- [{pr['title']}]({pr['html_url']})\n"

    new_content = re.sub(
        r'## 🔄 Latest Pull Requests\n<!-- START_SECTION:prs -->.*<!-- END_SECTION:prs -->',
        f"## 🔄 Latest Pull Requests\n<!-- START_SECTION:prs -->\n{
            pr_section}<!-- END_SECTION:prs -->",
        content,
        flags=re.DOTALL
    )

    with open('README.md', 'w') as file:
        file.write(new_content)


if __name__ == "__main__":
    github_token = os.environ['GITHUB_TOKEN']
    username = 'robert-cronin'
    latest_prs = get_latest_prs(username, github_token)
    update_readme(latest_prs)
