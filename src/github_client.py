import os
from typing import Optional

import requests

from .models import GitHubProfile, GitHubRepo

GITHUB_API_BASE = "https://api.github.com"


def _build_headers(token: Optional[str] = None) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    resolved_token = token or os.getenv("GITHUB_TOKEN")
    if resolved_token:
        headers["Authorization"] = f"Bearer {resolved_token}"
    return headers


def _get(url: str, headers: dict[str, str], params: Optional[dict] = None) -> dict | list:
    response = requests.get(url, headers=headers, params=params, timeout=10)
    if response.status_code == 404:
        raise ValueError(f"Recurso do GitHub não encontrado: {url}")
    if response.status_code == 403:
        raise PermissionError("Limite de requisições da API do GitHub atingido. Configure GITHUB_TOKEN no .env para aumentar o limite.")
    if response.status_code == 401:
        raise PermissionError("Token do GitHub inválido. Verifique seu GITHUB_TOKEN no .env.")
    response.raise_for_status()
    return response.json()


def _fetch_user(username: str, headers: dict[str, str]) -> dict:
    data = _get(f"{GITHUB_API_BASE}/users/{username}", headers)
    if not isinstance(data, dict):
        raise ValueError(f"Formato de resposta inesperado para o usuário '{username}'")
    return data


def _fetch_repos(username: str, headers: dict[str, str]) -> list[dict]:
    data = _get(
        f"{GITHUB_API_BASE}/users/{username}/repos",
        headers,
        params={"sort": "updated", "per_page": 30, "type": "owner"},
    )
    if not isinstance(data, list):
        return []
    return data


def _fetch_repo_languages(username: str, repo_name: str, headers: dict[str, str]) -> dict[str, int]:
    try:
        data = _get(f"{GITHUB_API_BASE}/repos/{username}/{repo_name}/languages", headers)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _aggregate_languages(repos: list[dict], username: str, headers: dict[str, str]) -> dict[str, int]:
    aggregated: dict[str, int] = {}
    # Limit to top 10 repos by stars to avoid excessive API calls
    sorted_repos = sorted(repos, key=lambda r: r.get("stargazers_count", 0), reverse=True)[:10]
    for repo in sorted_repos:
        langs = _fetch_repo_languages(username, repo["name"], headers)
        for lang, bytes_count in langs.items():
            aggregated[lang] = aggregated.get(lang, 0) + bytes_count
    return dict(sorted(aggregated.items(), key=lambda x: x[1], reverse=True))


def _parse_repo(repo: dict) -> GitHubRepo:
    return GitHubRepo(
        name=repo.get("name", ""),
        description=repo.get("description"),
        url=repo.get("html_url", ""),
        stars=repo.get("stargazers_count", 0),
        forks=repo.get("forks_count", 0),
        language=repo.get("language"),
        topics=repo.get("topics", []),
        updated_at=repo.get("updated_at", "")[:10] if repo.get("updated_at") else None,
    )


def fetch_github_profile(username: str, token: Optional[str] = None) -> GitHubProfile:
    """Fetch full GitHub profile including repos and aggregated language stats."""
    headers = _build_headers(token)

    user_data = _fetch_user(username, headers)
    repos_data = _fetch_repos(username, headers)

    repos = [_parse_repo(r) for r in repos_data if not r.get("fork", False)]
    recent_repos = sorted(repos, key=lambda r: r.updated_at or "", reverse=True)[:6]
    top_repos = sorted(repos, key=lambda r: r.stars, reverse=True)[:6]

    top_languages = _aggregate_languages(repos_data, username, headers)
    total_stars = sum(r.stars for r in repos)

    created_at = user_data.get("created_at", "")
    member_since = created_at[:7] if created_at else None  # "YYYY-MM"

    return GitHubProfile(
        username=username,
        name=user_data.get("name"),
        bio=user_data.get("bio"),
        public_repos=user_data.get("public_repos", 0),
        followers=user_data.get("followers", 0),
        following=user_data.get("following", 0),
        avatar_url=user_data.get("avatar_url", ""),
        profile_url=f"https://github.com/{username}",
        top_languages=top_languages,
        pinned_repos=top_repos,
        recent_repos=recent_repos,
        total_stars=total_stars,
        member_since=member_since,
    )
