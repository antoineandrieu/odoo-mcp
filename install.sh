#!/bin/bash
# Odoo MCP Server - Installation Script
# This script automates the installation and configuration process

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════╗"
echo "║   Odoo MCP Server - Installation Script       ║"
echo "╚════════════════════════════════════════════════╝"
echo -e "${NC}"

# Step 1: Check Python version
echo -e "${YELLOW}Step 1: Checking Python version...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    
    if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 10 ]; then
        echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"
    else
        echo -e "${RED}✗ Python 3.10+ required, found $PYTHON_VERSION${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ Python 3 not found. Please install Python 3.10 or higher.${NC}"
    exit 1
fi

# Step 2: Create virtual environment
echo -e "\n${YELLOW}Step 2: Creating virtual environment...${NC}"
if [ -d "$SCRIPT_DIR/.venv" ]; then
    echo -e "${YELLOW}Virtual environment already exists.${NC}"
    read -p "Do you want to recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$SCRIPT_DIR/.venv"
        python3 -m venv "$SCRIPT_DIR/.venv"
        echo -e "${GREEN}✓ Virtual environment recreated${NC}"
    fi
else
    python3 -m venv "$SCRIPT_DIR/.venv"
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Step 3: Activate virtual environment and install
echo -e "\n${YELLOW}Step 3: Installing dependencies...${NC}"
source "$SCRIPT_DIR/.venv/bin/activate"
pip install --upgrade pip > /dev/null 2>&1
pip install -e "$SCRIPT_DIR" > /dev/null 2>&1
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Step 4: Verify installation
echo -e "\n${YELLOW}Step 4: Verifying installation...${NC}"
if python3 -c "import odoo_mcp" 2>/dev/null; then
    echo -e "${GREEN}✓ Package installed successfully${NC}"
else
    echo -e "${RED}✗ Package installation failed${NC}"
    exit 1
fi

# Step 5: Configuration
echo -e "\n${YELLOW}Step 5: Configuration${NC}"
echo "Choose configuration method:"
echo "  1) Interactive configuration (recommended)"
echo "  2) Create .env file manually"
echo "  3) Configure later"
read -p "Enter choice (1-3): " -n 1 -r
echo

case $REPLY in
    1)
        echo -e "\n${BLUE}Running configuration helper...${NC}"
        python3 "$SCRIPT_DIR/configure.py"
        ;;
    2)
        if [ ! -f "$SCRIPT_DIR/.env" ]; then
            cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
            echo -e "${GREEN}✓ Created .env file from template${NC}"
            echo -e "${YELLOW}Please edit .env with your Odoo credentials:${NC}"
            echo "  nano $SCRIPT_DIR/.env"
        else
            echo -e "${YELLOW}.env file already exists${NC}"
        fi
        ;;
    3)
        echo -e "${YELLOW}Configuration skipped. Run ./configure.py when ready.${NC}"
        ;;
    *)
        echo -e "${YELLOW}Invalid choice. Configuration skipped.${NC}"
        ;;
esac

# Step 6: Installation complete
echo -e "\n${GREEN}"
echo "╔════════════════════════════════════════════════╗"
echo "║        Installation Complete! ✓                ║"
echo "╚════════════════════════════════════════════════╝"
echo -e "${NC}"

echo "Next steps:"
echo ""
echo "1. ${BLUE}Configure Claude Desktop${NC}"
echo "   Run: ${YELLOW}python3 configure.py${NC} (if not already done)"
echo ""
echo "2. ${BLUE}Add configuration to Claude Desktop config file:${NC}"
if [[ "$OSTYPE" == "darwin"* ]]; then
    CONFIG_PATH="~/Library/Application Support/Claude/claude_desktop_config.json"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    CONFIG_PATH="%APPDATA%\\Claude\\claude_desktop_config.json"
else
    CONFIG_PATH="~/.config/Claude/claude_desktop_config.json"
fi
echo "   File: ${YELLOW}${CONFIG_PATH}${NC}"
echo ""
echo "3. ${BLUE}Restart Claude Desktop${NC}"
echo ""
echo "4. ${BLUE}Test the connection${NC}"
echo "   Ask Claude: \"Can you ping the Odoo server?\""
echo ""
echo "For more help, see: ${YELLOW}INSTALL.md${NC}"
echo ""

# Deactivate virtual environment
deactivate 2>/dev/null || true

echo -e "${GREEN}Happy coding! 🚀${NC}"
