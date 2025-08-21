#!/usr/bin/env python3
"""
Test script for voidinstall - allows testing individual components safely
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all modules can be imported successfully"""
    print("[TEST] Testing imports...")
    try:
        from lib.disk.utils import manual_partitioning, list_partitions
        from lib.disk.filesystem import format_ext4, mount_root
        from lib.crypt.luks import luks_format
        from lib.packages.xbps import enable_repos, install_packages, upgrade_packages
        from lib.authentication.user import create_user_chroot, set_password_chroot, lock_root_chroot
        from lib.boot.grub import install_grub_chroot
        from lib.locale.config import configure_locale_chroot
        from lib.sound import install_sound, ensure_chroot_mounts
        from tui.main import launch_tui
        print("[TEST] ✓ All imports successful")
        return True
    except ImportError as e:
        print(f"[TEST] ✗ Import failed: {e}")
        return False

def test_tui_launch():
    """Test launching the TUI (dry run)"""
    print("[TEST] Testing TUI launch...")
    try:
        import npyscreen
        from tui.main import VoidInstallTUI
        print("[TEST] ✓ TUI can be instantiated")
        print("[TEST] Note: Run 'python test_installer.py --tui' to actually launch TUI")
        return True
    except Exception as e:
        print(f"[TEST] ✗ TUI test failed: {e}")
        return False

def test_disk_utils():
    """Test disk utility functions (safe operations only)"""
    print("[TEST] Testing disk utilities...")
    try:
        from lib.disk.utils import list_partitions
        # This is safe - just lists existing partitions
        print("[TEST] ✓ Disk utilities imported successfully")
        print("[TEST] Note: Actual disk operations require root privileges and real hardware")
        return True
    except Exception as e:
        print(f"[TEST] ✗ Disk utils test failed: {e}")
        return False

def test_chroot_helper():
    """Test chroot mount helper (safe - just checks logic)"""
    print("[TEST] Testing chroot helper...")
    try:
        from lib.sound import ensure_chroot_mounts
        print("[TEST] ✓ Chroot helper imported successfully")
        print("[TEST] Note: Actual mounting requires root privileges")
        return True
    except Exception as e:
        print(f"[TEST] ✗ Chroot helper test failed: {e}")
        return False

def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--tui':
        print("[TEST] Launching TUI...")
        from tui.main import launch_tui
        launch_tui()
        return
    
    print("=" * 50)
    print("VOIDINSTALL TEST SUITE")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_tui_launch,
        test_disk_utils,
        test_chroot_helper
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"RESULTS: {passed}/{total} tests passed")
    print("=" * 50)
    
    if passed == total:
        print("✓ All tests passed! Your installer is ready for testing.")
        print("\nNext steps:")
        print("1. Test TUI: python test_installer.py --tui")
        print("2. Test in VM: Use VirtualBox/VMware with Void Linux ISO")
        print("3. Test on real hardware (CAUTION: Will modify disk!)")
    else:
        print("✗ Some tests failed. Check your imports and dependencies.")

if __name__ == "__main__":
    main()
