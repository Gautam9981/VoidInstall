"""
Core installer logic for voidinstall (Void Linux)
Coordinates all install steps using modular components.
"""
from lib.disk.utils import manual_partitioning, list_partitions
from lib.disk.filesystem import format_ext4, mount_root
from lib.crypt.luks import luks_format
from lib.packages.xbps import enable_repos, install_packages, upgrade_packages
from lib.authentication.user import create_user_chroot, set_password_chroot, lock_root_chroot
from lib.boot.grub import install_grub_chroot

def run_install_flow():
	# 1. Manual partitioning
	manual_partitioning()
	disk = input("Enter disk (e.g., /dev/sda) to list partitions: ")
	list_partitions(disk)
	root_part = input("Enter root partition (e.g., /dev/sda1): ")

	# 2. Encryption (optional)
	encrypt = input("Encrypt root partition with LUKS? (y/N): ").lower() == 'y'
	if encrypt:
		luks_mapper = luks_format(root_part)
		root_device = luks_mapper
	else:
		root_device = root_part

	# 3. Format and mount
	format_ext4(root_device)
	mount_root(root_device)

	# 4. Enable repos and install base system
	enable_repos()
	install_packages("/mnt", "base-system", "linux", "vim", "grub-x86_64-efi", "sudo", "dhcpcd")
	upgrade_packages()

	# 5. User setup
	username = input("Enter username to create: ")
	create_user_chroot(username)
	set_password_chroot(username)
	lock_root_chroot()

	# 6. Bootloader
	install_grub_chroot()

	print("[INSTALL] Void Linux installation complete!")
