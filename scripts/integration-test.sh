#!/usr/bin/env bash
#
# Helper script for integration testing with a disposable InvenTree instance.
#
# Usage:
#   ./scripts/integration-test.sh up             # Start stack, seed data, create MCP users
#   ./scripts/integration-test.sh reset          # Wipe data, re-seed, re-create MCP users
#   ./scripts/integration-test.sh token          # Print mcp-service API token
#   ./scripts/integration-test.sh token admin    # Print admin API token
#   ./scripts/integration-test.sh token readonly # Print mcp-readonly API token
#   ./scripts/integration-test.sh smoke          # Run authenticated smoke tests
#   ./scripts/integration-test.sh status         # Check if the server is healthy
#   ./scripts/integration-test.sh down           # Tear down stack and delete all volumes
#   ./scripts/integration-test.sh mcp-config     # Write .mcp.json with a fresh token
#
set -euo pipefail

COMPOSE="docker compose -f docker-compose.dev.yml"
SERVER_URL="${INVENTREE_URL:-http://localhost:8000}"
MCP_URL="${SERVER_URL}/plugin/inventree-mcp/mcp/"

_wait_healthy() {
    echo "Waiting for InvenTree to become healthy..."
    local retries=60
    while [ $retries -gt 0 ]; do
        if curl -sf "${SERVER_URL}/api/" > /dev/null 2>&1; then
            echo "InvenTree is ready at ${SERVER_URL}"
            return 0
        fi
        retries=$((retries - 1))
        sleep 2
    done
    echo "ERROR: InvenTree did not become healthy within 120s" >&2
    $COMPOSE logs inventree-server --tail=30
    return 1
}

_get_admin_token() {
    curl -sf -X GET "${SERVER_URL}/api/user/token/" \
        -H "Authorization: Basic $(echo -n admin:inventree | base64)" \
        | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])"
}

_get_token() {
    # Returns the mcp-service token if that user exists, otherwise admin token
    local svc_token
    svc_token=$(curl -sf -X GET "${SERVER_URL}/api/user/token/" \
        -H "Authorization: Basic $(echo -n mcp-service:mcp-service | base64)" \
        2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])" 2>/dev/null) || true
    if [ -n "$svc_token" ]; then
        echo "$svc_token"
    else
        _get_admin_token
    fi
}

_setup_mcp_users() {
    # Create MCP service accounts with appropriate permissions.
    # Requires admin token. Failures are non-fatal (users may already exist).
    local admin_token
    admin_token=$(_get_admin_token)
    local auth="Authorization: Token ${admin_token}"
    local ct="Content-Type: application/json"

    echo "Creating MCP service group and users..."

    # Create mcp-readwrite group
    local group_id
    group_id=$(curl -sf -X POST "${SERVER_URL}/api/user/group/" \
        -H "$auth" -H "$ct" \
        -d '{"name": "mcp-readwrite"}' \
        2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('pk',''))" 2>/dev/null) || true

    if [ -z "$group_id" ]; then
        # Group may already exist — look it up
        group_id=$(curl -sf "${SERVER_URL}/api/user/group/?search=mcp-readwrite" \
            -H "$auth" \
            | python3 -c "import sys,json; r=json.load(sys.stdin); print(r[0]['pk'] if r else '')" 2>/dev/null) || true
    fi

    if [ -n "$group_id" ]; then
        echo "  Group 'mcp-readwrite' id=${group_id}"
    else
        echo "  WARNING: Could not create or find group. Skipping user setup."
        return 0
    fi

    # Create mcp-service user assigned to the group
    curl -sf -X POST "${SERVER_URL}/api/user/" \
        -H "$auth" -H "$ct" \
        -d "{\"username\": \"mcp-service\", \"password\": \"mcp-service\", \"group_ids\": [${group_id}]}" \
        > /dev/null 2>&1 || true
    echo "  User 'mcp-service' (password: mcp-service)"

    # Create mcp-readonly user (separate group would be ideal, but for dev
    # testing we just create the user without the readwrite group)
    curl -sf -X POST "${SERVER_URL}/api/user/" \
        -H "$auth" -H "$ct" \
        -d '{"username": "mcp-readonly", "password": "mcp-readonly"}' \
        > /dev/null 2>&1 || true
    echo "  User 'mcp-readonly' (password: mcp-readonly, no group — read-only stub)"

    echo "  NOTE: Role permissions for groups must be configured via the InvenTree"
    echo "        Admin Center UI (Admin Center > Groups > mcp-readwrite > Rule Sets)."
    echo "        The API does not currently support setting rule sets directly."
}

_install_plugin() {
    # Install the mcp package into the running containers, activate the plugin,
    # then restart so InvenTree registers the plugin URLs.
    echo "Installing mcp package in containers..."
    $COMPOSE exec -T inventree-server pip install 'mcp>=1.9' --quiet
    # Worker may still be starting up; installation is best-effort
    $COMPOSE exec -T inventree-worker pip install 'mcp>=1.9' --quiet 2>/dev/null || true

    echo "Activating MCP plugin and enabling plugin URLs in InvenTree database..."
    $COMPOSE exec -T inventree-server sh -c "
cd /home/inventree/src/backend/InvenTree
python manage.py shell -c \"
from plugin.models import PluginConfig
from common.models import InvenTreeSetting
cfg, created = PluginConfig.objects.get_or_create(key='inventree-mcp', defaults={'name': 'InvenTreeMCPPlugin', 'active': True})
if not cfg.active:
    cfg.active = True
    cfg.save()
print('  Plugin active:', cfg.key)
InvenTreeSetting.set_setting('ENABLE_PLUGINS_URL', True, None)
print('  ENABLE_PLUGINS_URL: True')
\"" 2>/dev/null || echo "  WARNING: could not activate plugin via shell (will retry after restart)"

    echo "Restarting services to register plugin URLs..."
    $COMPOSE restart inventree-server inventree-worker
    _wait_healthy
}

cmd_up() {
    echo "Starting InvenTree integration test stack..."
    $COMPOSE up -d
    _wait_healthy
    echo "Seeding demo data (this will take a moment)..."
    $COMPOSE run --rm inventree-server invoke dev.setup-test -i
    echo ""
    _install_plugin

    _setup_mcp_users
    echo ""
    echo "Ready! Accounts:"
    echo "  admin / inventree          (superuser — full access)"
    echo "  allaccess / nolimits       (demo — full permissions)"
    echo "  reader / readonly          (demo — view only)"
    echo "  mcp-service / mcp-service  (MCP — assign roles via Admin Center)"
    echo "  mcp-readonly / mcp-readonly (MCP — no roles, for testing 403s)"
    echo ""
    echo "MCP endpoint: ${MCP_URL}"
    echo ""
    _write_mcp_config
    echo ""
    echo "Smoke test:   ./scripts/integration-test.sh smoke"
}

cmd_reset() {
    echo "Resetting InvenTree data..."
    $COMPOSE run --rm inventree-server invoke dev.delete-data
    $COMPOSE run --rm inventree-server invoke dev.setup-test -i
    _install_plugin
    _setup_mcp_users
    _write_mcp_config
    echo "Data reset complete."
}

cmd_token() {
    local user="${2:-}"
    case "$user" in
        admin)
            _get_admin_token
            ;;
        readonly)
            curl -sf -X GET "${SERVER_URL}/api/user/token/" \
                -H "Authorization: Basic $(echo -n mcp-readonly:mcp-readonly | base64)" \
                | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])"
            ;;
        *)
            # Default: mcp-service if available, else admin
            _get_token
            ;;
    esac
}

_smoke_pass() { echo "PASS"; }
_smoke_fail() { echo "FAIL"; echo "  Response: $1"; }

# Assert a JSON-RPC tool call response has isError:false and the content is a list.
# FastMCP encodes each list item as a separate content block; the canonical
# list is in structuredContent.result (MCP 2025-03-26+).
_assert_tool_list() {
    python3 -c "
import sys, json
d = json.load(sys.stdin)
assert 'result' in d, 'no result key'
assert not d['result']['isError'], 'isError is true: ' + str(d['result'])
sc = d['result'].get('structuredContent', {})
items = sc['result'] if 'result' in sc else d['result']['content']
assert isinstance(items, list), 'items is not a list: ' + type(items).__name__
print(len(items))
" 2>/dev/null
}

# Assert a JSON-RPC tool call response has isError:false (for non-list returns).
_assert_tool_ok() {
    python3 -c "
import sys, json
d = json.load(sys.stdin)
assert 'result' in d, 'no result key'
assert not d['result']['isError'], 'isError is true: ' + str(d['result'])
" 2>/dev/null
}

cmd_smoke() {
    echo "Running MCP smoke tests..."
    echo ""

    local token
    token=$(_get_token)
    local auth="Authorization: Token ${token}"
    local ct="Content-Type: application/json"
    local accept="Accept: application/json"
    local pass=0
    local fail=0
    local resp

    # --- Test 1: Unauthenticated request should be rejected ---
    echo -n "1. Unauthenticated request returns 401... "
    local status
    status=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${MCP_URL}" \
        -H "$ct" -H "$accept" \
        -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"0.1.0"}}}')
    if [ "$status" = "401" ]; then
        _smoke_pass; pass=$((pass + 1))
    else
        _smoke_fail "(got ${status})"; fail=$((fail + 1))
    fi

    # --- Test 2: Authenticated initialize ---
    echo -n "2. Authenticated initialize... "
    resp=$(curl -sf -X POST "${MCP_URL}" -H "$ct" -H "$accept" -H "$auth" \
        -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"smoke-test","version":"0.1.0"}}}' \
        2>&1) || true
    if echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'result' in d" 2>/dev/null; then
        _smoke_pass; pass=$((pass + 1))
    else
        _smoke_fail "$resp"; fail=$((fail + 1))
    fi

    # --- Test 3: Authenticated tools/list ---
    echo -n "3. tools/list returns 28 tools... "
    resp=$(curl -sf -X POST "${MCP_URL}" -H "$ct" -H "$accept" -H "$auth" \
        -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' 2>&1) || true
    if echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); assert len(d['result']['tools']) == 28" 2>/dev/null; then
        _smoke_pass; pass=$((pass + 1))
    else
        local tool_count
        tool_count=$(echo "$resp" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('result',{}).get('tools',[])))" 2>/dev/null || echo "?")
        _smoke_fail "got ${tool_count} tools — expected 28"; fail=$((fail + 1))
    fi

    # --- Tests 4–12: tools/call for every domain ---
    _smoke_call() {
        local num="$1" label="$2" tool="$3" args="$4"
        echo -n "${num}. tools/call ${label}... "
        resp=$(curl -sf -X POST "${MCP_URL}" -H "$ct" -H "$accept" -H "$auth" \
            -d "{\"jsonrpc\":\"2.0\",\"id\":${num},\"method\":\"tools/call\",\"params\":{\"name\":\"${tool}\",\"arguments\":${args}}}" \
            2>&1) || true
        local count
        count=$(echo "$resp" | _assert_tool_list 2>/dev/null) || count=""
        if [ -n "$count" ]; then
            echo "PASS (${count} items)"; pass=$((pass + 1))
        else
            _smoke_fail "$resp"; fail=$((fail + 1))
        fi
    }

    _smoke_call  4 "list_parts"           list_parts           '{"limit":5}'
    _smoke_call  5 "search_parts"         search_parts         '{"query":"r","limit":5}'
    _smoke_call  6 "list_categories"      list_categories      '{"limit":5}'
    _smoke_call  7 "list_stock_items"     list_stock_items     '{"limit":5}'
    _smoke_call  8 "list_locations"       list_locations       '{"limit":5}'
    _smoke_call  9 "list_purchase_orders" list_purchase_orders '{"limit":5}'
    _smoke_call 10 "list_sales_orders"    list_sales_orders    '{"limit":5}'
    _smoke_call 11 "list_build_orders"    list_build_orders    '{"limit":5}'
    _smoke_call 12 "list_bom_items"       list_bom_items       '{"limit":5}'

    # --- Summary ---
    echo ""
    echo "Results: ${pass} passed, ${fail} failed"
    if [ "$fail" -gt 0 ]; then
        return 1
    fi
}

cmd_status() {
    if curl -sf "${SERVER_URL}/api/" > /dev/null 2>&1; then
        echo "InvenTree is running at ${SERVER_URL}"
        $COMPOSE ps
    else
        echo "InvenTree is not responding at ${SERVER_URL}"
        $COMPOSE ps
        return 1
    fi
}

_write_mcp_config() {
    local token
    token=$(_get_token)
    local mcp_json
    mcp_json=$(cat <<EOF
{
  "mcpServers": {
    "inventree": {
      "type": "http",
      "url": "${SERVER_URL}/plugin/inventree-mcp/mcp/",
      "headers": {
        "Authorization": "Token ${token}"
      }
    }
  }
}
EOF
)
    local config_file
    config_file="$(dirname "$(dirname "$0")")/.mcp.json"
    echo "$mcp_json" > "$config_file"
    echo "Wrote ${config_file} (token: ${token:0:12}...)"
    echo "Reconnect the MCP server in Claude Code to pick up the new token."
}

cmd_mcp_config() {
    _write_mcp_config
}

cmd_down() {
    echo "Tearing down stack and removing volumes..."
    $COMPOSE down -v --remove-orphans
    echo "Done."
}

case "${1:-help}" in
    up)         cmd_up ;;
    reset)      cmd_reset ;;
    token)      cmd_token "$@" ;;
    smoke)      cmd_smoke ;;
    status)     cmd_status ;;
    down)       cmd_down ;;
    mcp-config) cmd_mcp_config ;;
    *)
        echo "Usage: $0 {up|reset|token|smoke|status|down|mcp-config}"
        echo ""
        echo "  up               Start the stack, seed demo data, create MCP users"
        echo "  reset            Wipe all data, re-seed, re-create MCP users"
        echo "  token [user]     Print an API token (user: admin|readonly, default: mcp-service)"
        echo "  smoke            Run authenticated smoke tests against the MCP endpoint"
        echo "  status           Check if InvenTree is healthy"
        echo "  down             Tear down the stack and delete all volumes"
        echo "  mcp-config       Write .mcp.json with a fresh token for Claude Code"
        exit 1
        ;;
esac
