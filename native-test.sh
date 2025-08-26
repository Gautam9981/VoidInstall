#!/bin/bash

# VoidInstall Native Test Script
# Runs the VoidInstall TUI directly on Void Linux
# Merges functionality from Dockerfile and docker-test.sh for native environment

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

# Global variables for loopback device management
LOOP_DEVICE=""
LOOP_FILE="./test_disk.img"
LOOP_SIZE="30G"

# Enhanced cleanup function
cleanup() {
    print_info "Cleaning up resources..."
    cleanup_loopback
}

# Function to clean up loopback device
cleanup_loopback() {
    if [ ! -z "$LOOP_DEVICE" ] && [ -e "$LOOP_DEVICE" ]; then
        print_info "Detaching loopback device $LOOP_DEVICE"
        sudo losetup -d "$LOOP_DEVICE" 2>/dev/null || true
    fi
    
    # Optionally remove the disk image file
    if [ -f "$LOOP_FILE" ]; then
        read -p "Remove test disk image file ($LOOP_FILE)? (y/N): " remove_file
        if [[ "$remove_file" =~ ^[Yy] ]]; then
            print_info "Removing test disk image file"
            rm -f "$LOOP_FILE"
        fi
    fi
}

# Function to create loopback device
create_loopback_device() {
    print_info "Setting up 30GB test disk as loopback device..."
    
    # Check if we already have a loop device
    if [ ! -z "$LOOP_DEVICE" ] && [ -e "$LOOP_DEVICE" ]; then
        print_success "Loopback device already exists: $LOOP_DEVICE"
        return 0
    fi
    
    # Create disk image file if it doesn't exist
    if [ ! -f "$LOOP_FILE" ]; then
        print_info "Creating 30GB disk image file: $LOOP_FILE"
        print_warning "This may take a few moments..."
        
        # Create sparse file (doesn't actually allocate 30GB immediately)
        if ! dd if=/dev/zero of="$LOOP_FILE" bs=1 count=0 seek=30G 2>/dev/null; then
            print_error "Failed to create disk image file"
            return 1
        fi
        
        print_success "Disk image file created successfully"
    else
        print_info "Using existing disk image file: $LOOP_FILE"
    fi
    
    # Set up loopback device
    print_info "Setting up loopback device..."
    LOOP_DEVICE=$(sudo losetup --find --show "$LOOP_FILE")
    
    if [ $? -eq 0 ] && [ ! -z "$LOOP_DEVICE" ]; then
        print_success "Loopback device created: $LOOP_DEVICE"
        
        # Show device info
        print_info "Device information:"
        sudo fdisk -l "$LOOP_DEVICE" 2>/dev/null || echo "  Size: 30GB (unpartitioned)"
        
        return 0
    else
        print_error "Failed to create loopback device"
        return 1
    fi
}

# Function to show loopback device info
show_loopback_info() {
    if [ ! -z "$LOOP_DEVICE" ] && [ -e "$LOOP_DEVICE" ]; then
        echo ""
        print_info "Test Disk Information:"
        echo "  Device: $LOOP_DEVICE"
        echo "  Image File: $LOOP_FILE"
        echo "  Size: $LOOP_SIZE"
        echo ""
        print_info "Current partition table:"
        sudo fdisk -l "$LOOP_DEVICE" 2>/dev/null || echo "  No partitions (blank disk)"
        echo ""
    fi
}

# Set trap for cleanup
trap cleanup EXIT

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


