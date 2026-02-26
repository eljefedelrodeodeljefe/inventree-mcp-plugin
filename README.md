# inventree-mcp-plugin

MCP (Model Context Protocol) server plugin for [InvenTree](https://inventree.org/). Exposes InvenTree inventory data through standardized MCP tools, allowing AI assistants like Claude to interact with your inventory.

## Features

- **Parts**: List, search, create, and update parts
- **Stock**: List, adjust, and transfer stock items
- **Locations**: Browse stock location hierarchy
- **Categories**: Browse part category hierarchy
- **Orders**: View purchase and sales orders
- **BOM**: View bill of materials for assemblies
- **Builds**: View build orders

## Installation

```bash
pip install inventree-mcp-plugin
```

Or with uv:

```bash
uv pip install inventree-mcp-plugin
```

## Configuration

1. Enable the plugin in InvenTree Admin under **Settings > Plugin Settings**
2. Configure plugin settings:
   - **Require Authentication**: Whether the MCP endpoint requires authentication (default: `true`)

The MCP endpoint is available at: `/plugin/inventree-mcp/mcp/`

### Authentication

When **Require Authentication** is enabled (the default), every request to the MCP endpoint must include a valid credential. The plugin accepts the same auth methods as the InvenTree API:

| Method | Header |
|--------|--------|
| API Token | `Authorization: Token <your-inventree-token>` |
| Bearer | `Authorization: Bearer <your-inventree-token>` |
| Basic | `Authorization: Basic <base64(user:password)>` |
| Session | Cookie-based (browser sessions) |

To obtain an API token, either use the InvenTree web UI (**Settings > API Tokens**) or request one programmatically:

```bash
curl -s http://your-inventree-instance/api/user/token/ \
  -H "Authorization: Basic $(echo -n admin:inventree | base64)"
# Returns: {"token": "inv-..."}
```

Unauthenticated requests receive a JSON-RPC error response with HTTP 401.

### User Setup and Permissions

The plugin accesses InvenTree data through the Django ORM using the permissions of the authenticated user. InvenTree uses a role-based permission system: users belong to **groups**, and each group has **rule sets** that grant `view`, `add`, `change`, and `delete` permissions across 9 role categories.

**Important:** The plugin currently bypasses InvenTree's `RolePermission` checks because it uses the ORM directly rather than the REST API. This means any authenticated user can access all tools regardless of their role assignments. For production use, create a dedicated service account with appropriate group membership to establish a clear permission boundary.

#### Recommended user profiles

Create these groups and users via the InvenTree Admin Center (**Settings > Admin Center > Groups**):

**Read-only MCP user** — for AI assistants that only need to query data:

| Role | view | add | change | delete |
|------|------|-----|--------|--------|
| Part | yes | | | |
| Part Category | yes | | | |
| Stock Item | yes | | | |
| Stock Location | yes | | | |
| Build | yes | | | |
| Purchase Order | yes | | | |
| Sales Order | yes | | | |

**Read-write MCP user** — for AI assistants that also create/modify data:

| Role | view | add | change | delete |
|------|------|-----|--------|--------|
| Part | yes | yes | yes | |
| Part Category | yes | | | |
| Stock Item | yes | | yes | |
| Stock Location | yes | | | |
| Build | yes | | | |
| Purchase Order | yes | | | |
| Sales Order | yes | | | |

#### Creating the service account

1. Go to **Admin Center > Groups** and create a group (e.g. `mcp-readonly` or `mcp-readwrite`)
2. Set the role permissions as shown above
3. Go to **Admin Center > Users** and create a new user (e.g. `mcp-service`)
4. Assign the user to the group
5. Generate an API token for the user at **Settings > API Tokens**

Or via the API (requires an admin account):

```bash
# 1. Create a group (admin token required)
curl -X POST http://your-inventree-instance/api/user/group/ \
  -H "Authorization: Token <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "mcp-readonly"}'

# 2. Create a user assigned to that group
curl -X POST http://your-inventree-instance/api/user/ \
  -H "Authorization: Token <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"username": "mcp-service", "password": "a-strong-password", "group_ids": [<group-id>]}'

# 3. Get a token for the new user
curl -s http://your-inventree-instance/api/user/token/ \
  -H "Authorization: Basic $(echo -n mcp-service:a-strong-password | base64)"
```

#### Tool permission reference

| Tool | InvenTree Role(s) | Minimum Permission |
|------|-------------------|--------------------|
| `list_parts`, `get_part`, `search_parts` | Part | view |
| `create_part` | Part, Part Category | add (part), view (category) |
| `update_part` | Part | change |
| `list_stock_items`, `get_stock_item` | Stock Item | view |
| `adjust_stock` | Stock Item | change |
| `transfer_stock` | Stock Item, Stock Location | change (stock), view (location) |
| `list_locations`, `get_location`, `get_location_tree` | Stock Location | view |
| `list_categories`, `get_category`, `get_category_tree` | Part Category | view |
| `list_purchase_orders`, `get_purchase_order` | Purchase Order | view |
| `list_sales_orders`, `get_sales_order` | Sales Order | view |
| `list_bom_items`, `get_bom_for_part` | Part | view |
| `list_build_orders`, `get_build_order` | Build | view |

## Usage with MCP Clients

Configure your MCP client to connect via Streamable HTTP transport. Include the API token in the request headers:

```json
{
  "mcpServers": {
    "inventree": {
      "transport": {
        "type": "streamable-http",
        "url": "http://your-inventree-instance/plugin/inventree-mcp/mcp/"
      },
      "requestInit": {
        "headers": {
          "Authorization": "Token <your-inventree-token>"
        }
      }
    }
  }
}
```

## Available Tools

| Tool | Description |
|------|-------------|
| `list_parts` | List parts with optional category/active filters |
| `get_part` | Get detailed part information |
| `search_parts` | Search parts by name or description |
| `create_part` | Create a new part |
| `update_part` | Update an existing part |
| `list_stock_items` | List stock items with optional filters |
| `get_stock_item` | Get detailed stock item information |
| `adjust_stock` | Add or remove stock quantity |
| `transfer_stock` | Transfer stock to a different location |
| `list_locations` | List stock locations |
| `get_location` | Get location details |
| `get_location_tree` | Get hierarchical location tree |
| `list_categories` | List part categories |
| `get_category` | Get category details |
| `get_category_tree` | Get hierarchical category tree |
| `list_purchase_orders` | List purchase orders |
| `get_purchase_order` | Get purchase order with line items |
| `list_sales_orders` | List sales orders |
| `get_sales_order` | Get sales order with line items |
| `list_bom_items` | List BOM items |
| `get_bom_for_part` | Get full BOM for a part |
| `list_build_orders` | List build orders |
| `get_build_order` | Get build order details |

## Development

### Prerequisites

- [uv](https://docs.astral.sh/uv/) — Python package manager
- [prek](https://github.com/j178/prek) — pre-commit hook runner (replaces `pre-commit`)

Install prek and set up git hooks:

```bash
prek install
```

```bash
# Clone the repository
git clone https://github.com/eljefedelrodeodeljefe/inventree-mcp-plugin.git
cd inventree-mcp-plugin

# Install dependencies
uv sync --dev

# Run linting
uv run ruff check .
uv run ruff format --check .

# Run unit tests (mocked, no InvenTree required)
uv run pytest -v
```

## Integration Testing

A `docker-compose.dev.yml` is included to spin up a **disposable** InvenTree instance with PostgreSQL, Redis, and the plugin volume-mounted. All state lives in Docker volumes that are destroyed on teardown.

### Integration Prerequisites

- Docker and Docker Compose v2+

### Quick start

```bash
# Start InvenTree and seed the demo dataset
./scripts/integration-test.sh up

# MCP endpoint is now live at:
#   http://localhost:8000/plugin/inventree-mcp/mcp/

# Get an admin API token (useful for curl/httpie testing)
./scripts/integration-test.sh token
```

### Test accounts

The `up` command seeds InvenTree's [demo dataset](https://github.com/inventree/demo-dataset) and creates dedicated MCP service accounts:

| Username | Password | Purpose |
|----------|----------|---------|
| `admin` | `inventree` | Superuser — full access, use for admin tasks |
| `mcp-service` | `mcp-service` | MCP service account — assign roles via Admin Center |
| `mcp-readonly` | `mcp-readonly` | No roles — use to verify permission denials |
| `allaccess` | `nolimits` | Demo user — full permissions |
| `reader` | `readonly` | Demo user — view only |

After `up`, configure the `mcp-readwrite` group's role permissions via the Admin Center (**Admin Center > Groups > mcp-readwrite > Rule Sets**). See [User Setup and Permissions](#user-setup-and-permissions) for the recommended role matrix.

Get tokens for different users:

```bash
./scripts/integration-test.sh token           # mcp-service (default)
./scripts/integration-test.sh token admin     # admin superuser
./scripts/integration-test.sh token readonly  # mcp-readonly (no roles)
```

### Resetting state

```bash
# Wipe all data and re-seed (keeps containers running)
./scripts/integration-test.sh reset
```

This runs `invoke dev.delete-data` followed by `invoke dev.setup-test -i`, giving you a clean slate without rebuilding containers.

### Teardown

```bash
# Stop containers and delete all volumes
./scripts/integration-test.sh down
```

### Smoke tests

The script includes an authenticated smoke test suite that verifies the MCP endpoint end-to-end:

```bash
./scripts/integration-test.sh smoke
```

This automatically obtains a token and tests:

1. Unauthenticated requests are rejected (401)
2. Authenticated `initialize` succeeds
3. Authenticated `tools/list` returns registered tools
4. Authenticated `tools/call` for `list_parts` succeeds

### Manual MCP testing

With the stack running, obtain a token first then test the endpoint:

```bash
# Get a token
TOKEN=$(./scripts/integration-test.sh token)

# Initialize the MCP session
curl -X POST http://localhost:8000/plugin/inventree-mcp/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "Authorization: Token ${TOKEN}" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2025-03-26",
      "capabilities": {},
      "clientInfo": { "name": "test", "version": "0.1.0" }
    }
  }'

# List available tools
curl -X POST http://localhost:8000/plugin/inventree-mcp/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "Authorization: Token ${TOKEN}" \
  -d '{"jsonrpc": "2.0", "id": 2, "method": "tools/list"}'

# Call a tool
curl -X POST http://localhost:8000/plugin/inventree-mcp/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "Authorization: Token ${TOKEN}" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": { "name": "list_parts", "arguments": { "limit": 5 } }
  }'
```

### Script reference

```bash
./scripts/integration-test.sh up               # Start stack, seed data, create MCP users
./scripts/integration-test.sh reset            # Wipe data, re-seed, re-create MCP users
./scripts/integration-test.sh token            # Print mcp-service API token
./scripts/integration-test.sh token admin      # Print admin API token
./scripts/integration-test.sh token readonly   # Print mcp-readonly API token
./scripts/integration-test.sh smoke            # Run authenticated smoke tests
./scripts/integration-test.sh status           # Check if InvenTree is healthy
./scripts/integration-test.sh down             # Tear down + delete volumes
```

## License

MIT
