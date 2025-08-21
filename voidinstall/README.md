# VoidInstall - Void Linux TUI Installer

A user-friendly Text User Interface (TUI) installer for Void Linux, inspired by Archinstall. Features full disk encryption, desktop environment selection, sound system configuration, and modular architecture.

## Features

- **Interactive TUI** - Easy-to-use interface built with npyscreen
- **Full Disk Encryption** - LUKS encryption support (no LVM)
- **Desktop Environments** - XFCE, GNOME, KDE, MATE, Cinnamon
- **Sound Systems** - PipeWire or PulseAudio
- **Hardware Auto-Detection** - Automatically detects and installs appropriate drivers
  - CPU microcode (Intel/AMD)
  - Graphics drivers (Intel, AMD, NVIDIA, VMware, generic)
  - Audio firmware (SOF, ALSA)
- **Manual Partitioning** - Use cfdisk, fdisk, or parted for custom layouts
- **Modular Design** - Clean separation of concerns, inspired by Archinstall

## Requirements

- Void Linux live environment (ISO or USB)
- **Working network connection** (installer copies network config to installed system)
- Python 3.6+
- Root privileges (for installation)

## Installation

### 1. Boot Void Linux Live Environment

Download and boot from the [Void Linux live ISO](https://voidlinux.org/download/).

### 2. Install Dependencies

```bash
# Update package database
sudo xbps-install -S

# Install Python and dependencies
sudo xbps-install -y python3 python3-pip git

# Install npyscreen for TUI
pip3 install npyscreen
```

### 3. Get VoidInstall

```bash
# Clone the repository
git clone https://github.com/gautam9981/voidinstall.git
cd voidinstall

# Or download and extract if no git
wget https://github.com/gautam9981/voidinstall/archive/main.zip
unzip main.zip
cd voidinstall-main
```

## Usage

### TUI Mode (Recommended)

Launch the interactive Text User Interface:

```bash
sudo python3 -m tui.main
```

The TUI will guide you through:
1. Hardware detection and driver selection
2. Disk selection
3. Encryption options
4. User creation
5. Desktop environment selection
6. Sound system selection
7. Installation process

### CLI Mode

For automated or scripted installations:

```bash
sudo python3 lib/installer.py
```

### Manual Module Testing

Test individual components before installation:

```bash
# Test imports
python3 -c "from lib.installer import main; print('All modules imported successfully')"

# Test TUI without installing
python3 -c "from tui.main import launch_tui; launch_tui()"

# Test disk utilities (read-only)
python3 -c "from lib.disk.utils import list_partitions; list_partitions('/dev/sda')"
```

## Testing Safely

### Virtual Machine (Recommended)

1. **Set up VM with Void Linux live ISO:**
   - VirtualBox, VMware, or QEMU
   - Allocate at least 2GB RAM, 20GB disk
   - Boot from Void Linux live ISO

2. **Install and run VoidInstall in VM:**
   ```bash
   # Follow installation steps above
   sudo python3 -m tui.main
   ```

### Live USB Testing

1. Create bootable Void Linux USB
2. **Connect to network** (WiFi or Ethernet) in live environment
3. Boot from USB on test hardware
4. Install dependencies and run installer
5. Safe because it's a live environment

## Network Configuration

VoidInstall follows the same approach as Archinstall:

1. **Assumes working network** - You must have internet connectivity in the live environment
2. **Copies network configuration** - Automatically transfers your current network settings to the installed system
3. **Smart network manager selection**:
   - **NetworkManager** for GNOME, KDE, Cinnamon (modern desktop environments)
   - **dhcpcd + wpa_supplicant** for XFCE, MATE, or headless systems
4. **DNS configuration** - Copies `/etc/resolv.conf` from live environment

### Setting up Network in Live Environment

```bash
# For Ethernet (usually automatic)
sudo dhcpcd

# For WiFi
sudo wpa_passphrase "YourSSID" "YourPassword" > /etc/wpa_supplicant/wpa_supplicant.conf
sudo wpa_supplicant -B -i wlan0 -c /etc/wpa_supplicant/wpa_supplicant.conf
sudo dhcpcd wlan0

# Verify connection
ping -c 3 voidlinux.org
```

## Configuration Options

### Disk Encryption

- **LUKS encryption** with user-defined passphrase
- **No LVM** - direct encrypted partition
- **UEFI and BIOS support** - auto-detects boot mode and configures appropriately

### Desktop Environments

- **XFCE4** - Lightweight, traditional desktop
- **GNOME** - Modern, full-featured desktop
- **KDE Plasma** - Feature-rich, customizable
- **MATE** - Traditional GNOME 2 fork
- **Cinnamon** - Modern, user-friendly

### Sound Systems

- **PipeWire** - Modern, low-latency audio (recommended)
- **PulseAudio** - Traditional Linux audio system

### Graphics Drivers

**Auto-Detection Features:**
- **Intel** - Intel integrated graphics with Vulkan support
- **AMD** - AMD graphics with AMDGPU and Vulkan support  
- **NVIDIA** - Proprietary drivers (can be overridden to Nouveau)
- **VMware** - VMware virtualized graphics
- **Generic** - Kernel modesetting (fallback)

**Hardware Detection:**
- Automatically detects graphics hardware via lspci
- Suggests optimal driver based on detected hardware
- Allows manual override if needed
- Installs complete driver stack including Vulkan and VA-API

### CPU Microcode

**Automatic Installation:**
- **Intel** - `intel-ucode` package
- **AMD** - `linux-firmware-amd` package
- Detected via `/proc/cpuinfo` vendor identification

### Audio Firmware

**Smart Detection:**
- **SOF Firmware** - For modern Intel audio (snd_sof module)
- **ALSA Firmware** - For various sound cards requiring firmware
- Based on loaded kernel modules

## Troubleshooting

### Import Errors

```bash
# Ensure you're in the voidinstall directory
cd /path/to/voidinstall

# Check Python path
export PYTHONPATH="$(pwd):$PYTHONPATH"
```

### Permission Errors

```bash
# Ensure running as root
sudo python3 -m tui.main
```

### Missing Dependencies

```bash
# Install missing packages
sudo xbps-install -S python3 python3-pip
pip3 install npyscreen
```

## Warning

**⚠️ This installer will modify disk partitions and install a complete operating system. Always:**

- **Backup important data** before running
- **Test in a virtual machine** first
- **Use on dedicated hardware** or spare drives
- **Understand the risks** of disk partitioning

## Project Structure

```
voidinstall/
├── lib/                    # Core modules
│   ├── authentication/     # User management
│   ├── boot/              # Bootloader (GRUB)
│   ├── crypt/             # LUKS encryption
│   ├── disk/              # Disk operations
│   ├── locale/            # Locale configuration
│   ├── packages/          # Package management (xbps)
│   └── sound.py           # Sound system setup
├── tui/                   # Text User Interface
│   └── main.py           # TUI application
└── README.md             # This file
```
