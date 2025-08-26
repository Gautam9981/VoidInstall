#!/bin/bash

# VoidInstall Native Test Script
# Runs the VoidInstall TUI directly on Void Linux

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VOIDINSTALL_DIR="$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}



echo "=========================================="
echo "    VoidInstall Native Test Script"
echo "=========================================="
echo

# Check if running on Void Linux
if [ ! -f /etc/os-release ] || ! grep -q "void" /etc/os-release; then
    print_warning "This doesn't appear to be Void Linux"
    print_warning "This script is designed for native Void Linux testing"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if running as root (required for partitioning operations)
if [ "$EUID" -ne 0 ]; then
    print_error "This script must be run as root for partitioning operations"
    print_warning "Usage: sudo $0"
    exit 1
fi


# Update xbps package manager (equivalent to Dockerfile step)
print_info "Updating xbps..."
if xbps-install -uy xbps > /dev/null 2>&1; then
    print_success "xbps updated"
else
    print_warning "xbps update failed or not needed"
fi

# Install base system packages (equivalent to Dockerfile step)
print_info "Installing base packages..."
BASE_PACKAGES="python3 python3-pip git nano vim util-linux coreutils bash ncurses iputils sudo"
if xbps-install -Sy $BASE_PACKAGES > /dev/null 2>&1; then
    print_success "Base packages installed"
else
    print_error "Failed to install base packages"
    exit 1
fi

# Install partitioning and filesystem tools (equivalent to Dockerfile step)
print_info "Installing partitioning tools..."
PARTITION_PACKAGES="gptfdisk parted e2fsprogs dosfstools cryptsetup"
if xbps-install -Sy $PARTITION_PACKAGES > /dev/null 2>&1; then
    print_success "Partitioning tools installed"
else
    print_error "Failed to install partitioning tools"
    exit 1
fi

# Install Python TUI packages
print_info "Installing Python TUI packages..."
if python3 -m pip install --break-system-packages textual rich > /dev/null 2>&1; then
    print_success "Python TUI packages installed"
else
    print_warning "Failed to install TUI packages with pip, checking if already available..."
    
    # Check if packages are already available
    if python3 -c "import textual; import rich" 2>/dev/null; then
        print_success "TUI packages already available"
    else
        print_error "TUI packages not available and installation failed"
        print_info "Try manually: python3 -m pip install --break-system-packages textual rich"
        exit 1
    fi
fi

# Verify Python packages are importable (equivalent to Dockerfile step)
print_info "Verifying Python packages..."
if python3 -c "import textual; import rich; print('✓ Textual and Rich imports OK')" 2>/dev/null; then
    print_success "Package verification complete"
else
    print_error "Package verification failed"
    exit 1
fi

# Set up environment variables (equivalent to Dockerfile)
export VOID_INSTALLER_TEST_MODE=1
export TERM=xterm-256color
export PYTHONUNBUFFERED=1
export PYTHONIOENCODING=utf-8
export TEST_DISK="$LOOP_DEVICE"
export PYTHONPATH="$VOIDINSTALL_DIR:$PYTHONPATH"

# Change to the voidinstall directory
cd "$VOIDINSTALL_DIR"

print_info "Available disks:"
lsblk -d -o NAME,SIZE,TYPE,MODEL | grep -E "(disk|loop)"

echo
print_info "Test disk available at: $LOOP_DEVICE"
print_warning "Press Ctrl+C to exit"
echo

# Launch the TUI (with fallback options like docker-test.sh)
print_success "Starting VoidInstall TUI..."


