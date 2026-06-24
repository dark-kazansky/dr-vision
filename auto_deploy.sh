#!/bin/bash
# auto_deploy.sh: Automated deployment to remote server
# Packages, uploads, and deploys via Docker Compose.
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; BLUE='\033[0;34m'; NC='\033[0m'

SERVER="daido-server"
DEPLOY_DIR="~/doc-intelligence-prod"
TAR_FILE="drvision-deploy.tar.gz"

echo "════════════════════════════════════════════"
echo "  DR VISION — AUTOMATED DEPLOYMENT"
echo "  Target: $SERVER:$DEPLOY_DIR"
echo "════════════════════════════════════════════"
echo ""

# Step 1: Package
echo -e "${BLUE}[1/4]${NC} Packaging source code..."
chmod +x pack_deploy.sh
./pack_deploy.sh > /dev/null || { echo -e "${RED}[FAIL]${NC} Packaging failed"; exit 1; }
echo -e "${GREEN}[OK]${NC} Package created"

# Step 2: Prepare remote directory
echo -e "${BLUE}[2/4]${NC} Preparing server directory..."
ssh -o BatchMode=yes "$SERVER" "mkdir -p $DEPLOY_DIR" \
    || { echo -e "${RED}[FAIL]${NC} SSH connection failed"; exit 1; }

# Step 3: Upload
echo -e "${BLUE}[3/4]${NC} Uploading to server..."
cat "$TAR_FILE" | ssh -o BatchMode=yes "$SERVER" "cat > $DEPLOY_DIR/$TAR_FILE" \
    || { echo -e "${RED}[FAIL]${NC} Upload failed"; exit 1; }
echo -e "${GREEN}[OK]${NC} Upload complete"

# Step 4: Deploy
echo -e "${BLUE}[4/4]${NC} Extracting and starting services..."
ssh -o BatchMode=yes "$SERVER" "cd $DEPLOY_DIR && \
    tar -xzf $TAR_FILE && \
    if [ ! -f .env.prod ]; then \
        cp .env.example .env.prod; \
        echo 'Created .env.prod from template — review before production use'; \
    fi && \
    docker compose -f docker-compose.prod.yml --env-file .env.prod down && \
    docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build" \
    || { echo -e "${RED}[FAIL]${NC} Remote deployment failed"; exit 1; }

echo ""
echo "════════════════════════════════════════════"
echo -e "${GREEN}  DEPLOYMENT COMPLETE${NC}"
echo "  Server: $SERVER"
echo "════════════════════════════════════════════"
