"""
Job scrapers for:
  - trampos.co      — internal JSON API (/api/v2/opportunities), no auth required
  - programathor.com.br — server-side HTML, parsed with BeautifulSoup
  - gupy.io         — public REST API (portal.api.gupy.io/api/v1/jobs), no auth required
"""

import re
import time
from typing import Callable, Optional

ProgressCallback = Callable[[str], None]

import requests
from bs4 import BeautifulSoup

from .models import JobListing

# ─── Shared tech extraction ──────────────────────────────────────────────────

# Ordered longest-first to avoid partial matches (e.g. "JS" inside "Node.js")
TECH_PATTERNS: list[str] = [
    "React Native", "Node\\.js", "Vue\\.js", "Next\\.js", "Nuxt\\.js",
    "TypeScript", "JavaScript", "Python", "Django", "FastAPI", "Flask",
    "Spring Boot", "Ruby on Rails", "React", "Angular", "Svelte",
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "SQLite",
    "Docker", "Kubernetes", "AWS", "GCP", "Azure",
    "GraphQL", "REST", "Kotlin", "Swift", "Flutter", "Dart",
    "Go", "Rust", "Java", "PHP", "Laravel", "Ruby", "Scala",
    "Machine Learning", "TensorFlow", "PyTorch", "Pandas", "NumPy",
    "Git", "Linux", "SQL", "CSS", "HTML",
]

_TECH_RE = re.compile(
    r"\b(" + "|".join(TECH_PATTERNS) + r")\b",
    re.IGNORECASE,
)
_CANONICAL = {p.lower().replace("\\.", "."): p for p in TECH_PATTERNS}


def _extract_technologies(text: str) -> list[str]:
    if not text:
        return []
    found = {m.group(0) for m in _TECH_RE.finditer(text)}
    return sorted({_CANONICAL.get(t.lower(), t) for t in found})


# ─── Shared HTTP helpers ─────────────────────────────────────────────────────

def _build_session(accept: str = "application/json") -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "DevJobAnalyzer/1.0 (portfolio project)",
        "Accept": accept,
    })
    return session


def _get(session: requests.Session, url: str, params: Optional[dict] = None, source: str = "") -> requests.Response:
    try:
        response = session.get(url, params=params, timeout=10)
    except requests.exceptions.ConnectionError:
        raise ConnectionError(f"Não foi possível conectar a {source or url}. Verifique sua conexão.")
    except requests.exceptions.Timeout:
        raise TimeoutError(f"{source or url} demorou muito para responder.")

    if response.status_code == 429:
        raise PermissionError(f"Limite de requisições atingido em {source}. Aguarde alguns minutos antes de tentar novamente.")
    if response.status_code >= 500:
        raise ConnectionError(f"Erro de servidor em {source} (HTTP {response.status_code}).")

    response.raise_for_status()
    return response


# ─── trampos.co ──────────────────────────────────────────────────────────────

_TRAMPOS_API = "https://trampos.co/api/v2"
_TRAMPOS_URL = "https://trampos.co/oportunidades"


def _trampos_detail(session: requests.Session, job_id: int) -> dict:
    resp = _get(session, f"{_TRAMPOS_API}/opportunities/{job_id}", source="trampos.co")
    data = resp.json()
    if isinstance(data, dict):
        return data.get("opportunity", data)
    return {}


def _trampos_parse(raw: dict, detail: dict) -> JobListing:
    text = " ".join([
        detail.get("description", "") or "",
        detail.get("prerequisite", "") or "",
        detail.get("desirable", "") or "",
        raw.get("name", "") or "",
    ])
    company = raw.get("company") or {}
    location_parts = [raw.get("city"), raw.get("state")]
    location = ", ".join(p for p in location_parts if p) or "Não informado"
    if raw.get("home_office"):
        location = "Remoto"
    elif raw.get("hybrid"):
        location = f"Híbrido — {location}"

    published = raw.get("published_at", "")
    return JobListing(
        title=raw.get("name", "Sem título"),
        company=company.get("name", "Empresa não informada"),
        location=location,
        url=f"{_TRAMPOS_URL}/{raw['id']}" if raw.get("id") else "",
        technologies=_extract_technologies(text),
        salary=raw.get("salary") or None,
        posted_at=published[:10] if published else None,
        source="trampos.co",
    )


def _normalize(text: str) -> str:
    """Lowercase and strip accents for fuzzy matching."""
    import unicodedata
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode().lower()


def _trampos_matches(raw: dict, detail: dict, query_lower: str) -> bool:
    searchable = _normalize(" ".join([
        raw.get("name", ""),
        raw.get("category_name", ""),
        detail.get("description", "") or "",
        detail.get("prerequisite", "") or "",
        detail.get("desirable", "") or "",
    ]))
    # Match ALL words individually so "python junior" matches "Python Júnior"
    return all(word in searchable for word in _normalize(query_lower).split())


def fetch_trampos(
    query: str,
    max_results: int = 30,
    on_progress: Optional[ProgressCallback] = None,
) -> list[JobListing]:
    """Fetch jobs from trampos.co via /api/v2/opportunities (no auth required)."""
    session = _build_session()
    query_lower = query.lower()
    listings: list[JobListing] = []
    page = 1

    while len(listings) < max_results:
        resp = _get(
            session,
            f"{_TRAMPOS_API}/opportunities",
            params={"q": query, "per_page": 20, "page": page, "category_slug": "ti"},
            source="trampos.co",
        )
        data = resp.json()
        if not isinstance(data, dict):
            break

        pagination = data.get("pagination", {})
        opportunities = data.get("opportunities", [])
        if not opportunities:
            break

        for i, raw in enumerate(opportunities, 1):
            if len(listings) >= max_results:
                break
            job_id = raw.get("id")
            if not job_id:
                continue
            checked = (page - 1) * 20 + i
            if on_progress:
                on_progress(f"trampos.co: {len(listings)} encontradas / {checked} verificadas...")
            try:
                detail = _trampos_detail(session, job_id)
                time.sleep(0.3)
            except Exception:
                detail = {}

            if not _trampos_matches(raw, detail, query_lower):
                continue
            listings.append(_trampos_parse(raw, detail))

        if page >= pagination.get("total_pages", 1):
            break
        page += 1

    return listings


# ─── programathor.com.br ─────────────────────────────────────────────────────

_PROGRAMATHOR_BASE = "https://programathor.com.br"

# Tags that are NOT technology skills — appear in the same <div> positions
_PROGRAMATHOR_NON_TECH = {
    "remoto", "híbrido", "presencial", "clt", "pj", "estágio", "estagio",
    "júnior", "junior", "pleno", "sênior", "senior", "vencida",
    "pequena/média empresa", "startup", "grande empresa", "médio porte",
}


def _programathor_parse_card(anchor: BeautifulSoup) -> Optional[JobListing]:
    href = anchor.get("href", "")
    if not href.startswith("/jobs/"):
        return None

    url = f"{_PROGRAMATHOR_BASE}{href}"
    h3 = anchor.find("h3")
    if not h3:
        return None

    # Title — strip "Vencida" prefix (expired jobs)
    title = h3.get_text(strip=True).removeprefix("Vencida").strip()

    # All direct-child divs in order: company, location, size, salary, level, contract, ...skills
    divs = [d.get_text(strip=True) for d in anchor.find_all("div", recursive=False)]

    company = divs[0] if len(divs) > 0 else "Empresa não informada"
    location = divs[1] if len(divs) > 1 else "Não informado"

    # Salary is the first div that starts with "R$" or "Até" or "A partir"
    salary: Optional[str] = None
    for d in divs:
        if d.startswith(("R$", "Até", "A partir", "De R$")):
            salary = d
            break

    # Skills = divs whose text is NOT a known non-tech label and not salary
    skill_divs = [
        d for d in divs
        if d.lower() not in _PROGRAMATHOR_NON_TECH
        and not d.startswith(("R$", "Até", "A partir", "De R$"))
        and d != company
        and d != location
        and len(d) > 1
    ]
    # Extract techs from skill tags (already structured) + title for coverage
    tech_text = " ".join(skill_divs) + " " + title
    technologies = _extract_technologies(tech_text)

    return JobListing(
        title=title,
        company=company,
        location=location,
        url=url,
        technologies=technologies,
        salary=salary,
        source="programathor.com.br",
    )


def fetch_programathor(
    query: str,
    max_results: int = 30,
    on_progress: Optional[ProgressCallback] = None,
) -> list[JobListing]:
    """
    Fetch jobs from programathor.com.br via server-side HTML + BeautifulSoup.
    Skills are already structured as tags — no detail-page requests needed.
    """
    session = _build_session(accept="text/html,application/xhtml+xml")

    # Build URL slug: "python junior" → "/jobs-python?expertise=Júnior"
    words = query.lower().split()
    level_map = {"junior": "Júnior", "júnior": "Júnior", "pleno": "Pleno", "senior": "Sênior", "sênior": "Sênior"}
    level: Optional[str] = None
    tech_words: list[str] = []
    for w in words:
        if w in level_map:
            level = level_map[w]
        else:
            tech_words.append(w)

    slug = "-".join(tech_words) if tech_words else "desenvolvedor"
    base_url = f"{_PROGRAMATHOR_BASE}/jobs-{slug}"
    params: dict = {}
    if level:
        params["expertise"] = level

    listings: list[JobListing] = []
    page = 1

    while len(listings) < max_results:
        params["page"] = page
        if on_progress:
            on_progress(f"programathor.com.br: página {page}...")
        resp = _get(session, base_url, params=params, source="programathor.com.br")
        soup = BeautifulSoup(resp.text, "lxml")

        # Job cards are <a href="/jobs/..."> anchors
        anchors = [
            a for a in soup.find_all("a", href=True)
            if str(a.get("href", "")).startswith("/jobs/") and a.find("h3")
        ]

        if not anchors:
            break

        for anchor in anchors:
            if len(listings) >= max_results:
                break
            job = _programathor_parse_card(anchor)
            if job:
                listings.append(job)

        # Pagination: look for a "próxima" or numbered link beyond current page
        next_link = soup.find("a", string=re.compile(r"(Próxima|próxima|›|»)", re.IGNORECASE))
        if not next_link:
            break
        page += 1
        time.sleep(0.4)

    return listings


# ─── gupy.io ─────────────────────────────────────────────────────────────────

_GUPY_API = "https://portal.api.gupy.io/api/v1/jobs"


def _gupy_parse(raw: dict) -> JobListing:
    description = raw.get("description", "") or ""
    title = raw.get("name", "Sem título")
    technologies = _extract_technologies(description + " " + title)

    workplace = raw.get("workplaceType", "")
    if raw.get("isRemoteWork") or workplace == "remote":
        location = "Remoto"
    elif workplace == "hybrid":
        city = raw.get("city") or ""
        location = f"Híbrido — {city}" if city else "Híbrido"
    else:
        parts = [raw.get("city"), raw.get("state")]
        location = ", ".join(p for p in parts if p) or "Não informado"

    published = raw.get("publishedDate", "")
    return JobListing(
        title=title,
        company=raw.get("careerPageName", "Empresa não informada"),
        location=location,
        url=raw.get("jobUrl", ""),
        technologies=technologies,
        posted_at=published[:10] if published else None,
        source="gupy.io",
    )


def fetch_gupy(
    query: str,
    max_results: int = 30,
    on_progress: Optional[ProgressCallback] = None,
) -> list[JobListing]:
    """Fetch jobs from gupy.io via public REST API (no auth required)."""
    session = _build_session()
    listings: list[JobListing] = []
    offset = 0
    limit = 20

    while len(listings) < max_results:
        if on_progress:
            on_progress(f"gupy.io: {len(listings)} vagas...")
        resp = _get(
            session,
            _GUPY_API,
            params={"jobName": query, "limit": limit, "offset": offset},
            source="gupy.io",
        )
        data = resp.json()
        jobs = data.get("data", [])
        pagination = data.get("pagination", {})

        if not jobs:
            break

        for raw in jobs:
            if len(listings) >= max_results:
                break
            listings.append(_gupy_parse(raw))

        total = pagination.get("total", 0)
        offset += limit
        if offset >= total:
            break
        time.sleep(0.2)

    return listings


# ─── Unified entrypoint ───────────────────────────────────────────────────────

SOURCES: dict[str, callable] = {
    "trampos": fetch_trampos,
    "programathor": fetch_programathor,
    "gupy": fetch_gupy,
}


def fetch_jobs(
    query: str,
    max_results: int = 30,
    sources: Optional[list[str]] = None,
) -> list[JobListing]:
    """
    Busca vagas de um ou mais serviços.

    Args:
        query: Consulta de busca (ex: "python junior")
        max_results: Máximo de resultados por serviço
        sources: Lista de serviços para consultar. Padrão: todos.
                 Valores válidos: "trampos", "programathor", "gupy"
    """
    active = sources if sources else list(SOURCES.keys())
    invalid = [s for s in active if s not in SOURCES]
    if invalid:
        raise ValueError(f"Serviço(s) desconhecido(s): {invalid}. Válidos: {list(SOURCES.keys())}")

    all_listings: list[JobListing] = []
    for source_name in active:
        try:
            results = SOURCES[source_name](query, max_results)
            all_listings.extend(results)
        except (ConnectionError, TimeoutError, PermissionError):
            raise
        except Exception as e:
            raise RuntimeError(f"Erro ao buscar de {source_name}: {e}") from e

    return all_listings
