# VoidInstall: Interactive Void Linux Installer

VoidInstall is a modern, interactive, and user-friendly installer for Void Linux, inspired by Archinstall. It automates disk partitioning, hardware detection, user setup, desktop environment installation, and more—all from a single script.

## Features
- Auto/manual disk partitioning (UEFI & BIOS support)
- Force unmounts and wipes disks safely
- Hardware detection (CPU, GPU, WiFi, Bluetooth)
- Installs microcode, drivers, and firmware as needed
- User creation with sudo setup
- Desktop environment selection (XFCE, GNOME, KDE, or none)
- Sound system setup (ALSA, PulseAudio, PipeWire)
- Bootloader installation (GRUB, UEFI/BIOS aware)
- Colorful, clear, and interactive terminal UI
- Dependency checking and auto-installation

## Usage
1. **Boot into a Void Linux live environment** (with internet access).
2. **Run as root:**
   ```bash
      python3 voidinstall.py
   ```
3. **Follow the prompts** for disk selection, partitioning, user setup, desktop, etc.

## Requirements
- Void Linux live ISO (recommended)
- Internet connection (for package installation)
- Python 3

The script will check for and install any missing dependencies automatically.

## Notes
- All data on the selected disk will be erased during auto-partitioning.
- For UEFI systems, an EFI partition (FAT32, 512M+) is required.
- For BIOS systems, only root (ext4) and optional swap are required.
- The installer will set up all necessary chroot mounts and unmounts automatically.

## Troubleshooting
- If you cancel the install, the script will force unmount all partitions and clean up before retrying.
- If you encounter issues, check the output for error messages and ensure you are running from a Void Linux live environment.

