from dataclasses import dataclass, field
from typing import Optional


@dataclass
class JobListing:
    title: str
    company: str
    location: str
    url: str
    technologies: list[str] = field(default_factory=list)
    level: Optional[str] = None
    salary: Optional[str] = None
    posted_at: Optional[str] = None
    source: str = "trampos.co"


@dataclass
class GitHubRepo:
    name: str
    description: Optional[str]
    url: str
    stars: int
    forks: int
    language: Optional[str]
    topics: list[str] = field(default_factory=list)
    updated_at: Optional[str] = None


@dataclass
class GitHubProfile:
    username: str
    name: Optional[str]
    bio: Optional[str]
    public_repos: int
    followers: int
    following: int
    avatar_url: str
    profile_url: str
    top_languages: dict[str, int] = field(default_factory=dict)
    pinned_repos: list[GitHubRepo] = field(default_factory=list)
    recent_repos: list[GitHubRepo] = field(default_factory=list)
    total_stars: int = 0
    member_since: Optional[str] = None


@dataclass
class TechMatch:
    technology: str
    job_count: int
    in_github_profile: bool
    github_usage_bytes: int = 0


@dataclass
class AnalysisReport:
    generated_at: str
    query: str
    github_username: str
    jobs: list[JobListing] = field(default_factory=list)
    github_profile: Optional[GitHubProfile] = None
    tech_matches: list[TechMatch] = field(default_factory=list)
    match_score: float = 0.0
