#!/bin/bash
# Smoke test for v1.5.5+7+8 — runs against the gateway on localhost:8001
# via nginx on localhost:2026.
set -e

BASE="${BASE:-http://localhost:2026}"
echo "=== Smoke test against $BASE ==="

echo ""
echo "1. /health"
curl -sf "$BASE/health" | head -1
echo ""

echo "2. /api/connectors (v1.5.5 — expects 0 connectors without MICX_CONNECTORS env)"
curl -sf "$BASE/api/connectors" | head -1
echo ""

echo "3. /api/connectors/dlq (v1.5.5)"
curl -sf "$BASE/api/connectors/dlq" | head -1
echo ""

echo "4. /api/spaces (v1.5.5)"
curl -sf "$BASE/api/spaces" | head -1
echo ""

echo "5. /api/spaces/current (v1.5.5 — falls back to personal)"
curl -sf "$BASE/api/spaces/current" | head -1
echo ""

echo "6. /api/subscriptions?target_kind=thread&target_id=t-1 (v1.5.5)"
curl -sf -X GET "$BASE/api/subscriptions/thread/t-1" -w "\n  http_status=%{http_code}\n" | head -2
echo ""

echo "7. /api/users/search?q=alice (v1.5.7)"
curl -sf "$BASE/api/users/search?q=alice" | head -1
echo ""

echo "=== Smoke complete ==="
