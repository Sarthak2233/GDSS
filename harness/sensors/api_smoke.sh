#!/usr/bin/env bash
set -e

echo "=> [Layer 3] Running API smoke sensor..."

TEMP_REPO=$(mktemp -d)
git init -b main "$TEMP_REPO" > /dev/null
git -C "$TEMP_REPO" config user.name "Smoke Test"
git -C "$TEMP_REPO" config user.email "smoke@example.com"
echo "def smoke(): pass" > "$TEMP_REPO/smoke.py"
git -C "$TEMP_REPO" add smoke.py
git -C "$TEMP_REPO" commit -m "initial commit" > /dev/null

PORT=8788
gdss serve --repo "$TEMP_REPO" --port $PORT > server.log 2>&1 &
SERVER_PID=$!

for i in $(seq 1 10); do
    if curl -s -f http://127.0.0.1:$PORT/health 2>/dev/null | grep -q '"ok"'; then
        break
    fi
    sleep 0.5
done

function cleanup {
    kill $SERVER_PID > /dev/null 2>&1 || true
    rm -rf "$TEMP_REPO"
    rm -f server.log
}
trap cleanup EXIT

curl -s -f http://127.0.0.1:$PORT/health | grep -q '"ok"'
curl -s -f http://127.0.0.1:$PORT/v1/status | grep -q '"ok"'
curl -s -f http://127.0.0.1:$PORT/v1/graph | grep -q '"ok"'
curl -s -f http://127.0.0.1:$PORT/v1/drift | grep -q '"ok"'
curl -s -f http://127.0.0.1:$PORT/v1/alerts | grep -q '"ok"'
curl -s -f http://127.0.0.1:$PORT/v1/log?n=1 | grep -q '"ok"'

JSON=$(curl -s -f http://127.0.0.1:$PORT/v1/log?n=1)
if echo "$JSON" | grep -q "Smoke Test"; then
    echo "WHAT: Privacy violation."
    echo "WHY: Found author details in API response payload."
    echo "FIX: Ensure endpoints return strictly allowed metadata only."
    exit 1
fi

echo "=> API smoke OK."
