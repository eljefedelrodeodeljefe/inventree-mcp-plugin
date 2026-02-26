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

cmd_up() {
    echo "Starting InvenTree integration test stack..."
    $COMPOSE up -d
    _wait_healthy
    echo "Seeding demo data (this will take a moment)..."
    $COMPOSE run --rm inventree-server invoke dev.setup-test -i
    echo ""

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
    echo "Get a token:  ./scripts/integration-test.sh token"
    echo "Smoke test:   ./scripts/integration-test.sh smoke"
}

cmd_reset() {
    echo "Resetting InvenTree data..."
    $COMPOSE run --rm inventree-server invoke dev.delete-data
    $COMPOSE run --rm inventree-server invoke dev.setup-test -i
    _setup_mcp_users
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

cmd_smoke() {
    echo "Running MCP smoke tests..."
    echo ""

    local token
    token=$(_get_token)
    local auth_header="Authorization: Token ${token}"
    local pass=0
    local fail=0

    # --- Test 1: Unauthenticated request should be rejected ---
    echo -n "1. Unauthenticated request returns 401... "
    local status
    status=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${MCP_URL}" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json" \
        -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"0.1.0"}}}')
    if [ "$status" = "401" ]; then
        echo "PASS"
        pass=$((pass + 1))
    else
        echo "FAIL (got ${status})"
        fail=$((fail + 1))
    fi

    # --- Test 2: Authenticated initialize ---
    echo -n "2. Authenticated initialize... "
    local resp
    resp=$(curl -sf -X POST "${MCP_URL}" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json" \
        -H "${auth_header}" \
        -d '{
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": { "name": "smoke-test", "version": "0.1.0" }
            }
        }' 2>&1) || true
    if echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'result' in d" 2>/dev/null; then
        echo "PASS"
        pass=$((pass + 1))
    else
        echo "FAIL"
        echo "  Response: ${resp}"
        fail=$((fail + 1))
    fi

    # --- Test 3: Authenticated tools/list ---
    echo -n "3. Authenticated tools/list returns tools... "
    resp=$(curl -sf -X POST "${MCP_URL}" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json" \
        -H "${auth_header}" \
        -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' 2>&1) || true
    if echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); assert len(d['result']['tools']) > 0" 2>/dev/null; then
        local tool_count
        tool_count=$(echo "$resp" | python3 -c "import sys,json; print(len(json.load(sys.stdin)['result']['tools']))")
        echo "PASS (${tool_count} tools)"
        pass=$((pass + 1))
    else
        echo "FAIL"
        echo "  Response: ${resp}"
        fail=$((fail + 1))
    fi

    # --- Test 4: Authenticated tools/call (list_parts) ---
    echo -n "4. Authenticated tools/call list_parts... "
    resp=$(curl -sf -X POST "${MCP_URL}" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json" \
        -H "${auth_header}" \
        -d '{
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": { "name": "list_parts", "arguments": { "limit": 3 } }
        }' 2>&1) || true
    if echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'result' in d" 2>/dev/null; then
        echo "PASS"
        pass=$((pass + 1))
    else
        echo "FAIL"
        echo "  Response: ${resp}"
        fail=$((fail + 1))
    fi

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

cmd_down() {
    echo "Tearing down stack and removing volumes..."
    $COMPOSE down -v --remove-orphans
    echo "Done."
}

case "${1:-help}" in
    up)     cmd_up ;;
    reset)  cmd_reset ;;
    token)  cmd_token "$@" ;;
    smoke)  cmd_smoke ;;
    status) cmd_status ;;
    down)   cmd_down ;;
    *)
        echo "Usage: $0 {up|reset|token|smoke|status|down}"
        echo ""
        echo "  up               Start the stack, seed demo data, create MCP users"
        echo "  reset            Wipe all data, re-seed, re-create MCP users"
        echo "  token [user]     Print an API token (user: admin|readonly, default: mcp-service)"
        echo "  smoke            Run authenticated smoke tests against the MCP endpoint"
        echo "  status           Check if InvenTree is healthy"
        echo "  down             Tear down the stack and delete all volumes"
        exit 1
        ;;
esac
