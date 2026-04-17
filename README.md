# Dev Job Analyzer

Um CLI Python que combina **scraping de vagas dev** em múltiplos sites brasileiros com **análise de perfil GitHub** para gerar um relatório consolidado de match entre o que o mercado pede e o que você já sabe.

Construído como projeto de portfólio para demonstrar automação de dados, consumo de APIs REST, scraping HTML e geração de relatórios em Python.

---

## O que o projeto faz

1. **Busca vagas** em 3 fontes simultaneamente:
   - **[trampos.co](https://trampos.co)** — via endpoint JSON interno `/api/v2/opportunities` (sem auth)
   - **[programathor.com.br](https://programathor.com.br)** — via scraping HTML com BeautifulSoup (skills já estruturadas como tags)
   - **[gupy.io](https://gupy.io)** — via API REST pública `portal.api.gupy.io/api/v1/jobs` (sem auth)
2. **Extrai tecnologias** de cada vaga (título, descrição, requisitos) via regex sobre uma lista de +40 tecnologias conhecidas.
3. **Analisa seu perfil GitHub** via API REST pública: linguagens mais usadas, repositórios em destaque, stats gerais.
4. **Calcula um match score** entre as tecnologias mais pedidas nas vagas e as que aparecem no seu GitHub.
5. **Gera um relatório** em `.md` e `.html` — o HTML tem dark mode, barras de progresso por linguagem e cards de vagas.

---

## Exemplo de uso

```bash
python main.py --jobs "python junior" --github igorhit --output report
```

### Output no terminal

```text
╔══════════════════════════════╗
║     Dev Job Analyzer  🔍     ║
╚══════════════════════════════╝

→ Buscando vagas: "python junior" em [trampos, programathor, gupy]...
  ✓ trampos: 12 vagas
  ✓ programathor: 8 vagas
  ✓ gupy: 5 vagas

→ Analisando perfil GitHub: @igorhit...
  ✓ Perfil carregado — 24 repos, 6 linguagens

→ Gerando relatório...
  ✓ Markdown: /path/to/report.md
  ✓ HTML:     /path/to/report.html

────────────────────────────────────────────
  Vagas encontradas : 25
    trampos.co            : 12
    programathor.com.br   : 8
    gupy.io               : 5
  Techs nas vagas   : 12
  Match com GitHub  : 7/12 (58.3%)
  Top linguagens    : Python, JavaScript, HTML
────────────────────────────────────────────

Abra report.html no navegador para ver o relatório completo.
```

### Exemplo de relatório gerado (Markdown)

```markdown
# Dev Job Analyzer — Relatório

**Gerado em:** 2026-04-17 14:32
**Busca:** `python junior`
**Perfil GitHub:** @igorhit
**Vagas encontradas:** 18

## 💼 Vagas Encontradas

### 1. [Desenvolvedor(a) Python Júnior](https://trampos.co/oportunidades/123)
**Empresa:** Fintech XPTO
**Local:** Remoto
**Salário:** R$ 3.000 a R$ 4.500
**Tecnologias detectadas:** Python, Django, PostgreSQL, Git

## 🎯 Match: Vagas × Seu Perfil

**Match score: 58.3%**

| Tecnologia | Vagas que pedem | No seu GitHub? |
|---|---|---|
| Python | 15 | ✅ |
| Django | 9 | ✅ |
| Docker | 7 | ❌ |
| PostgreSQL | 6 | ✅ |
```

---

## Instalação

### Pré-requisitos

- Python 3.10+
- pip

### Passos

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/dev-job-analyzer.git
cd dev-job-analyzer

# 2. (Opcional) Crie um ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure o token do GitHub (opcional, mas recomendado. caso não saiba como, instruções mais abaixo)
cp .env.example .env
# Edite .env e adicione seu GITHUB_TOKEN
```

---

## Uso

```bash
# Busca em todas as fontes (padrão)
python main.py --jobs "python junior" --github seu-usuario

# Só fontes específicas
python main.py --jobs "react junior" --github seu-usuario --sources trampos programathor

# Com output personalizado e mais vagas por fonte
python main.py --jobs "react frontend" --github seu-usuario --output meu-relatorio --max-jobs 20

# Só vagas, sem análise do GitHub
python main.py --jobs "node.js junior" --github qualquer --no-github
```

### Parâmetros

| Parâmetro | Obrigatório | Descrição |
| --- | --- | --- |
| `--jobs` / `-j` | ✅ | Query de busca das vagas |
| `--github` / `-g` | ✅ | Username do GitHub |
| `--output` / `-o` | ❌ | Nome base dos arquivos de saída (padrão: `report`) |
| `--max-jobs` | ❌ | Máximo de vagas **por fonte** (padrão: `20`) |
| `--sources` | ❌ | Fontes a consultar: `trampos`, `programathor`, `gupy` (padrão: todas) |
| `--no-github` | ❌ | Pula análise do GitHub |

---

## Estrutura do projeto

```text
dev-job-analyzer/
├── main.py                  # CLI entrypoint (argparse)
├── .env.example             # Variáveis de ambiente (token GitHub)
├── requirements.txt         # Dependências fixadas
├── README.md
└── src/
    ├── __init__.py
    ├── models.py            # Dataclasses: JobListing, GitHubProfile, etc.
    ├── scraper.py           # Scraper trampos.co via /api/v2/
    ├── github_client.py     # GitHub REST API client
    └── report_generator.py  # Geração de .md e .html
```

Cada módulo tem uma única responsabilidade. `main.py` apenas orquestra — não contém lógica de negócio.

---

## Tecnologias utilizadas

| Tecnologia | Por que foi escolhida |
| --- | --- |
| **Python 3.10+** | Type hints com `list[str]` e `dict[str, int]` sem `from __future__` |
| **requests** | HTTP simples e confiável; trampos e gupy retornam JSON puro sem JS |
| **BeautifulSoup + lxml** | programathor.com.br renderiza server-side; lxml é o parser mais rápido |
| **python-dotenv** | Padrão de mercado para separar segredos do código |
| **argparse** | Stdlib — zero dependências extras para o CLI |
| **dataclasses** | Modelos limpos e tipados sem ORM ou Pydantic |
| **re (stdlib)** | Extração de tecnologias via regex — leve e sem dependências |

> Playwright foi avaliado mas não é necessário: trampos.co e gupy.io expõem APIs JSON públicas, e programathor.com.br renderiza server-side. Zero dependências de browser.

---

## Tratamento de erros

| Cenário | Comportamento |
| --- | --- |
| trampos.co fora do ar | `ConnectionError` com mensagem clara + exit code 1 |
| Rate limit da API trampos.co | `PermissionError` com instrução de aguardar |
| Usuário GitHub inexistente | Aviso no stderr, relatório gerado sem seção GitHub |
| Rate limit GitHub (60 req/h) | Aviso + instrução para adicionar `GITHUB_TOKEN` no `.env` |
| Token GitHub inválido | `PermissionError` com mensagem específica |

---

## Token GitHub (opcional)

Sem token: 60 requisições/hora (suficiente para uso casual).  
Com token: 5.000 requisições/hora.

### Como gerar o token

1. Acesse [github.com](https://github.com) e faça login
2. Clique na sua **foto de perfil** (canto superior direito) → **Settings**
3. No menu lateral esquerdo, desça até o fim → clique em **Developer settings**
4. Clique em **Personal access tokens** → **Tokens (classic)**
5. Clique em **Generate new token** → **Generate new token (classic)**
6. Preencha o campo **Note** com qualquer nome (ex: `dev-job-analyzer`)
7. Em **Expiration**, escolha o prazo que preferir (ex: 90 days)
8. **Não marque nenhum escopo** — para repos públicos não é necessário
9. Clique em **Generate token** no final da página
10. Copie o token gerado (começa com `ghp_`) — ele só aparece **uma vez**

### Como usar

Cole o token no arquivo `.env` na raiz do projeto:

```bash
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
```

> Se você fechar a página sem copiar, o token se perde. Nesse caso basta gerar um novo.

---

## Licença

MIT
