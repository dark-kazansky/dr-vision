#!/usr/bin/env bash
# Mirror the monolith's shared Python packages into the msbe shared library.
#
# Goal: the monolith and msbe import the same code, so endpoint contracts
# can never drift. Run after touching anything under backend/{agents,core,
# functions,config}/.
#
# Usage:
#   bash msbe/sync_shared.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${ROOT}/backend"
DST="${ROOT}/msbe/shared/src"

PACKAGES=(agents core functions config)

echo "Syncing shared packages from ${SRC} → ${DST}"

for pkg in "${PACKAGES[@]}"; do
  if [ ! -d "${SRC}/${pkg}" ]; then
    echo "  skip: ${SRC}/${pkg} (not found)"
    continue
  fi
  rm -rf "${DST}/${pkg}"
  mkdir -p "${DST}/${pkg}"
  # Copy *.py only — exclude __pycache__, *.pyc, *.bak, and .gitkeep.
  ( cd "${SRC}/${pkg}" && find . -type f -name '*.py' -print0 ) \
    | ( cd "${SRC}/${pkg}" && tar --null -cf - -T - ) \
    | ( cd "${DST}/${pkg}" && tar -xf - )
  echo "  synced ${pkg}/"
done

# Copy the YAML config so the synced Config class can load defaults if a
# service does not bring its own.
mkdir -p "${DST}/config"
if [ -f "${SRC}/config/settings.yaml" ]; then
  cp "${SRC}/config/settings.yaml" "${DST}/config/settings.yaml"
  echo "  synced config/settings.yaml"
fi

echo "Done."
