"""
Gera relatórios de análise nos formatos Markdown e HTML.
"""

import html
import textwrap
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import AnalysisReport, GitHubProfile, JobListing, TechMatch


# ─── Tech match analysis ────────────────────────────────────────────────────

def compute_tech_matches(jobs: list[JobListing], profile: Optional[GitHubProfile]) -> tuple[list[TechMatch], float]:
    """Cross-reference job technologies against GitHub profile languages."""
    tech_counter: Counter[str] = Counter()
    for job in jobs:
        for tech in job.technologies:
            tech_counter[tech.lower()] += 1

    if not tech_counter:
        return [], 0.0

    profile_langs: dict[str, int] = {}
    if profile:
        profile_langs = {k.lower(): v for k, v in profile.top_languages.items()}

    matches: list[TechMatch] = []
    for tech, count in tech_counter.most_common():
        in_profile = tech in profile_langs
        matches.append(TechMatch(
            technology=tech.title(),
            job_count=count,
            in_github_profile=in_profile,
            github_usage_bytes=profile_langs.get(tech, 0),
        ))

    matched = sum(1 for m in matches if m.in_github_profile)
    score = round((matched / len(matches)) * 100, 1) if matches else 0.0
    return matches, score


def build_report(
    query: str,
    github_username: str,
    jobs: list[JobListing],
    profile: Optional[GitHubProfile],
) -> AnalysisReport:
    tech_matches, score = compute_tech_matches(jobs, profile)
    return AnalysisReport(
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        query=query,
        github_username=github_username,
        jobs=jobs,
        github_profile=profile,
        tech_matches=tech_matches,
        match_score=score,
    )


# ─── Markdown generator ──────────────────────────────────────────────────────

def _md_jobs_section(jobs: list[JobListing]) -> str:
    if not jobs:
        return "_Nenhuma vaga encontrada para esta busca._\n"

    lines: list[str] = []
    for i, job in enumerate(jobs, 1):
        techs = ", ".join(job.technologies) if job.technologies else "Não identificadas"
        salary = job.salary or "Não divulgado"
        posted = job.posted_at or "—"
        lines.append(
            f"### {i}. [{job.title}]({job.url})\n"
            f"**Empresa:** {job.company}  \n"
            f"**Local:** {job.location}  \n"
            f"**Salário:** {salary}  \n"
            f"**Publicado em:** {posted}  \n"
            f"**Tecnologias detectadas:** {techs}  \n"
        )
    return "\n".join(lines)


def _md_github_section(profile: Optional[GitHubProfile]) -> str:
    if not profile:
        return "_Perfil GitHub não carregado._\n"

    top_langs = ", ".join(
        f"{lang} ({bytes_:,} bytes)" for lang, bytes_ in list(profile.top_languages.items())[:8]
    ) or "Nenhuma"

    pinned = "\n".join(
        f"- **[{r.name}]({r.url})** — {r.description or 'Sem descrição'} "
        f"({'⭐ ' + str(r.stars) if r.stars else 'sem stars'})"
        for r in profile.pinned_repos
    ) or "_Sem repositórios públicos._"

    return textwrap.dedent(f"""\
        | Campo | Valor |
        |---|---|
        | Nome | {profile.name or profile.username} |
        | Bio | {profile.bio or "—"} |
        | Repos públicos | {profile.public_repos} |
        | Seguidores | {profile.followers} |
        | Total de stars | {profile.total_stars} |
        | Membro desde | {profile.member_since or "—"} |

        **Linguagens mais usadas:**
        {top_langs}

        **Repositórios em destaque:**
        {pinned}
    """)


def _md_match_section(matches: list[TechMatch], score: float) -> str:
    if not matches:
        return "_Não foi possível calcular o match — nenhuma tecnologia identificada nas vagas._\n"

    rows = "\n".join(
        f"| {m.technology} | {m.job_count} | {'✅' if m.in_github_profile else '❌'} |"
        for m in matches
    )
    return textwrap.dedent(f"""\
        **Match score: {score}%**

        | Tecnologia | Vagas que pedem | No seu GitHub? |
        |---|---|---|
        {rows}

        > ✅ = você já usa essa tecnologia  ❌ = oportunidade para aprender
    """)


def to_markdown(report: AnalysisReport) -> str:
    return textwrap.dedent(f"""\
        # Dev Job Analyzer — Relatório

        **Gerado em:** {report.generated_at}
        **Busca:** `{report.query}`
        **Perfil GitHub:** [{report.github_username}](https://github.com/{report.github_username})
        **Vagas encontradas:** {len(report.jobs)}

        ---

        ## 💼 Vagas Encontradas

        {_md_jobs_section(report.jobs)}

        ---

        ## 🐙 Análise do Perfil GitHub

        {_md_github_section(report.github_profile)}

        ---

        ## 🎯 Match: Vagas × Seu Perfil

        {_md_match_section(report.tech_matches, report.match_score)}

        ---

        *Relatório gerado por [Dev Job Analyzer](https://github.com)*
    """)


# ─── HTML generator ──────────────────────────────────────────────────────────

def _esc(value: Optional[str]) -> str:
    return html.escape(str(value or ""))


def _html_jobs(jobs: list[JobListing]) -> str:
    if not jobs:
        return "<p><em>Nenhuma vaga encontrada.</em></p>"
    cards = []
    for job in jobs:
        techs_html = "".join(
            f'<span class="tag">{_esc(t)}</span>' for t in job.technologies
        ) or '<span class="tag muted">Não identificadas</span>'
        cards.append(f"""
        <div class="card">
          <h3><a href="{_esc(job.url)}" target="_blank">{_esc(job.title)}</a></h3>
          <p><strong>Empresa:</strong> {_esc(job.company)} &nbsp;|&nbsp;
             <strong>Local:</strong> {_esc(job.location)} &nbsp;|&nbsp;
             <strong>Salário:</strong> {_esc(job.salary or 'Não divulgado')}</p>
          <p><strong>Publicado:</strong> {_esc(job.posted_at or '—')}</p>
          <p>{techs_html}</p>
        </div>""")
    return "\n".join(cards)


def _html_github(profile: Optional[GitHubProfile]) -> str:
    if not profile:
        return "<p><em>Perfil GitHub não carregado.</em></p>"

    lang_bars = ""
    total_bytes = sum(profile.top_languages.values()) or 1
    for lang, bytes_ in list(profile.top_languages.items())[:8]:
        pct = round((bytes_ / total_bytes) * 100, 1)
        lang_bars += f"""
        <div class="lang-row">
          <span class="lang-name">{_esc(lang)}</span>
          <div class="lang-bar-wrap"><div class="lang-bar" style="width:{pct}%"></div></div>
          <span class="lang-pct">{pct}%</span>
        </div>"""

    repos_html = ""
    for r in profile.pinned_repos:
        repos_html += f"""
        <div class="repo-card">
          <a href="{_esc(r.url)}" target="_blank"><strong>{_esc(r.name)}</strong></a>
          <p>{_esc(r.description or '—')}</p>
          <small>⭐ {r.stars} &nbsp; 🍴 {r.forks} &nbsp; {_esc(r.language or '')}</small>
        </div>"""

    return f"""
    <div class="gh-stats">
      <div class="stat-box"><span class="stat-num">{profile.public_repos}</span><br>Repositórios</div>
      <div class="stat-box"><span class="stat-num">{profile.followers}</span><br>Seguidores</div>
      <div class="stat-box"><span class="stat-num">{profile.total_stars}</span><br>Estrelas</div>
    </div>
    <p><strong>Bio:</strong> {_esc(profile.bio or '—')}</p>
    <p><strong>Membro desde:</strong> {_esc(profile.member_since or '—')}</p>
    <h4>Linguagens mais usadas</h4>{lang_bars}
    <h4>Repositórios em destaque</h4>
    <div class="repo-grid">{repos_html}</div>"""


def _html_match(matches: list[TechMatch], score: float) -> str:
    if not matches:
        return "<p><em>Sem dados de match.</em></p>"

    rows = "".join(
        f"""<tr>
          <td>{_esc(m.technology)}</td>
          <td class="center">{m.job_count}</td>
          <td class="center">{'<span class="yes">✅</span>' if m.in_github_profile else '<span class="no">❌</span>'}</td>
        </tr>"""
        for m in matches
    )
    color = "#22c55e" if score >= 60 else "#f59e0b" if score >= 30 else "#ef4444"
    return f"""
    <div class="score-box" style="border-color:{color}">
      <span class="score-num" style="color:{color}">{score}%</span>
      <span class="score-label">pontuação de compatibilidade</span>
    </div>
    <table>
      <thead><tr><th>Tecnologia</th><th>Vagas</th><th>No GitHub?</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
    <p class="legend">✅ você já usa &nbsp; ❌ oportunidade para aprender</p>"""


_HTML_STYLE = """
  :root { --bg:#0f172a; --surface:#1e293b; --border:#334155; --text:#e2e8f0; --muted:#94a3b8; --accent:#38bdf8; }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:var(--bg); color:var(--text); font-family:system-ui,sans-serif; padding:2rem; }
  h1 { color:var(--accent); margin-bottom:.25rem; }
  h2 { color:var(--accent); margin:2rem 0 1rem; border-bottom:1px solid var(--border); padding-bottom:.5rem; }
  h3 a { color:var(--text); text-decoration:none; } h3 a:hover { color:var(--accent); }
  .meta { color:var(--muted); margin-bottom:2rem; }
  .card { background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:1rem 1.25rem; margin-bottom:1rem; }
  .tag { display:inline-block; background:#0ea5e9; color:#fff; font-size:.75rem; padding:2px 8px; border-radius:999px; margin:2px; }
  .tag.muted { background:var(--border); }
  .gh-stats { display:flex; gap:1rem; margin-bottom:1rem; }
  .stat-box { background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:1rem 1.5rem; text-align:center; }
  .stat-num { font-size:1.75rem; font-weight:700; color:var(--accent); }
  .lang-row { display:flex; align-items:center; gap:.75rem; margin:.4rem 0; }
  .lang-name { width:110px; font-size:.85rem; }
  .lang-bar-wrap { flex:1; background:var(--border); border-radius:4px; height:8px; }
  .lang-bar { height:8px; background:var(--accent); border-radius:4px; }
  .lang-pct { width:40px; font-size:.8rem; color:var(--muted); text-align:right; }
  .repo-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(260px,1fr)); gap:1rem; margin-top:.5rem; }
  .repo-card { background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:.75rem 1rem; }
  .repo-card a { color:var(--accent); text-decoration:none; } .repo-card p { font-size:.85rem; color:var(--muted); margin:.25rem 0; }
  .score-box { border:3px solid; border-radius:12px; display:inline-flex; flex-direction:column; align-items:center; padding:.75rem 1.5rem; margin-bottom:1rem; }
  .score-num { font-size:2.5rem; font-weight:800; }
  .score-label { font-size:.8rem; color:var(--muted); }
  table { width:100%; border-collapse:collapse; margin-top:.5rem; }
  th, td { padding:.5rem .75rem; border:1px solid var(--border); }
  th { background:var(--surface); }
  .center { text-align:center; }
  .yes { color:#22c55e; } .no { color:#ef4444; }
  .legend { font-size:.8rem; color:var(--muted); margin-top:.5rem; }
  footer { margin-top:3rem; text-align:center; color:var(--muted); font-size:.8rem; }
"""


def to_html(report: AnalysisReport) -> str:
    gh_link = f"https://github.com/{_esc(report.github_username)}"
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Dev Job Analyzer — {_esc(report.query)}</title>
  <style>{_HTML_STYLE}</style>
</head>
<body>
  <h1>Dev Job Analyzer</h1>
  <p class="meta">
    Gerado em <strong>{_esc(report.generated_at)}</strong> &nbsp;·&nbsp;
    Busca: <code>{_esc(report.query)}</code> &nbsp;·&nbsp;
    GitHub: <a href="{gh_link}" target="_blank">{_esc(report.github_username)}</a> &nbsp;·&nbsp;
    {len(report.jobs)} vagas encontradas
  </p>

  <h2>💼 Vagas Encontradas</h2>
  {_html_jobs(report.jobs)}

  <h2>🐙 Perfil GitHub</h2>
  {_html_github(report.github_profile)}

  <h2>🎯 Match: Vagas × Seu Perfil</h2>
  {_html_match(report.tech_matches, report.match_score)}

  <footer>Gerado por Dev Job Analyzer · <a href="https://github.com" style="color:inherit">github.com</a></footer>
</body>
</html>"""


# ─── File writer ─────────────────────────────────────────────────────────────

def save_reports(report: AnalysisReport, output_stem: str) -> tuple[Path, Path]:
    """Write .md and .html files, returning both paths."""
    md_path = Path(f"{output_stem}.md")
    html_path = Path(f"{output_stem}.html")

    md_path.write_text(to_markdown(report), encoding="utf-8")
    html_path.write_text(to_html(report), encoding="utf-8")

    return md_path, html_path
