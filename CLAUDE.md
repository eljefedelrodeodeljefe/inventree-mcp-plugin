# CLAUDE.md

## Project

MCP (Model Context Protocol) server plugin for [InvenTree](https://inventree.org/). Runs inside InvenTree as a Django plugin; exposes inventory data via stateless Streamable HTTP to MCP clients (Claude, etc.).

## Commands

```bash
# Setup
uv sync --dev
prek install          # install git hooks

# Lint
uv run ruff check .
uv run ruff format --check .
uv run mypy inventree_mcp_plugin

# Unit tests (no InvenTree required — all deps are mocked)
uv run pytest -v

# Integration tests (requires Docker)
./scripts/integration-test.sh up       # start stack, seed data, create MCP users
./scripts/integration-test.sh smoke    # run authenticated end-to-end smoke tests
./scripts/integration-test.sh token    # print mcp-service API token
./scripts/integration-test.sh down     # tear down + delete volumes
```

## Architecture

```text
HTTP request (MCP client)
  → Django URL router
  → MCPView (mcp_transport.py)        — auth check, ASGI scope construction
  → StreamableHTTPSessionManager
  → FastMCP server (mcp_server.py)    — stateless, JSON responses
  → @mcp.tool() functions (tools/)    — Django ORM queries
  → JSON-RPC response
```

Key files:

| File | Purpose |
|------|---------|
| `inventree_mcp_plugin/core.py` | Plugin entry point, URL registration, `REQUIRE_AUTH` setting |
| `inventree_mcp_plugin/mcp_server.py` | FastMCP instance, imports all tool modules to register them |
| `inventree_mcp_plugin/mcp_transport.py` | `MCPView` — bridges Django HTTP ↔ MCP ASGI |
| `inventree_mcp_plugin/tools/simple/` | One module per domain (parts, stock, locations, categories, orders, bom, builds) |
| `inventree_mcp_plugin/tools/combinatory/` | Tools that compose multiple simple operations (empty — add new tools here) |
| `inventree_mcp_plugin/tools/complex/` | Multi-step orchestration tools (empty — add new tools here) |
| `tests/conftest.py` | Stubs Django/InvenTree modules so tools can be imported without InvenTree |

## Conventions

- **Tools**: each tool is a standalone function decorated with `@mcp.tool()`. Docstrings drive MCP schema generation — keep them accurate.
- **ORM access**: tools query InvenTree models directly (not via the REST API). `request.user` auth is handled upstream in `MCPView`.
- **Types**: strict mypy. All parameters and return types must be annotated.
- **Line length**: 120 characters (ruff).
- **Python**: 3.11+ only. No backcompat shims.
- **Dependencies**: `mcp>=1.9` is the only production dependency. Django and InvenTree are provided by the plugin host environment — do not add them to `pyproject.toml`.
- **Unit tests**: mock the entire InvenTree/Django module tree via `conftest.py`. Tests must run with `uv run pytest` and no InvenTree instance.
- **Tool list sync**: when adding, removing, or renaming tools, always update the tool list in both `README.md` and the "Working with the live InvenTree instance" section of this file.

## Git workflow

**Branching — Gitflow:**

| Branch | Purpose |
| ------ | ------- |
| `main` | Latest release — only receives merges from `release/*` and `hotfix/*` |
| `develop` | Integration branch — all feature work targets here |
| `feature/<name>` | New features, branched from and merged back into `develop` |
| `release/<version>` | Release prep (version bump, changelog), merged into `main` + `develop` |
| `hotfix/<name>` | Critical fixes on `main`, merged into `main` + `develop` |

**Commits — Conventional Commits:**

```text
<type>(<scope>): <short summary>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `ci`, `perf`

Scope is optional but encouraged when targeting a specific area (e.g. `tools`, `auth`, `stock`).

```text
feat(tools): add create_build_order tool
fix(auth): return 401 on expired token
chore(deps): bump mcp to 1.10
docs: add prek prerequisite to README
```

Breaking changes must include `BREAKING CHANGE:` in the commit footer.

## CI

Four jobs in `.github/workflows/ci.yml`:

| Job | What it does |
|-----|-------------|
| `lint` | `ruff check` + `ruff format --check` + `mypy` |
| `pre-commit` | `prek run --all-files` via `j178/prek-action@v1` |
| `test` | `pytest -v` |
| `smoke` | Spins up the Docker integration stack and runs `integration-test.sh smoke` |

## Releases

Automated via `python-semantic-release` in `.github/workflows/release.yml`. Triggered manually via `workflow_dispatch` (Actions → Release → Run workflow). PSR parses Conventional Commit messages since the last tag, bumps the version in `pyproject.toml`, updates `CHANGELOG.md`, creates a git tag, and publishes a GitHub release. No manual version bumping needed — just follow the commit convention.

## Working with the live InvenTree instance

An `inventree` MCP server is configured in `.mcp.json` and points to the local integration test stack (`http://localhost:8000`). When the stack is running, the following tools are available directly — use them instead of making raw HTTP requests or suggesting curl commands:

`list_parts`, `get_part`, `search_parts`, `create_part`, `update_part`, `delete_parts`, `list_stock_items`, `get_stock_item`, `adjust_stock`, `transfer_stock`, `list_locations`, `get_location`, `get_location_tree`, `list_categories`, `get_category`, `get_category_tree`, `list_purchase_orders`, `get_purchase_order`, `list_sales_orders`, `get_sales_order`, `list_bom_items`, `get_bom_for_part`, `list_build_orders`, `get_build_order`, `list_tags`, `search_tags`

**Always prefer these MCP tools** for any inventory query or mutation. Do not use WebFetch, Bash curl, or the InvenTree REST API directly.

Start the stack if needed: `./scripts/integration-test.sh up`

## Integration test stack

`docker-compose.dev.yml` runs PostgreSQL 17, Redis 7, InvenTree (stable), and a Celery worker. The plugin directory is volume-mounted read-only into the container. Credentials: `admin` / `inventree`. See `scripts/integration-test.sh` for full command reference.
