# Contributing

Thanks for your interest in **myebirdstuff**. This document is a short entry point; deeper architecture, testing, and refactor notes live in **[docs/development.md](docs/development.md)**.

---

## Code of conduct

We want collaboration to be welcoming and constructive. Please:

- Be respectful and assume good intent.
- Stay focused on the work: disagree with ideas, not people.
- Help keep discussion inclusive; harassment and abuse are not acceptable.

If something crosses a line, report it to the maintainers (e.g. via GitHub issue or contact the repo owner). Maintainers may remove participants or content that undermines a safe, productive environment.

---

## How to contribute

1. **Issues** — For bugs, describe what you expected, what happened, and how to reproduce (OS, Python version, and steps). For features or larger changes, opening an issue first helps align on scope.
2. **Pull requests** — Fork the repo, create a branch from the target default branch (e.g. `main`), and open a PR when the change is ready for review.
3. **Commits & PRs** — Prefer small, reviewable changes. In the PR description, explain **what** changed and **why** (and note any trade-offs). Link related issues when applicable.

---

## Development setup

- **Python:** Use a version consistent with CI (currently **3.12**; see [.github/workflows/tests.yml](.github/workflows/tests.yml)). Why we align with CI instead of bumping to every new Python release: [docs/development.md — Python version](docs/development.md#python-version).
- **Dependencies:**  
  `pip install -r requirements.txt`  
  For the **GPS script** (`scripts/eBirdChecklistNameFromGPS.py`): also `pip install -r requirements-gps-script.txt`. Offline tests (no API key):  
  `python scripts/eBirdChecklistNameFromGPS.py --testfile tests/fixtures/gps_checklistName_testing.json` (see the script docstring).
- **Tests:**  
  `pytest tests/ -v`  
  Optional coverage (matches CI’s package scope):  
  `pytest tests/ -v --cov=explorer --cov-report=term-missing`  
  More detail: [docs/development.md — Testing workflow](docs/development.md#testing-workflow).
- **Lint:**  
  `ruff check explorer/`  
  (same as CI; `ruff` is in `requirements.txt`, rules in `ruff.toml` — currently Pyflakes + pycodestyle, with line-length and import-order left for a later pass).

---

## Project conventions

- **Design and modules** — See [docs/development.md](docs/development.md) (architecture, separation of UI vs core logic, Streamlit notes). **Map/theme tweakables** (clustering, pin size/opacity, colours) live in [`explorer/app/streamlit/defaults.py`](explorer/app/streamlit/defaults.py). Fixed UI strings, URLs, and spinner emoji lists live in [`explorer/app/streamlit/streamlit_ui_constants.py`](explorer/app/streamlit/streamlit_ui_constants.py). Persisted settings schema defaults live in [`explorer/core/settings_schema_defaults.py`](explorer/core/settings_schema_defaults.py). See [docs/AI_CONTEXT.md — Defaults](docs/AI_CONTEXT.md#defaults).
- **AI-assisted work** — If you use AI tools, follow **[docs/AI_CONTEXT.md](docs/AI_CONTEXT.md)** (AI Coding Rules and related sections).
- **Secrets** — Do not commit API keys, tokens, or personal paths. Use local config patterns described in the explorer docs (e.g. `config/config_template.yaml` and gitignored secret files). When in doubt, ask before adding something that could leak private data.

---

## License and expectations

By contributing, you agree that your contributions are licensed under the same terms as the project (see the repository **LICENSE** if present). If you are unsure whether a change is appropriate, open an issue first.
