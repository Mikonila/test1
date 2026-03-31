#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   DUCKDNS_SUBDOMAIN=myanxietyapp
#   DUCKDNS_TOKEN=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
#   ./deploy/duckdns-update.sh

: "${DUCKDNS_SUBDOMAIN:?Missing DUCKDNS_SUBDOMAIN}"
: "${DUCKDNS_TOKEN:?Missing DUCKDNS_TOKEN}"

curl -s "https://www.duckdns.org/update?domains=${DUCKDNS_SUBDOMAIN}&token=${DUCKDNS_TOKEN}&ip="
echo

echo "DuckDNS updated. Domain: ${DUCKDNS_SUBDOMAIN}.duckdns.org"
