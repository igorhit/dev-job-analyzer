#!/usr/bin/env python3
"""
Dev Job Analyzer — ponto de entrada da CLI.

Uso:
    python main.py --jobs "python junior" --github igorhit --output report
"""

import argparse
import sys

from dotenv import load_dotenv

load_dotenv()

from src.github_client import fetch_github_profile
from src.report_generator import build_report, save_reports
from src.scraper import SOURCES, fetch_jobs

ALL_SOURCES = list(SOURCES.keys())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="dev-job-analyzer",
        description="Analisa vagas dev em múltiplos sites e faz match com seu perfil GitHub.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Fontes disponíveis: {", ".join(ALL_SOURCES)}

Exemplos:
  python main.py --jobs "python junior" --github seuusuario
  python main.py --jobs "react junior" --github seuusuario --sources trampos programathor
  python main.py --jobs "django" --github seuusuario --output relatorio --max-jobs 20
        """,
    )
    parser.add_argument(
        "--jobs", "-j",
        required=True,
        metavar="QUERY",
        help='Busca de vagas (ex: "python junior", "react frontend")',
    )
    parser.add_argument(
        "--github", "-g",
        required=True,
        metavar="USERNAME",
        help="Username do GitHub para análise (ex: igorhit)",
    )
    parser.add_argument(
        "--output", "-o",
        default="report",
        metavar="STEM",
        help="Nome base dos arquivos de saída sem extensão (padrão: report)",
    )
    parser.add_argument(
        "--max-jobs",
        type=int,
        default=20,
        metavar="N",
        help=f"Número máximo de vagas por fonte (padrão: 20)",
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        metavar="SOURCE",
        default=ALL_SOURCES,
        choices=ALL_SOURCES,
        help=f"Fontes a consultar (padrão: todas). Opções: {', '.join(ALL_SOURCES)}",
    )
    parser.add_argument(
        "--no-github",
        action="store_true",
        help="Pula a análise do GitHub (útil para testar o scraper isolado)",
    )
    return parser.parse_args()


def _step(msg: str) -> None:
    print(f"\n→ {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"  ✓ {msg}", flush=True)


def _warn(msg: str) -> None:
    print(f"  ⚠ {msg}", file=sys.stderr, flush=True)


def _fail(msg: str) -> None:
    print(f"\n✗ {msg}", file=sys.stderr, flush=True)


def main() -> None:
    args = parse_args()

    print("\n╔══════════════════════════════╗")
    print("║     Dev Job Analyzer  🔍     ║")
    print("╚══════════════════════════════╝")

    sources_label = ", ".join(args.sources)

    # ── 1. Scrape jobs ────────────────────────────────────────────────────────
    _step(f'Buscando vagas: "{args.jobs}" em [{sources_label}]...')
    jobs = []
    for source in args.sources:
        print(f"  • {source}: iniciando...", end="", flush=True)

        def _progress(msg: str, _src: str = source) -> None:
            print(f"\r  • {msg:<60}", end="", flush=True)

        try:
            results = SOURCES[source](args.jobs, args.max_jobs, on_progress=_progress)
            print(f"\r  ✓ {source}: {len(results)} vagas encontradas{'':<40}")
            jobs.extend(results)
        except (ConnectionError, TimeoutError) as e:
            print()
            _warn(f"{source}: {e}")
        except PermissionError as e:
            print()
            _warn(f"{source}: {e}")
        except Exception as e:
            print()
            _warn(f"{source}: erro inesperado — {e}")

    if not jobs:
        _warn("Nenhuma vaga encontrada em nenhuma fonte. Tente uma busca mais abrangente.")

    # ── 2. Fetch GitHub profile ───────────────────────────────────────────────
    profile = None
    if not args.no_github:
        _step(f"Analisando perfil GitHub: @{args.github}...")
        try:
            profile = fetch_github_profile(username=args.github)
            _ok(f"Perfil carregado — {profile.public_repos} repos, {len(profile.top_languages)} linguagens")
        except ValueError as e:
            _warn(f"Usuário GitHub não encontrado: {e}")
        except PermissionError as e:
            _warn(str(e))
        except Exception as e:
            _warn(f"Não foi possível carregar o GitHub: {e}")

    # ── 3. Build report ────────────────────────────────────────────────────────
    _step("Gerando relatório...")
    report = build_report(
        query=args.jobs,
        github_username=args.github,
        jobs=jobs,
        profile=profile,
    )

    # ── 4. Save files ──────────────────────────────────────────────────────────
    try:
        md_path, html_path = save_reports(report, args.output)
        _ok(f"Markdown: {md_path.resolve()}")
        _ok(f"HTML:     {html_path.resolve()}")
    except OSError as e:
        _fail(f"Erro ao salvar relatório: {e}")
        sys.exit(1)

    # ── 5. Summary ─────────────────────────────────────────────────────────────
    by_source = {}
    for job in jobs:
        by_source[job.source] = by_source.get(job.source, 0) + 1

    print("\n" + "─" * 44)
    print(f"  Vagas encontradas : {len(jobs)}")
    for src, count in by_source.items():
        print(f"    {src:<22}: {count}")
    if report.tech_matches:
        matched = sum(1 for m in report.tech_matches if m.in_github_profile)
        print(f"  Techs nas vagas   : {len(report.tech_matches)}")
        print(f"  Match com GitHub  : {matched}/{len(report.tech_matches)} ({report.match_score}%)")
    if profile:
        top3 = list(profile.top_languages.keys())[:3]
        print(f"  Top linguagens    : {', '.join(top3) or '—'}")
    print("─" * 44)
    print(f"\nAbra {html_path} no navegador para ver o relatório completo.\n")


if __name__ == "__main__":
    main()
