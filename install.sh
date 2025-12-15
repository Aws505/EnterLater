#!/bin/bash
# EnterLater installation script
# This script installs EnterLater for the current user

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}EnterLater Installer${NC}"
echo "====================="
echo

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Define installation paths
INSTALL_DIR="$HOME/EnterLater"
DESKTOP_FILE="$HOME/.local/share/applications/EnterLater.desktop"

# Check for required system dependencies
echo "Checking dependencies..."
if ! command -v xdotool &> /dev/null; then
    echo "WARNING: xdotool is not installed."
    echo "Install it with: sudo apt install xdotool"
    echo
fi

if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 is not installed."
    exit 1
fi

# Check for Python dependencies
echo "Checking Python dependencies..."
python3 -c "import pystray, PIL" 2>/dev/null || {
    echo "WARNING: pystray and/or Pillow not installed."
    echo "Tray icon features will be disabled."
    echo "Install with: pip install pystray pillow"
    echo
}

# Create installation directory if it doesn't exist
if [ "$SCRIPT_DIR" != "$INSTALL_DIR" ]; then
    echo "Copying files to $INSTALL_DIR..."
    mkdir -p "$INSTALL_DIR"
    cp "$SCRIPT_DIR/EnterLater.py" "$INSTALL_DIR/"
    cp "$SCRIPT_DIR/enterlater.png" "$INSTALL_DIR/"
    if [ -f "$SCRIPT_DIR/README.md" ]; then
        cp "$SCRIPT_DIR/README.md" "$INSTALL_DIR/"
    fi
    if [ -f "$SCRIPT_DIR/LICENSE" ]; then
        cp "$SCRIPT_DIR/LICENSE" "$INSTALL_DIR/"
    fi
    chmod +x "$INSTALL_DIR/EnterLater.py"
else
    echo "Already in installation directory."
    chmod +x "$INSTALL_DIR/EnterLater.py"
fi

# Create .local/share/applications directory if it doesn't exist
mkdir -p "$(dirname "$DESKTOP_FILE")"

# Create the desktop entry file with user-specific paths
echo "Creating desktop launcher..."
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Type=Application
Name=EnterLater
Comment=Fire Enter (or text + Enter) into a window at a specific time
Exec=python3 $INSTALL_DIR/EnterLater.py
Icon=$INSTALL_DIR/enterlater.png
Terminal=false
Categories=Utility;
StartupNotify=false
EOF

# Update desktop database
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi

echo
echo -e "${GREEN}✓ Installation complete!${NC}"
echo
echo "You can now:"
echo "  1. Launch from your application menu (search for 'EnterLater')"
echo "  2. Run from terminal: python3 $INSTALL_DIR/EnterLater.py"
echo
echo "Installation location: $INSTALL_DIR"
echo "Desktop file: $DESKTOP_FILE"
