#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
TOKEN=$(curl -s -X POST "$BASE_URL/api/auth/demo-login" \
  -H 'Content-Type: application/json' \
  -d '{"role":"admin"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s -X POST "$BASE_URL/api/admin/ingest/samples" -H "Authorization: Bearer $TOKEN" >/dev/null
curl -s "$BASE_URL/api/search?q=San%20Miguel" -H "Authorization: Bearer $TOKEN" | python -m json.tool
curl -s -X POST "$BASE_URL/api/query" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"question":"Que naves aparecen en la Batalla de San Miguel?","output_format":"text"}' | python -m json.tool
