# Contributing to enviroplus-sensors-to-mqtt

Thank you for your interest in contributing!

## Development Workflow

1. Clone the repository and install the development environment:
   ```bash
   git clone https://github.com/hellqvio86/enviroplus-sensors-to-mqtt.git
   cd enviroplus-sensors-to-mqtt
   make install
   ```

2. Verify tests and linters pass:
   ```bash
   make test
   ```

## Code Standards

- **Linting & Formatting**: Follow Ruff configuration defined in `pyproject.toml`. Run `uv run ruff check .` and `uv run ruff format src tests`.
- **Typing**: Follow standard type hints (`str | None` rather than `Optional[str]`).
- **Testing**: All changes and bugfixes must include unit tests. Tests must run without physical hardware or network connectivity. Maintain $\ge 75\%$ test coverage.
- **Line Endings**: LF line endings are enforced across all text files via `.gitattributes`.

---

## Commit & Tagging Conventions

### Conventional Commit Tags
All commit messages must strictly follow [Conventional Commits](https://www.conventionalcommits.org/):
- `feat(...)`: New user-facing features or command-line flags
- `fix(...)`: Bug fixes
- `perf(...)`: Performance optimizations
- `docs(...)`: Documentation updates
- `test(...)`: Adding or improving tests
- `refactor(...)`: Code refactoring without behavior change
- `chore(...)`: Maintenance, dependency updates, or version bumps (e.g., `chore(release): bump version to 0.2.0`)
- `ci(...)`: CI/CD workflows and automation scripts

### Git Release Tags
All git release tags must strictly adhere to Semantic Versioning with a mandatory lowercase `v` prefix:
- **Format**: `v<MAJOR>.<MINOR>.<PATCH>` (e.g., `v0.1.0`, `v0.2.0`, `v1.0.0`).
- **Rule**: Never create or push raw numeric tags without the leading `v` (e.g., `0.2.0` is strictly forbidden).
- **Pre-releases** (if applicable): `v<MAJOR>.<MINOR>.<PATCH>-<pre>` (e.g., `v0.2.0-rc.1`).
- **Automation**: CI automatically creates the annotated tag `v<version>` from `pyproject.toml` when a release is drafted on `main`.
