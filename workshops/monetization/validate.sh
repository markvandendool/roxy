#!/bin/bash
# Monetization Workshop - Quick Validation Script
# Verifies all components are in place and ready to use

WORKSHOP_DIR="$HOME/.roxy/workshops/monetization"
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "Monetization Workshop - System Check"
echo "========================================"
echo ""

# Check workshop structure
echo "📂 Directory Structure..."
if [ -d "$WORKSHOP_DIR" ]; then
    echo -e "${GREEN}✓${NC} Workshop directory exists"
else
    echo -e "${RED}✗${NC} Workshop directory missing"
    exit 1
fi

# Check required directories
REQUIRED_DIRS=(
    "brain/strategies"
    "brain/playbooks"
    "products"
    "content/engines"
    "automation/n8n"
    "automation/obs"
    "analytics"
    "grants"
    "ops"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$WORKSHOP_DIR/$dir" ]; then
        echo -e "${GREEN}✓${NC} $dir"
    else
        echo -e "${RED}✗${NC} $dir missing"
    fi
done

echo ""
echo "📄 Core Documents..."
REQUIRED_DOCS=(
    "00_INDEX.md"
    "README.md"
    "brain/playbooks/00_executive-summary.md"
    "brain/playbooks/01_revenue-playbook.md"
    "brain/strategies/01_asset-inventory.md"
    "grants/00_INDEX.md"
    "ops/RUNBOOK.md"
    "ops/TROUBLESHOOTING.md"
    "products/BUILD.md"
    "content/PIPELINE.md"
)

for doc in "${REQUIRED_DOCS[@]}"; do
    if [ -f "$WORKSHOP_DIR/$doc" ]; then
        echo -e "${GREEN}✓${NC} $doc"
    else
        echo -e "${RED}✗${NC} $doc missing"
    fi
done

echo ""
echo "🛠️ Scripts & Tools..."
REQUIRED_SCRIPTS=(
    "products/package_products.sh"
    "content/engines/faceless_video_engine.py"
    "analytics/init-tracker.sh"
    "analytics/generate-weekly-report.sh"
)

for script in "${REQUIRED_SCRIPTS[@]}"; do
    if [ -f "$WORKSHOP_DIR/$script" ]; then
        if [ -x "$WORKSHOP_DIR/$script" ]; then
            echo -e "${GREEN}✓${NC} $script (executable)"
        else
            echo -e "${YELLOW}!${NC} $script (not executable)"
        fi
    else
        echo -e "${RED}✗${NC} $script missing"
    fi
done

echo ""
echo "🔗 External Dependencies..."

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION"
else
    echo -e "${RED}✗${NC} Python not found"
fi

# Check ffmpeg
if command -v ffmpeg &> /dev/null; then
    echo -e "${GREEN}✓${NC} ffmpeg"
else
    echo -e "${YELLOW}!${NC} ffmpeg not installed (needed for video generation)"
fi

# Check espeak
if command -v espeak &> /dev/null; then
    echo -e "${GREEN}✓${NC} espeak (TTS)"
else
    echo -e "${YELLOW}!${NC} espeak not installed (needed for text-to-speech)"
fi

# Check OBS
if command -v obs &> /dev/null; then
    echo -e "${GREEN}✓${NC} OBS Studio"
else
    echo -e "${YELLOW}!${NC} OBS not installed (optional, for high-quality recording)"
fi

# Check Docker
if command -v docker &> /dev/null; then
    echo -e "${GREEN}✓${NC} Docker"
else
    echo -e "${YELLOW}!${NC} Docker not installed (optional, for n8n)"
fi

echo ""
echo "🔗 Roxy Infrastructure..."

# Check Roxy components
ROXY_COMPONENTS=(
    "$HOME/.roxy/obs_controller.py"
    "$HOME/.roxy/mcp/mcp_n8n.py"
    "$HOME/.roxy/mcp/mcp_obs.py"
)

for component in "${ROXY_COMPONENTS[@]}"; do
    if [ -f "$component" ]; then
        echo -e "${GREEN}✓${NC} $(basename $component)"
    else
        echo -e "${YELLOW}!${NC} $(basename $component) not found"
    fi
done

echo ""
echo "🎬 8K Theater Integration..."
THEATER_LINK="$WORKSHOP_DIR/automation/obs/theater-scenes"
if [ -L "$THEATER_LINK" ]; then
    TARGET=$(readlink -f "$THEATER_LINK")
    if [ -d "$TARGET" ]; then
        echo -e "${GREEN}✓${NC} Theater scenes linked → $TARGET"
    else
        echo -e "${RED}✗${NC} Theater scenes link broken"
    fi
else
    echo -e "${YELLOW}!${NC} Theater scenes not linked"
fi

echo ""
echo "📊 File Count..."
FILE_COUNT=$(find "$WORKSHOP_DIR" -type f | wc -l)
echo "Total files: $FILE_COUNT"

MD_COUNT=$(find "$WORKSHOP_DIR" -name "*.md" | wc -l)
echo "Documentation: $MD_COUNT markdown files"

SCRIPT_COUNT=$(find "$WORKSHOP_DIR" \( -name "*.sh" -o -name "*.py" \) | wc -l)
echo "Scripts: $SCRIPT_COUNT executable files"

echo ""
echo "========================================"
echo "Next Steps:"
echo "========================================"
echo "1. Read: $WORKSHOP_DIR/README.md"
echo "2. Initialize analytics: $WORKSHOP_DIR/analytics/init-tracker.sh"
echo "3. Package first product: $WORKSHOP_DIR/products/package_products.sh"
echo "4. Generate first video: cd $WORKSHOP_DIR/content/engines && python3 faceless_video_engine.py"
echo ""
echo "Documentation: $WORKSHOP_DIR/00_INDEX.md"
echo ""
