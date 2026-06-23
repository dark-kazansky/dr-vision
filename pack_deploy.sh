#!/bin/bash
# pack_deploy.sh: Package Doc Intelligence for server deployment
# Creates a production-ready tarball excluding dev artifacts.
set -euo pipefail

GREEN='\033[0;32m'; BLUE='\033[0;34m'; NC='\033[0m'

OUTPUT="drvision-deploy.tar.gz"

echo "════════════════════════════════════════════"
echo "  DR VISION — PACKAGE FOR DEPLOYMENT"
echo "════════════════════════════════════════════"
echo ""

# Remove old archive
[[ -f "$OUTPUT" ]] && rm "$OUTPUT"

echo -e "${BLUE}[INFO]${NC} Creating $OUTPUT..."

tar --exclude='node_modules' \
    --exclude='.nuxt' \
    --exclude='.output' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='.venv' \
    --exclude='.conda' \
    --exclude='.pytest_cache' \
    --exclude='.ruff_cache' \
    --exclude='.hypothesis' \
    --exclude='artifacts' \
    --exclude='dataResult' \
    --exclude='data' \
    --exclude='*.tar.gz' \
    -czf "$OUTPUT" . > /dev/null

echo -e "${GREEN}[OK]${NC} Created $OUTPUT ($(du -h "$OUTPUT" | cut -f1))"
echo ""
echo "Deployment steps:"
echo "  1. scp $OUTPUT user@server:/path/to/deploy/"
echo "  2. tar -xzf $OUTPUT"
echo "  3. cp .env.example .env.prod  (edit with production values)"
echo "  4. docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build"
echo ""
