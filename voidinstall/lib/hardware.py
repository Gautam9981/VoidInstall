"""
Hardware detection utilities for voidinstall - inspired by archinstall
"""
import subprocess
import os
from enum import Enum
from pathlib import Path


class CpuVendor(Enum):
    AuthenticAMD = 'amd'
    GenuineIntel = 'intel'
    Unknown = 'unknown'

    @classmethod
    def get_vendor(cls, name: str) -> 'CpuVendor':
        for vendor in cls:
            if vendor.name == name:
                return vendor
        print(f"[DEBUG] Unknown CPU vendor '{name}' detected.")
        return cls.Unknown

    def get_microcode_package(self) -> str | None:
        """Get the appropriate microcode package for Void Linux"""
        if self == CpuVendor.AuthenticAMD:
            return "linux-firmware-amd"
        elif self == CpuVendor.GenuineIntel:
            return "intel-ucode"
        return None


class GfxDriver(Enum):
    INTEL = "intel"
    AMD = "amd" 
    NVIDIA_PROPRIETARY = "nvidia_proprietary"
    NVIDIA_NOUVEAU = "nvidia_nouveau"
    VMWARE = "vmware"
    GENERIC = "generic"

    def get_void_packages(self) -> list[str]:
        """Get the appropriate graphics packages for Void Linux"""
        match self:
            case GfxDriver.INTEL:
                return [
                    "xorg-server", "xf86-video-intel", "mesa", "mesa-intel-dri",
                    "vulkan-loader", "mesa-vulkan-intel", "libva-intel-driver"
                ]
            case GfxDriver.AMD:
                return [
                    "xorg-server", "xf86-video-amdgpu", "xf86-video-ati", "mesa",
                    "mesa-ati-dri", "vulkan-loader", "mesa-vulkan-radeon", "libva-mesa-driver"
                ]
            case GfxDriver.NVIDIA_PROPRIETARY:
                return [
                    "xorg-server", "nvidia", "nvidia-libs", "nvidia-dkms"
                ]
            case GfxDriver.NVIDIA_NOUVEAU:
                return [
                    "xorg-server", "xf86-video-nouveau", "mesa", "mesa-nouveau-dri",
                    "vulkan-loader", "mesa-vulkan-nouveau"
                ]
            case GfxDriver.VMWARE:
                return [
                    "xorg-server", "xf86-video-vmware", "mesa"
                ]
            case GfxDriver.GENERIC:
                return [
                    "xorg-server", "xf86-video-modesetting", "mesa"
                ]


class HardwareDetection:
    def __init__(self):
        self._cpu_info = None
        self._graphics_devices = None
        self._loaded_modules = None

    @property
    def cpu_info(self) -> dict[str, str]:
        """Get CPU information from /proc/cpuinfo"""
        if self._cpu_info is None:
            cpu_info = {}
            try:
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if line.strip():
                            if ':' in line:
                                key, value = line.split(':', 1)
                                cpu_info[key.strip()] = value.strip()
            except FileNotFoundError:
                pass
            self._cpu_info = cpu_info
        return self._cpu_info

    @property 
    def loaded_modules(self) -> list[str]:
        """Get list of loaded kernel modules"""
        if self._loaded_modules is None:
            modules = []
            try:
                with open('/proc/modules', 'r') as f:
                    for line in f:
                        module = line.split()[0]
                        modules.append(module)
            except FileNotFoundError:
                pass
            self._loaded_modules = modules
        return self._loaded_modules

    @property
    def graphics_devices(self) -> dict[str, str]:
        """Get graphics devices from lspci"""
        if self._graphics_devices is None:
            cards = {}
            try:
                result = subprocess.run(['lspci'], capture_output=True, text=True)
                for line in result.stdout.split('\n'):
                    if 'VGA' in line or '3D' in line:
                        if ':' in line:
                            _, identifier = line.split(':', 1)
                            cards[identifier.strip()] = line
            except (subprocess.SubprocessError, FileNotFoundError):
                pass
            self._graphics_devices = cards
        return self._graphics_devices

    def detect_cpu_vendor(self) -> CpuVendor:
        """Detect CPU vendor"""
        vendor_id = self.cpu_info.get('vendor_id', '')
        return CpuVendor.get_vendor(vendor_id)

    def get_cpu_model(self) -> str:
        """Get CPU model name"""
        return self.cpu_info.get('model name', 'Unknown')

    def detect_microcode_package(self) -> str | None:
        """Detect required microcode package"""
        vendor = self.detect_cpu_vendor()
        return vendor.get_microcode_package()

    def has_nvidia_graphics(self) -> bool:
        """Check if system has NVIDIA graphics"""
        return any('nvidia' in device.lower() for device in self.graphics_devices.keys())

    def has_amd_graphics(self) -> bool:
        """Check if system has AMD graphics"""
        return any('amd' in device.lower() or 'ati' in device.lower() 
                  for device in self.graphics_devices.keys())

    def has_intel_graphics(self) -> bool:
        """Check if system has Intel graphics"""
        return any('intel' in device.lower() for device in self.graphics_devices.keys())

    def is_vm(self) -> bool:
        """Check if running in a virtual machine"""
        vm_indicators = [
            'vmware', 'virtualbox', 'qemu', 'kvm', 'xen', 'hyper-v'
        ]
        
        # Check system vendor
        try:
            with open('/sys/devices/virtual/dmi/id/sys_vendor', 'r') as f:
                vendor = f.read().strip().lower()
                if any(vm in vendor for vm in vm_indicators):
                    return True
        except FileNotFoundError:
            pass

        # Check product name
        try:
            with open('/sys/devices/virtual/dmi/id/product_name', 'r') as f:
                product = f.read().strip().lower()
                if any(vm in product for vm in vm_indicators):
                    return True
        except FileNotFoundError:
            pass

        # Check graphics devices for VM indicators
        for device in self.graphics_devices.keys():
            if any(vm in device.lower() for vm in vm_indicators):
                return True

        return False

    def detect_graphics_driver(self) -> GfxDriver:
        """Auto-detect the best graphics driver"""
        if self.is_vm():
            # Check for specific VM types
            for device in self.graphics_devices.keys():
                if 'vmware' in device.lower():
                    return GfxDriver.VMWARE
            return GfxDriver.GENERIC

        # Physical hardware detection
        if self.has_nvidia_graphics():
            # For NVIDIA, default to proprietary unless user prefers open source
            return GfxDriver.NVIDIA_PROPRIETARY
        elif self.has_amd_graphics():
            return GfxDriver.AMD
        elif self.has_intel_graphics():
            return GfxDriver.INTEL
        else:
            return GfxDriver.GENERIC

    def requires_sof_firmware(self) -> bool:
        """Check if SOF (Sound Open Firmware) is required"""
        return 'snd_sof' in self.loaded_modules

    def requires_alsa_firmware(self) -> bool:
        """Check if ALSA firmware is required"""
        alsa_modules = {
            'snd_asihpi', 'snd_cs46xx', 'snd_darla20', 'snd_darla24',
            'snd_echo3g', 'snd_emu10k1', 'snd_gina20', 'snd_gina24',
            'snd_hda_codec_ca0132', 'snd_hdsp', 'snd_indigo', 'snd_indigodj',
            'snd_indigodjx', 'snd_indigoio', 'snd_indigoiox', 'snd_layla20',
            'snd_layla24', 'snd_mia', 'snd_mixart', 'snd_mona', 'snd_pcxhr',
            'snd_vx_lib'
        }
        
        return any(module in self.loaded_modules for module in alsa_modules)

    def get_recommended_packages(self) -> dict[str, list[str]]:
        """Get all recommended packages based on hardware detection"""
        packages = {
            'microcode': [],
            'graphics': [],
            'audio_firmware': []
        }

        # Microcode
        if microcode_pkg := self.detect_microcode_package():
            packages['microcode'].append(microcode_pkg)

        # Graphics
        gfx_driver = self.detect_graphics_driver()
        packages['graphics'] = gfx_driver.get_void_packages()

        # Audio firmware
        if self.requires_sof_firmware():
            packages['audio_firmware'].append('sof-firmware')
        if self.requires_alsa_firmware():
            packages['audio_firmware'].append('alsa-firmware')

        return packages

    def print_hardware_summary(self):
        """Print a summary of detected hardware"""
        print("\n[HARDWARE] Detected Hardware:")
        print(f"  CPU: {self.get_cpu_model()}")
        print(f"  CPU Vendor: {self.detect_cpu_vendor().value}")
        
        if microcode := self.detect_microcode_package():
            print(f"  Microcode: {microcode}")
        
        print(f"  Graphics Driver: {self.detect_graphics_driver().value}")
        
        if self.graphics_devices:
            print("  Graphics Devices:")
            for device in self.graphics_devices.keys():
                print(f"    - {device}")
        
        if self.is_vm():
            print("  Running in Virtual Machine")
        
        if self.requires_sof_firmware():
            print("  Requires SOF firmware")
        if self.requires_alsa_firmware():
            print("  Requires ALSA firmware")


# Global instance for easy access
hardware = HardwareDetection()
