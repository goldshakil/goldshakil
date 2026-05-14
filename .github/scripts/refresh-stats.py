#!/usr/bin/env python3
"""
Refresh the README's work-focused stats:
  - Contribution count for Dahab-Shakeel (last 365 days)
  - Language percentage breakdown across primary work repos

Updates the README in-place between marker comments. No-ops if nothing changed.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import requests

WORK_USER = "Dahab-Shakeel"
WORK_REPOS = ["sibelhealth/discovery-hub", "sibelhealth/tucana"]
README_PATH = Path("README.md")
MIN_PERCENT = 1  # drop languages under this share
TOP_N = 9        # cap how many language badges we show

# (color hex, simple-icons logo, logoColor) — extend as needed.
LANG_STYLE: dict[str, tuple[str, str, str]] = {
    "Python":     ("3776AB", "python",      "white"),
    "TypeScript": ("3178C6", "typescript",  "white"),
    "Java":       ("ED8B00", "openjdk",     "white"),
    "JavaScript": ("F7DF1E", "javascript",  "black"),
    "Shell":      ("4EAA25", "gnubash",     "white"),
    "Vue":        ("4FC08D", "vuedotjs",    "white"),
    "Gherkin":    ("5EBE3E", "cucumber",    "white"),
    "HCL":        ("844FBA", "terraform",   "white"),
    "Rust":       ("CE422B", "rust",        "white"),
    "Go":         ("00ADD8", "go",          "white"),
    "HTML":       ("E34F26", "html5",       "white"),
    "SCSS":       ("CC6699", "sass",        "white"),
    "CSS":        ("1572B6", "css3",        "white"),
    "C":          ("A8B9CC", "c",           "white"),
    "C++":        ("00599C", "cplusplus",   "white"),
    "Ruby":       ("CC342D", "ruby",        "white"),
    "Kotlin":     ("7F52FF", "kotlin",      "white"),
    "Swift":      ("F05138", "swift",       "white"),
    "Dockerfile": ("2496ED", "docker",      "white"),
    "Makefile":   ("6D6D6D", "gnumake",     "white"),
}


def gh_request(url: str, token: str, *, graphql: bool = False, body: dict | None = None):
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if graphql:
        resp = requests.post(url, json=body, headers=headers, timeout=30)
    else:
        resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_total_contributions(token: str) -> int:
    query = """
    query($user: String!) {
      user(login: $user) {
        contributionsCollection {
          contributionCalendar { totalContributions }
        }
      }
    }
    """
    data = gh_request(
        "https://api.github.com/graphql",
        token,
        graphql=True,
        body={"query": query, "variables": {"user": WORK_USER}},
    )
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]


def fetch_combined_languages(token: str) -> dict[str, int]:
    combined: dict[str, int] = {}
    for repo in WORK_REPOS:
        data = gh_request(f"https://api.github.com/repos/{repo}/languages", token)
        for lang, count in data.items():
            combined[lang] = combined.get(lang, 0) + count
    return combined


def lang_badge(language: str, percent: int) -> str:
    if language in LANG_STYLE:
        color, logo, logo_color = LANG_STYLE[language]
        return (
            f'<img src="https://img.shields.io/badge/{language}-{percent}%25-{color}'
            f'?style=for-the-badge&logo={logo}&logoColor={logo_color}" alt="{language} {percent}%" />'
        )
    return (
        f'<img src="https://img.shields.io/badge/{language}-{percent}%25-555555'
        f'?style=for-the-badge" alt="{language} {percent}%" />'
    )


def build_contribs_block(total: int) -> str:
    return (
        f'<img src="https://img.shields.io/badge/'
        f'Contributions%20to%20private%20Sibel%20repos%20(last%20year)-{total}-61dafb'
        f'?style=for-the-badge&logo=github&logoColor=white" alt="work contributions" />'
    )


def build_langs_block(language_bytes: dict[str, int]) -> str:
    total = sum(language_bytes.values())
    if total == 0:
        return "<sub>(no language data)</sub>"
    ranked = sorted(language_bytes.items(), key=lambda kv: -kv[1])[:TOP_N]
    pcts = [(lang, round(count / total * 100)) for lang, count in ranked]
    pcts = [(lang, pct) for lang, pct in pcts if pct >= MIN_PERCENT]
    lines: list[str] = []
    for i, (lang, pct) in enumerate(pcts):
        lines.append(lang_badge(lang, pct))
        if (i + 1) % 4 == 0 and (i + 1) < len(pcts):
            lines.append("<br/>")
    return "\n".join(lines)


def replace_block(text: str, start_marker: str, end_marker: str, new_inner: str) -> str:
    pattern = re.compile(
        f"({re.escape(start_marker)})(.*?)({re.escape(end_marker)})",
        re.DOTALL,
    )
    if not pattern.search(text):
        raise SystemExit(f"Markers not found in README: {start_marker} … {end_marker}")
    return pattern.sub(lambda m: f"{m.group(1)}\n{new_inner}\n{m.group(3)}", text)


def main() -> int:
    token = os.environ.get("DAHAB_PAT")
    if not token:
        print("ERROR: DAHAB_PAT env var not set", file=sys.stderr)
        return 1

    total = fetch_total_contributions(token)
    languages = fetch_combined_languages(token)

    readme = README_PATH.read_text()
    readme = replace_block(readme, "<!--START_CONTRIBS-->", "<!--END_CONTRIBS-->", build_contribs_block(total))
    readme = replace_block(readme, "<!--START_LANGS-->", "<!--END_LANGS-->", build_langs_block(languages))
    README_PATH.write_text(readme)

    pct_summary = ", ".join(
        f"{lang} {round(count / sum(languages.values()) * 100)}%"
        for lang, count in sorted(languages.items(), key=lambda kv: -kv[1])[:5]
    )
    print(f"Updated: {total} contributions · top langs: {pct_summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
