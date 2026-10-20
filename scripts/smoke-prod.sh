#!/usr/bin/env bash
# Post-deployment smoke checks against public Azure URLs.
# Required env: BACKEND_PUBLIC_URL, FRONTEND_PUBLIC_URL
# Optional: SMOKE_MAX_ATTEMPTS (default 12), SMOKE_SLEEP_SECONDS (default 10)
set -euo pipefail

SMOKE_MAX_ATTEMPTS="${SMOKE_MAX_ATTEMPTS:-12}"
SMOKE_SLEEP_SECONDS="${SMOKE_SLEEP_SECONDS:-10}"
CURL_CONNECT_TIMEOUT="${CURL_CONNECT_TIMEOUT:-5}"
CURL_MAX_TIME="${CURL_MAX_TIME:-15}"
BODY_TRUNCATE="${BODY_TRUNCATE:-500}"

strip_slash() {
  local u="${1:-}"
  u="${u%/}"
  printf '%s' "$u"
}

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "ERROR: ${name} is unset or empty (must be a public HTTPS origin, not localhost)." >&2
    exit 1
  fi
}

require_env BACKEND_PUBLIC_URL
require_env FRONTEND_PUBLIC_URL

BACKEND_PUBLIC_URL="$(strip_slash "$BACKEND_PUBLIC_URL")"
FRONTEND_PUBLIC_URL="$(strip_slash "$FRONTEND_PUBLIC_URL")"

echo "Smoke targets:"
echo "  BACKEND_PUBLIC_URL=${BACKEND_PUBLIC_URL}"
echo "  FRONTEND_PUBLIC_URL=${FRONTEND_PUBLIC_URL}"
echo "  attempts=${SMOKE_MAX_ATTEMPTS} sleep=${SMOKE_SLEEP_SECONDS}s"

# GET url -> writes body to $1 file, echoes HTTP status (or 000 on transport failure).
http_get() {
  local url="$1"
  local out_file="$2"
  local code
  code="$(
    curl -sS \
      --connect-timeout "${CURL_CONNECT_TIMEOUT}" \
      --max-time "${CURL_MAX_TIME}" \
      -o "${out_file}" \
      -w '%{http_code}' \
      "${url}" 2>/dev/null || true
  )"
  if [[ -z "${code}" ]]; then
    code="000"
  fi
  printf '%s' "${code}"
}

truncate_body() {
  local f="$1"
  if [[ ! -f "${f}" ]]; then
    echo "(no body)"
    return
  fi
  head -c "${BODY_TRUNCATE}" "${f}" | tr '\n' ' '
  echo
}

# Retry wrapper: attempt until validate_fn succeeds or attempts exhausted.
# validate_fn receives (body_file) and returns 0 on success.
retry_check() {
  local name="$1"
  local url="$2"
  local validate_fn="$3"
  local attempt code body_file

  body_file="$(mktemp)"

  for ((attempt = 1; attempt <= SMOKE_MAX_ATTEMPTS; attempt++)); do
    echo "[${name}] attempt ${attempt}/${SMOKE_MAX_ATTEMPTS}: GET ${url}"
    code="$(http_get "${url}" "${body_file}")"

    if [[ "${code}" == "200" ]] && "${validate_fn}" "${body_file}"; then
      echo "[${name}] OK (HTTP ${code})"
      rm -f "${body_file}"
      return 0
    fi

    echo "[${name}] FAIL attempt ${attempt}: HTTP ${code}"
    echo "[${name}] body (truncated): $(truncate_body "${body_file}")"

    if ((attempt < SMOKE_MAX_ATTEMPTS)); then
      sleep "${SMOKE_SLEEP_SECONDS}"
    fi
  done

  rm -f "${body_file}"
  echo "ERROR: [${name}] failed after ${SMOKE_MAX_ATTEMPTS} attempts: ${url}" >&2
  return 1
}

validate_health() {
  local body_file="$1"
  jq -e '
    .status == "ok" and .database == "connected"
  ' "${body_file}" >/dev/null
}

validate_productions() {
  local body_file="$1"
  jq -e '
    (.items | type == "array") and
    (.total | type == "number") and
    (.limit | type == "number") and
    (.offset | type == "number")
  ' "${body_file}" >/dev/null
}

validate_frontend() {
  # Body content is not asserted — any HTTP 200 is enough for liveness.
  return 0
}

retry_check "health" "${BACKEND_PUBLIC_URL}/health" validate_health
retry_check "productions" "${BACKEND_PUBLIC_URL}/api/v1/productions" validate_productions
retry_check "frontend" "${FRONTEND_PUBLIC_URL}/" validate_frontend

echo "All smoke checks passed."
