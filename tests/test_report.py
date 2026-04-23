import pytest
from src.models import GitHubProfile, JobListing
from src.report_generator import compute_tech_matches


def _make_job(techs: list[str]) -> JobListing:
    return JobListing(
        title="Dev Júnior",
        company="XPTO",
        location="Remoto",
        url="https://example.com",
        technologies=techs,
    )


def _make_profile(languages: dict[str, int]) -> GitHubProfile:
    return GitHubProfile(
        username="testuser",
        name=None,
        bio=None,
        public_repos=10,
        followers=0,
        following=0,
        avatar_url="",
        profile_url="https://github.com/testuser",
        top_languages=languages,
    )


def test_perfect_match():
    jobs = [_make_job(["Python", "Django"])]
    profile = _make_profile({"Python": 10000, "Django": 5000})
    matches, score = compute_tech_matches(jobs, profile)
    assert score == 100.0
    assert all(m.in_github_profile for m in matches)


def test_no_match():
    jobs = [_make_job(["Docker", "Kubernetes"])]
    profile = _make_profile({"Python": 10000})
    matches, score = compute_tech_matches(jobs, profile)
    assert score == 0.0
    assert all(not m.in_github_profile for m in matches)


def test_partial_match():
    jobs = [_make_job(["Python", "Docker"])]
    profile = _make_profile({"Python": 10000})
    matches, score = compute_tech_matches(jobs, profile)
    assert score == 50.0


def test_empty_jobs_returns_zero():
    matches, score = compute_tech_matches([], _make_profile({"Python": 1000}))
    assert matches == []
    assert score == 0.0


def test_no_profile_all_unmatched():
    jobs = [_make_job(["Python", "React"])]
    matches, score = compute_tech_matches(jobs, None)
    assert score == 0.0
    assert all(not m.in_github_profile for m in matches)


def test_job_count_aggregates_across_jobs():
    jobs = [_make_job(["Python"]), _make_job(["Python", "Docker"])]
    profile = _make_profile({"Python": 5000})
    matches, _ = compute_tech_matches(jobs, profile)
    python_match = next(m for m in matches if m.technology.lower() == "python")
    assert python_match.job_count == 2


def test_match_is_case_insensitive():
    jobs = [_make_job(["Python"])]
    profile = _make_profile({"python": 5000})
    _, score = compute_tech_matches(jobs, profile)
    assert score == 100.0
