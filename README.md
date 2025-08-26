# VoidInstall
This is based off of archinstall (https://github.com/archlinux/archinstall)

# VoidInstall - Void Linux TUI Installer

A user-friendly Text User Interface (TUI) installer for Void Linux, inspired by Archinstall. Features full disk encryption, desktop environment selection, sound system configuration, and modular architecture.

## Features

- **Interactive TUI** - Easy-to-use interface built with textual + rich
- **Full Disk Encryption** - LUKS encryption support (no LVM)
- **Desktop Environments** - XFCE, GNOME, KDE, MATE, Cinnamon
- **Sound Systems** - PipeWire or PulseAudio
- **Graphics Drivers** - Intel, AMD, NVIDIA, VMware, generic modesetting
- **Manual Partitioning** - Use cfdisk, fdisk, or parted for custom layouts
- **Modular Design** - Clean separation of concerns, inspired by Archinstall

## Requirements

- Void Linux live environment (ISO or USB)
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
pip3 install python3-textual
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
1. Disk selection
2. Encryption options
3. User creation
4. Desktop environment selection
5. Sound system selection
6. Graphics driver selection
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
2. Boot from USB on test hardware
3. Install dependencies and run installer
4. Safe because it's a live environment

## Configuration Options

### Disk Encryption

- **LUKS encryption** with user-defined passphrase
- **No LVM** - direct encrypted partition
- Supports both UEFI and BIOS systems

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

- **Intel** - Intel integrated graphics (`xf86-video-intel*`)
- **AMD** - AMD graphics (`xf86-video-amdgpu*`)
- **NVIDIA** - NVIDIA proprietary drivers (`nvidia*`)
- **VMware** - VMware virtualized graphics
- **Generic** - Kernel modesetting (fallback)

## Warning

**⚠️ This installer will modify disk partitions and install a complete operating system. Always:**

- **Backup important data** before running
- **Test in a virtual machine** first
- **Use on dedicated hardware** or spare drives
- **Understand the risks** of disk partitioning


