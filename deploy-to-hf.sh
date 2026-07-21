#!/bin/bash
# Deploy ARGUS to HF Spaces with Gradio

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🚀 ARGUS → Hugging Face Spaces (Gradio)${NC}\n"

read -p "Enter your Hugging Face username: " HF_USERNAME

if [ -z "$HF_USERNAME" ]; then
    echo -e "${RED}✗ Username required${NC}"
    exit 1
fi

SPACE_NAME="argus"
SPACE_URL="https://huggingface.co/spaces/$HF_USERNAME/$SPACE_NAME"

echo -e "${YELLOW}→ Space: $SPACE_URL${NC}\n"

# Clone or update
if [ ! -d "hf-space" ]; then
    echo -e "${BLUE}Cloning HF Space...${NC}"
    git clone "https://huggingface.co/spaces/$HF_USERNAME/$SPACE_NAME" hf-space
    cd hf-space
else
    echo -e "${BLUE}Updating HF Space...${NC}"
    cd hf-space
    git pull origin main 2>/dev/null || true
fi

echo -e "${GREEN}✓ Ready${NC}\n"

# Copy files
echo -e "${BLUE}Syncing ARGUS files...${NC}"
rsync -av --exclude='.git' --exclude='hf-space' --exclude='.env' --exclude='data' ../ . >/dev/null 2>&1 || true

# Create .gitignore
cat > .gitignore << 'EOF'
.env
*.env
data/ledger/*
data/vector_store/*
data/trust_calibration/*
__pycache__/
*.pyc
.pytest_cache/
.venv/
*.egg-info/
node_modules/
dist/
build/
.DS_Store
*.tmp
EOF

echo -e "${GREEN}✓ Files synced${NC}\n"

# Git operations with proper commits
echo -e "${BLUE}Staging changes...${NC}"
git add -A

echo -e "${BLUE}Checking for changes...${NC}"
if git diff --cached --quiet; then
    echo -e "${YELLOW}⚠ No changes to commit${NC}"
else
    echo -e "${BLUE}Committing...${NC}"
    git commit -m "Deploy ARGUS Gradio app to HF Spaces - $(date +%Y-%m-%d\ %H:%M:%S)"
    echo -e "${GREEN}✓ Changes committed${NC}\n"
fi

echo -e "${BLUE}Pushing to HF...${NC}"
git push -u origin main --force

echo -e "${GREEN}✓ Push complete!${NC}\n"

echo -e "${BLUE}════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo "📍 Your Space: https://huggingface.co/spaces/$HF_USERNAME/$SPACE_NAME"
echo ""
echo "⏳ Build Status: Watch at $SPACE_URL"
echo ""
echo "✅ Live URL: https://$HF_USERNAME-$SPACE_NAME.hf.space"
echo ""
echo -e "${BLUE}════════════════════════════════════════${NC}"

cd ..
