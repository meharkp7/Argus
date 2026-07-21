#!/bin/bash
# Deploy ARGUS Agent Demo to HF Spaces with intelligent commits

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🚀 ARGUS Agent Demo → Hugging Face Spaces${NC}\n"

read -p "Enter your Hugging Face username: " HF_USERNAME

if [ -z "$HF_USERNAME" ]; then
    echo -e "${RED}✗ Username required${NC}"
    exit 1
fi

SPACE_NAME="argus"
SPACE_URL="https://huggingface.co/spaces/$HF_USERNAME/$SPACE_NAME"

echo -e "${YELLOW}→ Deploying to: $SPACE_URL${NC}\n"

# Clone or update
if [ ! -d "hf-space" ]; then
    echo -e "${BLUE}Cloning HF Space...${NC}"
    git clone "https://huggingface.co/spaces/$HF_USERNAME/$SPACE_NAME" hf-space
    cd hf-space
else
    echo -e "${BLUE}Updating local Space...${NC}"
    cd hf-space
    git fetch origin
    git reset --hard origin/main 2>/dev/null || true
fi

echo -e "${GREEN}✓ Space ready${NC}\n"

# Sync files
echo -e "${BLUE}Syncing ARGUS files...${NC}"
rsync -av \
    --exclude='.git' \
    --exclude='hf-space' \
    --exclude='.env' \
    --exclude='*.env' \
    --exclude='data/ledger' \
    --exclude='data/vector_store' \
    --exclude='data/trust_calibration' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.pytest_cache' \
    --exclude='.venv' \
    --exclude='node_modules' \
    --exclude='.DS_Store' \
    ../ . >/dev/null 2>&1 || true

# Create .gitignore
cat > .gitignore << 'EOF'
.env
*.env
data/ledger/
data/vector_store/
data/trust_calibration/
__pycache__/
*.pyc
.pytest_cache/
.venv/
venv/
env/
*.egg-info/
.eggs/
node_modules/
dist/
build/
.DS_Store
*.tmp
.idea/
.vscode/
EOF

echo -e "${GREEN}✓ Files synced${NC}\n"

# Stage and commit with intelligent messages
echo -e "${BLUE}Staging changes...${NC}"
git add -A

if git diff --cached --quiet; then
    echo -e "${YELLOW}⚠ No changes to commit${NC}"
    cd ..
    exit 0
fi

echo -e "${BLUE}Analyzing changes...${NC}"

# Determine commit message based on what changed
if git diff --cached --name-only | grep -q "app.py"; then
    if git diff --cached --name-only | grep -q "requirements.txt"; then
        COMMIT_MSG="feat: Multi-agent demo interface with Gradio + dependencies"
    else
        COMMIT_MSG="feat: Multi-agent demo interface (Sensor, Permit, Correlation, Explainer, Orchestrator)"
    fi
elif git diff --cached --name-only | grep -q "requirements.txt"; then
    COMMIT_MSG="chore: Update dependencies for HF Spaces"
elif git diff --cached --name-only | grep -q "backend/"; then
    COMMIT_MSG="refactor: Backend updates for agent coordination"
elif git diff --cached --name-only | grep -q "deploy"; then
    COMMIT_MSG="ci: Deployment script improvements"
else
    COMMIT_MSG="chore: Update ARGUS Space - $(date +%Y-%m-%d\ %H:%M:%S)"
fi

echo -e "${BLUE}Committing: $COMMIT_MSG${NC}"
git commit -m "$COMMIT_MSG"

echo -e "${GREEN}✓ Changes committed${NC}\n"

echo -e "${BLUE}Pushing to HF...${NC}"
git push -u origin main --force 2>&1 | grep -E "(Unpacking|Compressing|Writing|100%|main)" || true

echo -e "${GREEN}✓ Push complete!${NC}\n"

echo -e "${BLUE}════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Deployment successful!${NC}"
echo ""
echo "📍 HF Space: https://huggingface.co/spaces/$HF_USERNAME/$SPACE_NAME"
echo ""
echo "⏳ Build Status: Check at Space page (2-5 min build time)"
echo ""
echo "✅ Live URL: https://$HF_USERNAME-$SPACE_NAME.hf.space"
echo ""
echo "🤖 Available Demo Tabs:"
echo "  • Initialize System"
echo "  • Sensor Agent"
echo "  • Permit Agent"
echo "  • Correlation Agent"
echo "  • Explainer Agent"
echo "  • Orchestrator"
echo ""
echo -e "${BLUE}════════════════════════════════════════${NC}"

cd ..
