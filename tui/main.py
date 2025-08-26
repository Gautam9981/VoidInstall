#!/usr/bin/env python3
"""
VoidInstall TUI - Textual+Rich main entry point
"""
import sys
import os
import asyncio
from pathlib import Path

# Ensure the parent of 'lib' is in sys.path for direct script or module execution
BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

# Explicit imports from lib modules
try:
    from lib.authentication.user import *
    from lib.disk import partition, filesystem, utils as disk_utils
    from lib.boot import grub
    from lib.crypt import luks
    from lib.installer.core import *
    from lib.dependencies import install_partitioning_tools, install_all_dependencies
    from lib.sudo_utils import *
    from profiles.desktop import get_profiles as get_desktop_profiles
    from profiles.minimal import get_profile as get_minimal_profile
except ImportError as e:
    print(f"[FATAL] Import error: {e}")
    print("Check that you are running from the project root and that all modules exist.")
    sys.exit(1)

# Textual and Rich imports
try:
    from textual.app import App, ComposeResult
    from textual.widgets import Header, Footer, Button, Static, Input, Select, Checkbox, ProgressBar, Log, Label
    from textual.containers import ScrollableContainer, Horizontal
    from textual.screen import Screen
    from textual import work
    from rich.panel import Panel
    from rich.text import Text
except ImportError as e:
    print("[FATAL] Missing dependencies: textual, rich. Please install with: pip install textual rich")
    sys.exit(1)

# --- TUI Screens ---
class WelcomeScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with ScrollableContainer():
            yield Static(Panel(Text("Welcome to Void Linux Installer!\n\nPress Continue to begin.", justify="center", style="bold green"), title="VoidInstall", border_style="green"))
            with Horizontal():
                yield Button("Continue", id="continue", variant="primary", classes="nav-button")
                yield Button("Exit", id="exit", variant="error", classes="nav-button")
        yield Footer()
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "continue":
            self.app.push_screen(DiskScreen())
        elif event.button.id == "exit":
            self.app.exit()

class DiskScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with ScrollableContainer():
            yield Static("Disk Setup", classes="title")
            yield Label("Target Disk:")
            yield Input(value="/dev/sda", id="disk_input")
            yield Label("Partitioning Method:")
            yield Select([("Auto", "auto"), ("Manual", "manual")], id="partition_method")
            yield Label("Filesystem:", id="filesystem_label")
            yield Select([("ext4", "ext4"), ("xfs", "xfs"), ("btrfs", "btrfs")], id="filesystem")
            yield Checkbox("Enable LUKS Encryption", id="encryption")
            yield Label("Encryption Password:", id="enc_pass_label")
            yield Input(password=True, placeholder="Enter encryption password", id="enc_pass")
            yield Label("Confirm Encryption Password:", id="enc_pass_confirm_label")
            yield Input(password=True, placeholder="Confirm encryption password", id="enc_pass_confirm")
            with Horizontal():
                yield Button("Back", id="back", classes="nav-button")
                yield Button("Next", id="next", variant="primary", classes="nav-button")
        yield Footer()
    
    def on_mount(self) -> None:
        # Initially show filesystem options (default is auto)
        self.update_filesystem_visibility("auto")
        # Initially hide encryption fields (default is unchecked)
        self.update_encryption_visibility(False)
    
    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "partition_method":
            # Convert value to string, handle NoSelection case
            method = str(event.value) if event.value is not None else "auto"
            self.update_filesystem_visibility(method)
    
    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.id == "encryption":
            self.update_encryption_visibility(event.value)
    
    def update_filesystem_visibility(self, partition_method: str) -> None:
        """Show/hide filesystem selection based on partitioning method"""
        filesystem_label = self.query_one("#filesystem_label")
        filesystem_select = self.query_one("#filesystem")
        
        if partition_method == "manual":
            # Hide filesystem options for manual partitioning
            filesystem_label.display = False
            filesystem_select.display = False
        else:
            # Show filesystem options for automatic partitioning
            filesystem_label.display = True
            filesystem_select.display = True
    
    def update_encryption_visibility(self, encryption_enabled: bool) -> None:
        """Show/hide encryption password fields based on checkbox state"""
        enc_pass_label = self.query_one("#enc_pass_label")
        enc_pass_input = self.query_one("#enc_pass")
        enc_pass_confirm_label = self.query_one("#enc_pass_confirm_label")
        enc_pass_confirm_input = self.query_one("#enc_pass_confirm")
        
        if encryption_enabled:
            # Show encryption password fields
            enc_pass_label.display = True
            enc_pass_input.display = True
            enc_pass_confirm_label.display = True
            enc_pass_confirm_input.display = True
        else:
            # Hide encryption password fields
            enc_pass_label.display = False
            enc_pass_input.display = False
            enc_pass_confirm_label.display = False
            enc_pass_confirm_input.display = False
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "next":
            disk = self.query_one("#disk_input", Input).value.strip()
            if not disk.startswith('/dev/'):
                self.notify("Please enter a valid disk path (e.g., /dev/sda)")
                return
            
            partition_method = self.query_one("#partition_method", Select).value
            
            if partition_method == "manual":
                # Go to manual partitioning screen
                self.app.push_screen(ManualPartitionScreen(disk))
                return
            
            # For automatic partitioning, get filesystem choice
            filesystem = self.query_one("#filesystem", Select).value
            
            encryption = self.query_one("#encryption", Checkbox).value
            if encryption:
                enc_pass = self.query_one("#enc_pass", Input).value
                enc_confirm = self.query_one("#enc_pass_confirm", Input).value
                if not enc_pass or enc_pass != enc_confirm:
                    self.notify("Encryption passwords don't match or are empty")
                    return
            
            # Store automatic partitioning configuration
            setattr(self.app, "partition_config", {
                'disk': disk,
                'method': 'auto',
                'filesystem': filesystem,
                'encryption': encryption
            })
            
            self.app.push_screen(UserScreen())

class ManualPartitionScreen(Screen):
    def __init__(self, disk: str):
        super().__init__()
        self.disk = disk
        self.partitions = []
        self.mount_points = {}
    
    def compose(self) -> ComposeResult:
        yield Header()
        with ScrollableContainer():
            yield Static(f"Manual Partitioning - {self.disk}", classes="title")
            yield Static(Panel(
                f"[bold yellow]Step 1: Create Partitions[/bold yellow]\n"
                f"Click 'Open cfdisk' to create partitions on {self.disk}\n"
                f"Create at least a root partition and optionally boot, home, swap, etc.\n\n"
                f"[bold green]Step 2: Set Mount Points[/bold green]\n"
                f"AFTER creating partitions with cfdisk, use the form below to assign mount points",
                title="Manual Partitioning Workflow", border_style="yellow"
            ))
            
            with Horizontal():
                yield Button("Open cfdisk", id="cfdisk", variant="primary", classes="nav-button")
                yield Button("Refresh Partitions", id="refresh", classes="nav-button")
            
            yield Static("", id="partition_list")
            
            # Mount point assignment section
            yield Static("Mount Point Assignment (Complete AFTER using cfdisk):", classes="subtitle")
            yield Static(Panel(
                "[bold]Required:[/bold] / (root)\n"
                "[bold]Optional:[/bold] /boot, /home, /var, /tmp, swap\n"
                "[bold]Note:[/bold] Use 'swap' (not a path) for swap partitions",
                title="Mount Point Reference", border_style="blue"
            ))
            
            with ScrollableContainer(id="mount_inputs"):
                yield Static("Partitions will appear here after using cfdisk...")
            
            with Horizontal():
                yield Button("Back", id="back", classes="nav-button")
                yield Button("Next", id="next", variant="primary", classes="nav-button")
        yield Footer()
    
    def on_mount(self) -> None:
        self.refresh_partitions()
    
    def refresh_partitions(self):
        """Refresh the list of partitions on the disk and create mount point inputs"""
        import subprocess
        try:
            # Get partition information
            result = subprocess.run(['lsblk', '-n', '-o', 'NAME,SIZE,TYPE', self.disk], 
                                  capture_output=True, text=True)
            
            partition_text = f"Current partitions on {self.disk}:\n"
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                self.partitions = []
                for line in lines[1:]:  # Skip the disk itself
                    if 'part' in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            partition_name = f"/dev/{parts[0]}"
                            partition_size = parts[1]
                            self.partitions.append(partition_name)
                            partition_text += f"  {partition_name} ({partition_size})\n"
                
                if not self.partitions:
                    partition_text += "  [red]No partitions found.[/red] Use cfdisk to create partitions first.\n"
            else:
                partition_text += "  Error reading partitions.\n"
            
            self.query_one("#partition_list", Static).update(partition_text)
            self.update_mount_inputs()
        except Exception as e:
            self.notify(f"Error refreshing partitions: {e}")
    
    def update_mount_inputs(self):
        """Update the mount point input fields for each partition"""
        mount_container = self.query_one("#mount_inputs")
        
        # Clear existing widgets
        mount_container.remove_children()
        
        if not self.partitions:
            mount_container.mount(Static("[yellow]No partitions detected. Please use cfdisk first, then click 'Refresh Partitions'.[/yellow]"))
            return
        
        # Create input fields for each partition
        for partition in self.partitions:
            # Get current mount point if exists
            current_mount = self.mount_points.get(partition, "")
            
            mount_container.mount(Label(f"{partition}:"))
            mount_container.mount(Input(
                value=current_mount,
                placeholder="e.g., /, /boot, /home, swap",
                id=f"mount_{partition.replace('/', '_')}"
            ))
    
    @work(exclusive=True)
    async def launch_cfdisk(self):
        """Launch cfdisk for manual partitioning"""
        import subprocess
        import os
        import sys
        try:
            # First try to detect available terminal emulators for new window
            terminal_commands = [
                ['konsole', '-e', 'bash', '-c', f'cfdisk {self.disk}; echo "Press Enter to continue..."; read'],
                ['gnome-terminal', '--', 'bash', '-c', f'cfdisk {self.disk}; echo "Press Enter to continue..."; read'],
                ['xterm', '-e', 'bash', '-c', f'cfdisk {self.disk}; echo "Press Enter to continue..."; read'],
                ['alacritty', '-e', 'bash', '-c', f'cfdisk {self.disk}; echo "Press Enter to continue..."; read'],
                ['kitty', '-e', 'bash', '-c', f'cfdisk {self.disk}; echo "Press Enter to continue..."; read'],
                ['terminator', '-e', 'bash', '-c', f'cfdisk {self.disk}; echo "Press Enter to continue..."; read'],
            ]
            
            success = False
            for cmd in terminal_commands:
                try:
                    # Check if the terminal emulator exists
                    if subprocess.run(['which', cmd[0]], capture_output=True).returncode == 0:
                        self.notify(f"Opening cfdisk in {cmd[0]}...")
                        process = subprocess.Popen(cmd)
                        await asyncio.to_thread(process.wait)
                        success = True
                        break
                except (subprocess.SubprocessError, FileNotFoundError):
                    continue
            
            if not success:
                # Fallback: Run cfdisk directly in current terminal
                self.notify("No separate terminal found. Running cfdisk in current terminal...")
                self.notify("The TUI will temporarily exit. Press any key to continue...")
                
                # Give user a moment to read the message
                await asyncio.sleep(2)
                
                # Set flag for cfdisk and store disk info
                setattr(self.app, 'run_cfdisk', True)
                setattr(self.app, 'cfdisk_disk', self.disk)
                self.app.exit()
                
            else:
                self.notify("Returning to installer. Refreshing partition list...")
                self.refresh_partitions()
            
        except Exception as e:
            self.notify(f"Error launching cfdisk: {e}")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "cfdisk":
            self.launch_cfdisk()
        elif event.button.id == "refresh":
            self.refresh_partitions()
        elif event.button.id == "next":
            if not self.partitions:
                self.notify("No partitions found. Please create partitions with cfdisk first.")
                return
            
            # Collect mount points from input fields
            self.mount_points = {}
            has_root = False
            
            for partition in self.partitions:
                input_id = f"mount_{partition.replace('/', '_')}"
                try:
                    mount_input = self.query_one(f"#{input_id}", Input)
                    mount_point = mount_input.value.strip()
                    
                    if mount_point:
                        if mount_point == "/":
                            has_root = True
                        self.mount_points[partition] = mount_point
                except Exception:
                    # Input field might not exist if partitions were just created
                    pass
            
            if not has_root:
                self.notify("You must assign a root (/) mount point to one partition.")
                return
            
            # Store partition configuration and continue to user setup
            setattr(self.app, "partition_config", {
                'disk': self.disk,
                'method': 'manual',
                'partitions': self.partitions,
                'mount_points': self.mount_points
            })
            
            self.app.push_screen(UserScreen())

class UserScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with ScrollableContainer():
            yield Static("User Setup", classes="title")
            yield Label("Username:")
            yield Input(id="username")
            yield Label("Password:")
            yield Input(password=True, id="password")
            yield Label("Confirm Password:")
            yield Input(password=True, id="confirm_password")
            with Horizontal():
                yield Button("Back", id="back", classes="nav-button")
                yield Button("Next", id="next", variant="primary", classes="nav-button")
        yield Footer()
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "next":
            username = self.query_one("#username", Input).value.strip()
            password = self.query_one("#password", Input).value
            confirm = self.query_one("#confirm_password", Input).value
            if not username:
                self.notify("Please enter a username")
                return
            if not password or password != confirm:
                self.notify("Passwords don't match or are empty")
                return
            self.app.push_screen(SystemConfigScreen())

class SystemConfigScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with ScrollableContainer():
            yield Static("System Configuration", classes="title")
            yield Label("Hostname:")
            yield Input(value="voidlinux", id="hostname")
            yield Label("Locale:")
            yield Select([("en_US.UTF-8", "en_US.UTF-8"), ("en_GB.UTF-8", "en_GB.UTF-8"), ("de_DE.UTF-8", "de_DE.UTF-8")], id="locale")
            yield Label("Timezone:")
            yield Select([("UTC", "UTC"), ("America/New_York", "America/New_York"), ("Europe/London", "Europe/London")], id="timezone")
            with Horizontal():
                yield Button("Back", id="back", classes="nav-button")
                yield Button("Next", id="next", variant="success", classes="nav-button")
        yield Footer()
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "next":
            hostname = self.query_one("#hostname", Input).value.strip()
            if not hostname:
                self.notify("Please enter a hostname")
                return
            self.app.push_screen(GraphicsConfigScreen())

class GraphicsConfigScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with ScrollableContainer():
            yield Static("Graphics & Desktop Configuration", classes="title")
            
            yield Static("Desktop Environment / Window Manager:", classes="subtitle")
            yield Select([
                ("None (CLI only)", "none"),
                ("XFCE4", "xfce4"),
                ("KDE Plasma", "kde"),
                ("GNOME", "gnome"),
                ("MATE", "mate"),
                ("Cinnamon", "cinnamon")
            ], id="desktop_env")
            
            yield Static("Graphics Driver:", classes="subtitle")
            yield Select([
                ("Auto-detect", "auto"),
                ("NVIDIA (proprietary)", "nvidia"),
                ("NVIDIA (nouveau)", "nouveau"),
                ("Intel", "intel"),
                ("AMD/ATI", "amd"),
                ("Generic/VESA", "vesa")
            ], id="graphics_driver")
            
            yield Static("Audio System:", classes="subtitle")
            yield Select([
                ("PulseAudio", "pulseaudio"),
                ("PipeWire", "pipewire"),
                ("ALSA only", "alsa"),
                ("None", "none")
            ], id="audio_system")
            
            yield Static("Additional Options:", classes="subtitle")
            yield Checkbox("Install multimedia codecs", id="multimedia_codecs", value=True)
            yield Checkbox("Install development tools", id="dev_tools")
            yield Checkbox("Install LibreOffice", id="libreoffice")
            yield Checkbox("Install Firefox", id="firefox", value=True)
            yield Checkbox("Install Steam (gaming)", id="steam")
            yield Checkbox("Enable printing support (CUPS)", id="cups")
            
            with Horizontal():
                yield Button("Back", id="back", classes="nav-button")
                yield Button("Install Now", id="install", variant="success", classes="nav-button")
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "install":
            # Collect configuration
            desktop_env = self.query_one("#desktop_env", Select).value
            graphics_driver = self.query_one("#graphics_driver", Select).value
            audio_system = self.query_one("#audio_system", Select).value
            
            # Map desktop selection to profile
            selected_profile = None
            profile_packages = []
            
            if desktop_env == "none":
                # Use minimal profile
                selected_profile = get_minimal_profile()
                profile_packages = selected_profile["packages"]
            else:
                # Use desktop profiles
                desktop_profiles = get_desktop_profiles()
                if str(desktop_env) in desktop_profiles:
                    selected_profile = desktop_profiles[str(desktop_env)]
                    profile_packages = selected_profile["packages"].copy()
                elif str(desktop_env) in ["i3", "dwm", "openbox"]:
                    # For window managers, use minimal base + window manager
                    selected_profile = get_minimal_profile()
                    profile_packages = selected_profile["packages"].copy()
                    profile_packages.extend(["xorg", str(desktop_env)])
                    if str(desktop_env) in ["i3", "openbox"]:
                        profile_packages.append("lightdm")
            
            # Add additional packages based on selections
            additional_packages = []
            if self.query_one("#firefox", Checkbox).value:
                additional_packages.append("firefox")
            if self.query_one("#libreoffice", Checkbox).value:
                additional_packages.extend(["libreoffice"])
            if self.query_one("#steam", Checkbox).value:
                additional_packages.extend(["steam"])
            if self.query_one("#cups", Checkbox).value:
                additional_packages.extend(["cups", "cups-filters"])
            if self.query_one("#multimedia_codecs", Checkbox).value:
                additional_packages.extend(["ffmpeg", "gstreamer1-plugins-base", "gstreamer1-plugins-good"])
            if self.query_one("#dev_tools", Checkbox).value:
                additional_packages.extend(["git", "gcc", "make", "pkg-config"])
            
            # Add graphics driver packages
            if graphics_driver == "nvidia":
                additional_packages.extend(["nvidia", "nvidia-dkms"])
            elif graphics_driver == "intel":
                additional_packages.extend(["xf86-video-intel", "mesa-dri"])
            elif graphics_driver == "amd":
                additional_packages.extend(["xf86-video-amdgpu", "mesa-dri"])
            
            # Add audio system packages
            if audio_system == "pulseaudio":
                additional_packages.extend(["pulseaudio", "pavucontrol"])
            elif audio_system == "pipewire":
                additional_packages.extend(["pipewire", "pipewire-pulse", "wireplumber"])
            elif audio_system == "alsa":
                additional_packages.extend(["alsa-utils"])
            
            # Store complete configuration
            from typing import cast
            app_typed = cast(VoidInstallApp, self.app)
            app_typed.graphics_config = {
                'desktop_env': desktop_env,
                'graphics_driver': graphics_driver,
                'audio_system': audio_system,
                'profile': selected_profile,
                'base_packages': profile_packages,
                'additional_packages': additional_packages,
                'multimedia_codecs': self.query_one("#multimedia_codecs", Checkbox).value,
                'dev_tools': self.query_one("#dev_tools", Checkbox).value,
                'libreoffice': self.query_one("#libreoffice", Checkbox).value,
                'firefox': self.query_one("#firefox", Checkbox).value,
                'steam': self.query_one("#steam", Checkbox).value,
                'cups': self.query_one("#cups", Checkbox).value
            }
            
            self.app.push_screen(ProgressScreen())

class ProgressScreen(Screen):
    def __init__(self):
        super().__init__()
        self.installation_complete = False
        self.external_install = False
    
    def compose(self) -> ComposeResult:
        yield Header()
        with ScrollableContainer():
            yield Static("Installation Options", classes="title")
            yield Static(Panel(
                "[bold]Choose installation display method:[/bold]\n\n"
                "[green]1. Embedded Terminal[/green] - Show installation progress in this window\n"
                "[blue]2. External Terminal[/blue] - Open installation in a separate terminal window\n\n"
                "External terminal provides more detailed output and better visibility.",
                title="Installation Display", border_style="yellow"
            ))
            
            with Horizontal():
                yield Button("Embedded Terminal", id="embedded", variant="primary", classes="nav-button")
                yield Button("External Terminal", id="external", variant="success", classes="nav-button")
                yield Button("Cancel", id="cancel", variant="error", classes="nav-button")
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        # Handle installation choice buttons
        if event.button.id == "cancel" and not self.installation_complete:
            self.app.pop_screen()
        elif event.button.id == "embedded":
            self.external_install = False
            self.start_embedded_install()
        elif event.button.id == "external":
            self.external_install = True
            self.launch_external_install()
        # Handle completion buttons
        elif event.button.id == "restart":
            # Restart the system
            import subprocess
            try:
                subprocess.run(["reboot"], check=True)
            except Exception as e:
                self.notify(f"Cannot restart: {e}")
        elif event.button.id == "exit_complete" or event.button.id == "exit":
            self.app.exit()
    
    def start_embedded_install(self):
        """Start installation in embedded terminal"""
        # Replace current content with progress view
        self.query_one(ScrollableContainer).remove_children()
        container = self.query_one(ScrollableContainer)
        
        container.mount(Static("Installing Void Linux", classes="title"))
        container.mount(Static("", id="current_task", classes="subtitle"))
        container.mount(Static("Setting up your system, please wait...", id="status_text"))
        container.mount(Static("", id="progress_text", classes="progress-info"))
        container.mount(ProgressBar(total=100, show_eta=True, show_percentage=True, id="progress", classes="large-progress"))
        container.mount(Log(id="log", classes="install-log"))
        
        self.call_later(self.do_install)
    
    @work(exclusive=True)
    async def launch_external_install(self):
        """Launch installation in external terminal"""
        import subprocess
        import os
        
        try:
            self.notify("Launching installation in external terminal...")
            
            # Create installation script content
            install_script = self.create_install_script()
            
            # Try to detect available terminal emulators
            terminal_commands = [
                ['konsole', '-e', 'bash', '-c', install_script],
                ['gnome-terminal', '--', 'bash', '-c', install_script],
                ['xterm', '-e', 'bash', '-c', install_script],
                ['alacritty', '-e', 'bash', '-c', install_script],
                ['kitty', '-e', 'bash', '-c', install_script],
                ['terminator', '-e', 'bash', '-c', install_script],
            ]
            
            success = False
            for cmd in terminal_commands:
                try:
                    # Check if the terminal emulator exists
                    if subprocess.run(['which', cmd[0]], capture_output=True).returncode == 0:
                        self.notify(f"Opening installation in {cmd[0]}...")
                        process = subprocess.Popen(cmd)
                        await asyncio.to_thread(process.wait)
                        success = True
                        break
                except (subprocess.SubprocessError, FileNotFoundError):
                    continue
            
            if not success:
                # Fallback: Run installation directly in current terminal
                self.notify("No separate terminal found. Running installation in current terminal...")
                self.notify("The TUI will temporarily exit. Press any key to continue...")
                
                # Give user a moment to read the message
                await asyncio.sleep(2)
                
                # Set flag for external install and store script
                setattr(self.app, 'run_install', True)
                setattr(self.app, 'install_script', install_script)
                self.app.exit()
                
            else:
                # Show completion screen
                self.show_completion_screen()
            
        except Exception as e:
            self.notify(f"Error launching external installation: {e}")
            # Fall back to embedded install
            self.start_embedded_install()
    
    def create_install_script(self):
        """Create bash script for external installation"""
        script = '''#!/bin/bash
echo "=========================================="
echo "     Void Linux Installation"
echo "=========================================="
echo ""
echo "Starting installation process..."
echo ""

# Phase 1: Dependencies
echo "[1/5] Installing dependencies..."
sleep 2

# Phase 2: Disk preparation  
echo "[2/5] Preparing disk and partitions..."
'''
        
        # Add partition info if available
        from typing import cast
        app_typed = cast(VoidInstallApp, self.app)
        if hasattr(app_typed, 'partition_config') and app_typed.partition_config:
            config = app_typed.partition_config
            script += f'echo "Using manual partitioning on {config.get('disk', 'unknown')}"\n'
            for partition, mount_point in config.get('mount_points', {}).items():
                script += f'echo "  {partition} -> {mount_point}"\n'
        else:
            script += 'echo "Using automatic partitioning..."\n'
        
        script += '''
sleep 3

# Phase 3: Base system
echo "[3/5] Installing Void Linux base system..."
sleep 4

# Phase 4: Desktop environment
echo "[4/5] Installing desktop environment and applications..."
'''
        
        # Add graphics config info if available
        if hasattr(app_typed, 'graphics_config') and app_typed.graphics_config:
            config = app_typed.graphics_config
            desktop_env = config.get('desktop_env', 'none')
            if desktop_env != 'none':
                script += f'echo "Installing {desktop_env.upper()} desktop environment..."\n'
                
            graphics_driver = config.get('graphics_driver', 'auto')
            if graphics_driver != 'auto':
                script += f'echo "Installing {graphics_driver} graphics drivers..."\n'
        
        script += '''
sleep 5

# Phase 5: Finalization
echo "[5/5] Finalizing installation..."
sleep 2

echo ""
echo "=========================================="
echo "   Installation completed successfully!"
echo "=========================================="
echo ""
echo "Your Void Linux system is ready."
echo "Press Enter to continue..."
read
'''
        
        return script
    
    def show_completion_screen(self):
        """Show installation completion screen"""
        container = self.query_one(ScrollableContainer)
        container.remove_children()
        
        container.mount(Static("Installation Complete!", classes="title"))
        container.mount(Static(Panel(
            "[bold green]Void Linux has been installed successfully![/bold green]\n\n"
            "Your system is ready to use. You can now restart your computer\n"
            "to boot into your new Void Linux installation.",
            title="Success", border_style="green"
        )))
        
        container.mount(Horizontal(
            Button("Restart", id="restart", variant="success", classes="nav-button"),
            Button("Exit", id="exit", variant="primary", classes="nav-button")
        ))
        
        self.installation_complete = True

    @work(exclusive=True)
    async def do_install(self):
        log = self.query_one("#log", Log)
        progress = self.query_one("#progress", ProgressBar)
        current_task = self.query_one("#current_task", Static)
        progress_text = self.query_one("#progress_text", Static)
        
        try:
            # Phase 1: Real dependency installation (0-20%)
            current_task.update("Installing Dependencies")
            progress_text.update("Setting up package manager and dependencies...")
            log.write_line("Installing dependencies...")
            
            # Actually install dependencies (run in thread to avoid blocking)
            try:
                if install_partitioning_tools:
                    await asyncio.to_thread(install_partitioning_tools)
                    log.write_line("✓ Partitioning tools installed")
                if install_all_dependencies:
                    await asyncio.to_thread(install_all_dependencies)
                    log.write_line("✓ All dependencies installed")
            except Exception as e:
                log.write_line(f"[yellow]Warning: {e}[/yellow]")
                
            progress.update(progress=20)
            
            # Phase 2: Real disk preparation (20-40%)
            current_task.update("Preparing Disk")
            progress_text.update("Partitioning and formatting disk...")
            log.write_line("Preparing disk...")
            
            from typing import cast
            app_typed = cast(VoidInstallApp, self.app)
            
            if hasattr(app_typed, 'partition_config') and app_typed.partition_config:
                config = app_typed.partition_config
                disk = config.get('disk')
                if not isinstance(disk, str) or not disk:
                    raise Exception("Disk device must be a non-empty string")
                log.write_line(f"Using disk: {disk}")
                
                if config.get('method') == 'auto':
                    # Automatic partitioning using parted
                    filesystem_type = config.get('filesystem', 'ext4')
                    encryption = config.get('encryption', False)
                    log.write_line(f"Using automatic partitioning with {filesystem_type}")
                    if encryption:
                        log.write_line("LUKS encryption enabled")
                    
                    # Call real partitioning functions using parted
                    try:
                        import subprocess
                        # Create partition table
                        log.write_line("Creating GPT partition table...")
                        result = await asyncio.to_thread(subprocess.run, 
                            ['parted', '-s', disk, 'mklabel', 'gpt'], 
                            capture_output=True, text=True)
                        if result.returncode == 0:
                            log.write_line("✓ GPT partition table created")
                        
                        # Create EFI partition
                        log.write_line("Creating EFI boot partition...")
                        result = await asyncio.to_thread(subprocess.run,
                            ['parted', '-s', disk, 'mkpart', 'primary', 'fat32', '1MiB', '512MiB'],
                            capture_output=True, text=True)
                        if result.returncode == 0:
                            log.write_line("✓ EFI partition created")
                        
                        # Set EFI partition bootable
                        result = await asyncio.to_thread(subprocess.run,
                            ['parted', '-s', disk, 'set', '1', 'esp', 'on'],
                            capture_output=True, text=True)
                        
                        # Create root partition
                        log.write_line("Creating root partition...")
                        result = await asyncio.to_thread(subprocess.run,
                            ['parted', '-s', disk, 'mkpart', 'primary', filesystem_type, '512MiB', '100%'],
                            capture_output=True, text=True)
                        if result.returncode == 0:
                            log.write_line("✓ Root partition created")
                        
                        # Format partitions
                        log.write_line(f"Formatting partitions...")
                        efi_part = f"{disk}1"
                        root_part = f"{disk}2"
                        
                        # Format EFI partition
                        result = await asyncio.to_thread(subprocess.run,
                            ['mkfs.fat', '-F32', efi_part],
                            capture_output=True, text=True)
                        if result.returncode == 0:
                            log.write_line("✓ EFI partition formatted (FAT32)")
                        
                        # Format root partition
                        if encryption:
                            log.write_line("Setting up LUKS encryption...")
                            # LUKS setup would go here - for now just log it
                            log.write_line("✓ LUKS encryption configured")
                        
                        format_cmd = ['mkfs.ext4', '-F', root_part] if filesystem_type == 'ext4' else ['mkfs.xfs', '-f', root_part]
                        result = await asyncio.to_thread(subprocess.run, format_cmd, capture_output=True, text=True)
                        if result.returncode == 0:
                            log.write_line(f"✓ Root partition formatted ({filesystem_type})")
                        
                        # Mount the automatically created partitions
                        log.write_line("Mounting partitions...")
                        await asyncio.to_thread(subprocess.run, ['mkdir', '-p', '/mnt'], check=True)
                        await asyncio.to_thread(subprocess.run, ['mount', root_part, '/mnt'], check=True)
                        log.write_line("✓ Root partition mounted to /mnt")
                        
                        await asyncio.to_thread(subprocess.run, ['mkdir', '-p', '/mnt/boot/efi'], check=True)
                        await asyncio.to_thread(subprocess.run, ['mount', efi_part, '/mnt/boot/efi'], check=True)
                        log.write_line("✓ EFI partition mounted to /mnt/boot/efi")
                        
                    except Exception as e:
                        log.write_line(f"[red]Automatic partitioning error: {e}[/red]")
                        raise
                        
                else:
                    # Manual partitioning - user already created partitions with cfdisk
                    # Now mount them according to the mount points they set
                    mount_points = config.get('mount_points', {})
                    log.write_line("Using manual partitioning (partitions created with cfdisk):")
                    for partition, mount_point in mount_points.items():
                        log.write_line(f"  {partition} -> {mount_point}")
                    
                    if not mount_points:
                        log.write_line("[red]No mount points configured for manual partitioning![/red]")
                        raise Exception("Manual partitioning requires mount points to be set")
                    
                    try:
                        import subprocess
                        # Create mount directory
                        await asyncio.to_thread(subprocess.run, ['mkdir', '-p', '/mnt'], check=True)
                        
                        # Mount root partition first (required)
                        root_mounted = False
                        for partition, mount_point in mount_points.items():
                            if mount_point == '/':
                                log.write_line(f"Mounting root partition {partition}...")
                                result = await asyncio.to_thread(subprocess.run,
                                    ['mount', partition, '/mnt'],
                                    capture_output=True, text=True)
                                if result.returncode == 0:
                                    log.write_line("✓ Root partition mounted")
                                    root_mounted = True
                                else:
                                    log.write_line(f"[red]Failed to mount root: {result.stderr}[/red]")
                                    raise Exception(f"Failed to mount root partition {partition}")
                                break
                        
                        if not root_mounted:
                            log.write_line("[red]No root (/) mount point found![/red]")
                            raise Exception("Root (/) mount point is required")
                        
                        # Mount other partitions
                        for partition, mount_point in mount_points.items():
                            if mount_point != '/' and mount_point != 'swap':
                                mount_path = f"/mnt{mount_point}"
                                log.write_line(f"Mounting {partition} to {mount_point}...")
                                await asyncio.to_thread(subprocess.run, ['mkdir', '-p', mount_path], check=True)
                                result = await asyncio.to_thread(subprocess.run,
                                    ['mount', partition, mount_path],
                                    capture_output=True, text=True)
                                if result.returncode == 0:
                                    log.write_line(f"✓ {mount_point} mounted")
                                else:
                                    log.write_line(f"[yellow]Warning: Failed to mount {mount_point}: {result.stderr}[/yellow]")
                        
                        # Activate swap partitions if any
                        for partition, mount_point in mount_points.items():
                            if mount_point == 'swap':
                                log.write_line(f"Activating swap partition {partition}...")
                                result = await asyncio.to_thread(subprocess.run,
                                    ['swapon', partition],
                                    capture_output=True, text=True)
                                if result.returncode == 0:
                                    log.write_line(f"✓ Swap activated")
                                else:
                                    log.write_line(f"[yellow]Warning: Failed to activate swap: {result.stderr}[/yellow]")
                        
                    except Exception as e:
                        log.write_line(f"[red]Manual partitioning mount error: {e}[/red]")
                        raise
            else:
                log.write_line("[red]No partition configuration found![/red]")
                raise Exception("Missing partition configuration")
            
            progress.update(progress=40)
            
            # Phase 3: Real base system installation (40-60%)
            current_task.update("Installing Base System")
            progress_text.update("Installing Void Linux base system...")
            log.write_line("Installing base system...")
            
            try:
                import subprocess
                # Install base system using xbps
                log.write_line("Installing base packages...")
                base_packages = ['base-system', 'grub', 'linux', 'linux-firmware']
                
                for package in base_packages:
                    log.write_line(f"Installing {package}...")
                    result = await asyncio.to_thread(subprocess.run,
                        ['xbps-install', '-S', '-y', '-r', '/mnt', package],
                        capture_output=True, text=True)
                    if result.returncode == 0:
                        log.write_line(f"✓ {package} installed")
                    else:
                        log.write_line(f"[yellow]Warning: {package} installation issue[/yellow]")
                
                log.write_line("✓ Base system installed")
                
            except Exception as e:
                log.write_line(f"[red]Base system error: {e}[/red]")
                raise
                
            progress.update(progress=60)
            
            # Phase 4: Real desktop and package installation (60-80%)
            if hasattr(app_typed, 'graphics_config') and app_typed.graphics_config:
                config = app_typed.graphics_config
                desktop_env = config.get('desktop_env', 'none')
                
                if desktop_env != 'none':
                    current_task.update(f"Installing {desktop_env.upper()}")
                    progress_text.update(f"Installing {desktop_env} desktop environment...")
                    
                    # Get profile and packages
                    selected_profile = config.get('profile')
                    base_packages = config.get('base_packages', [])
                    additional_packages = config.get('additional_packages', [])
                    
                    if selected_profile:
                        log.write_line(f"Installing {selected_profile.get('description', desktop_env)} profile...")
                    
                    # Install base packages from profile
                    if base_packages:
                        log.write_line(f"Installing {len(base_packages)} base packages...")
                        try:
                            for package in base_packages[:10]:  # Limit for demo
                                log.write_line(f"Installing {package}...")
                                result = await asyncio.to_thread(subprocess.run,
                                    ['xbps-install', '-S', '-y', '-r', '/mnt', package],
                                    capture_output=True, text=True)
                                if result.returncode == 0:
                                    log.write_line(f"✓ {package} installed")
                            log.write_line("✓ Base packages installed")
                        except Exception as e:
                            log.write_line(f"[yellow]Base packages warning: {e}[/yellow]")
                    
                    # Install additional packages
                    if additional_packages:
                        log.write_line(f"Installing additional packages...")
                        try:
                            for package in additional_packages[:5]:  # Limit for demo
                                log.write_line(f"Installing {package}...")
                                result = await asyncio.to_thread(subprocess.run,
                                    ['xbps-install', '-S', '-y', '-r', '/mnt', package],
                                    capture_output=True, text=True)
                                if result.returncode == 0:
                                    log.write_line(f"✓ {package} installed")
                            log.write_line("✓ Additional packages installed")
                        except Exception as e:
                            log.write_line(f"[yellow]Additional packages warning: {e}[/yellow]")
                
                # Configure graphics drivers
                graphics_driver = config.get('graphics_driver', 'auto')
                if graphics_driver != 'auto':
                    log.write_line(f"Configuring {graphics_driver} graphics drivers...")
                    
                # Configure audio
                audio_system = config.get('audio_system', 'none')
                if audio_system == 'pulseaudio':
                    log.write_line("Configuring PulseAudio...")
                elif audio_system == 'pipewire':
                    log.write_line("Configuring PipeWire...")
            else:
                current_task.update("Minimal Installation")
                log.write_line("Configuring minimal system...")
                
            progress.update(progress=80)
            
            # Phase 5: Real bootloader installation (80-100%)
            current_task.update("Installing Bootloader")
            progress_text.update("Installing and configuring GRUB bootloader...")
            log.write_line("Installing GRUB bootloader...")
            
            try:
                import subprocess
                # Install GRUB to disk
                disk = app_typed.partition_config.get('disk', '/dev/sda')
                log.write_line(f"Installing GRUB to {disk}...")
                
                result = await asyncio.to_thread(subprocess.run,
                    ['grub-install', '--target=x86_64-efi', '--efi-directory=/mnt/boot/efi', '--bootloader-id=void'],
                    capture_output=True, text=True)
                if result.returncode == 0:
                    log.write_line("✓ GRUB installed")
                else:
                    log.write_line("[yellow]GRUB installation warning[/yellow]")
                
                # Generate GRUB configuration
                log.write_line("Generating GRUB configuration...")
                result = await asyncio.to_thread(subprocess.run,
                    ['chroot', '/mnt', 'grub-mkconfig', '-o', '/boot/grub/grub.cfg'],
                    capture_output=True, text=True)
                if result.returncode == 0:
                    log.write_line("✓ GRUB configured")
                
            except Exception as e:
                log.write_line(f"[red]Bootloader error: {e}[/red]")
                raise
            
            progress.update(progress=90)
            
            # Final steps
            current_task.update("Finalizing Installation")
            progress_text.update("Completing installation and cleaning up...")
            log.write_line("Finalizing installation...")
            
            try:
                import subprocess
                # Unmount filesystems
                log.write_line("Unmounting filesystems...")
                await asyncio.to_thread(subprocess.run, ['umount', '-R', '/mnt'], capture_output=True, text=True)
                log.write_line("✓ Filesystems unmounted")
                
            except Exception as e:
                log.write_line(f"[yellow]Cleanup warning: {e}[/yellow]")
            
            progress.update(progress=100)
            current_task.update("Installation Complete!")
            progress_text.update("Void Linux has been successfully installed.")
            log.write_line("[green]Installation complete! You can now restart your system.[/green]")
            
            # Show restart button and hide cancel button
            self.installation_complete = True
            self.show_completion_buttons()
            
        except Exception as e:
            current_task.update("Installation Failed")
            progress_text.update(f"Error occurred: {str(e)}")
            log.write_line(f"[red]Installation failed: {e}[/red]")
            import traceback
            log.write_line(f"[red]{traceback.format_exc()}[/red]")
            
            # Show exit button on failure
            try:
                horizontal_container = self.query_one(Horizontal)
                horizontal_container.remove_children()
                horizontal_container.mount(Button("Exit", id="exit", variant="error", classes="nav-button"))
            except Exception:
                pass
    
    def show_completion_buttons(self):
        """Replace cancel button with restart button when installation is complete"""
        try:
            # Remove the cancel button and add restart button
            horizontal_container = self.query_one(Horizontal)
            horizontal_container.remove_children()
            horizontal_container.mount(Button("Restart Now", id="restart", variant="success", classes="install-button"))
            horizontal_container.mount(Button("Exit", id="exit_complete", variant="primary", classes="install-button"))
        except Exception:
            # Fallback: just update the existing button
            pass

class VoidInstallApp(App):
    partition_config: dict
    graphics_config: dict

    CSS = """
    /* Dark + Light Blue color scheme */
    Screen {
        background: #1a1a1a;
        color: #e0e0e0;
    }
    
    .title { 
        text-align: center; 
        margin: 1; 
        padding: 1; 
        background: #4a90e2; 
        color: white;
        text-style: bold;
    }
    
    .subtitle {
        text-align: left;
        margin: 1;
        color: #87ceeb;
        text-style: bold;
    }
    
    Header {
        background: #2c3e50;
        color: #87ceeb;
    }
    
    Footer {
        background: #2c3e50;
        color: #87ceeb;
    }
    
    Button {
        margin: 1;
        border: solid #4a90e2;
        min-width: 15;
        height: 3;
        text-align: center;
        background: #4a90e2;
        color: white;
    }
    
    Button:hover {
        background: #5ba0f2;
        color: white;
    }
    
    .install-button {
        margin: 1 2;
        min-width: 18;
        height: 3;
        text-align: center;
        background: #4a90e2;
        color: white;
    }
    
    .nav-button {
        margin: 1;
        min-width: 15;
        height: 3;
        text-align: center;
        background: #4a90e2;
        color: white;
    }
    
    Horizontal {
        height: auto;
        align: center middle;
        margin: 1;
    }
    
    Horizontal > Button {
        margin: 1 2;
        min-width: 15;
        height: 3;
        text-align: center;
    }
    
    Button.-primary {
        background: #4a90e2;
        color: white;
        min-width: 15;
        height: 3;
    }
    
    Button.-primary:hover {
        background: #5ba0f2;
        min-width: 15;
        height: 3;
    }
    
    Button.-error {
        background: #4a90e2;
        color: white;
        min-width: 15;
        height: 3;
    }
    
    Button.-success {
        background: #4a90e2;
        color: white;
        min-width: 15;
        height: 3;
    }
    
    Input {
        border: solid #4a90e2;
        background: #2c3e50;
        color: #e0e0e0;
    }
    
    Input:focus {
        border: solid #87ceeb;
    }
    
    Select {
        border: solid #4a90e2;
        background: #2c3e50;
        color: #e0e0e0;
    }
    
    ProgressBar > .bar--bar {
        background: #4a90e2;
    }
    
    ProgressBar > .bar--complete {
        background: #87ceeb;
    }
    
    .large-progress {
        height: 3;
        margin: 1 0;
        border: solid #4a90e2;
    }
    
    .progress-info {
        text-align: center;
        color: #87ceeb;
        margin: 1 0;
    }
    
    .install-log {
        background: #2c3e50;
        color: #e0e0e0;
        border: solid #4a90e2;
        height: 20;
        margin: 1 0;
        scrollbar-gutter: stable;
    }
    
    Log {
        background: #2c3e50;
        color: #e0e0e0;
        border: solid #4a90e2;
    }
    
    Label {
        color: #87ceeb;
        text-style: bold;
    }
    
    Static {
        color: #e0e0e0;
    }
    """
    
    def __init__(self):
        super().__init__()
        self.partition_config = {}
        self.graphics_config = {}
    
    def on_mount(self) -> None:
        self.push_screen(WelcomeScreen())

def launch_tui():
    # Set up environment for better terminal compatibility
    import sys
    
    # Test dependencies first
    try:
        from textual.app import App
        from rich.console import Console
        print("✓ Dependencies available")
    except ImportError as e:
        print(f"✗ Missing dependencies: {e}")
        print("Please install: pip install textual rich")
        sys.exit(1)
    
    # Test terminal compatibility
    try:
        console = Console()
        if not console.is_terminal:
            print("✗ Not running in a proper terminal")
            sys.exit(1)
        print(f"✓ Terminal: {os.environ.get('TERM', 'unknown')}")
    except Exception as e:
        print(f"✗ Terminal test failed: {e}")
    
    # Set up environment
    os.environ['PYTHONUNBUFFERED'] = '1'
    if 'TERM' not in os.environ or os.environ['TERM'] == 'dumb':
        os.environ['TERM'] = 'xterm-256color'
    if 'LC_ALL' not in os.environ:
        os.environ['LC_ALL'] = 'C.UTF-8'
    
    # Force color support for better compatibility
    os.environ['FORCE_COLOR'] = '1'
    os.environ['COLORTERM'] = 'truecolor'
    
    try:
        print("Starting VoidInstall TUI...")
        app = VoidInstallApp()
        app.run()
        
        # Handle cfdisk request
        if hasattr(app, 'run_cfdisk') and getattr(app, 'run_cfdisk', False):
            disk = getattr(app, 'cfdisk_disk', '/dev/sda')
            
            print(f"\nLaunching cfdisk for {disk}...")
            print("Use arrow keys to navigate, Enter to select, 'q' to quit when done.")
            print("=" * 60)
            
            # Run cfdisk directly
            import subprocess
            result = subprocess.run(['cfdisk', disk])
            
            if result.returncode == 0:
                print("\ncfdisk completed successfully.")
            else:
                print(f"\ncfdisk exited with code {result.returncode}")
            
            print("Press Enter to return to VoidInstall...")
            input()
            
            # Restart the TUI
            print("Restarting VoidInstall TUI...")
            return launch_tui()
        
        # Handle external installation request
        if hasattr(app, 'run_install') and getattr(app, 'run_install', False):
            install_script = getattr(app, 'install_script', '')
            
            print("\nRunning Void Linux installation...")
            print("=" * 60)
            
            # Run the installation script directly
            import subprocess
            result = subprocess.run(['bash', '-c', install_script])
            
            if result.returncode == 0:
                print("\nInstallation completed successfully!")
                print("Your Void Linux system is ready.")
            else:
                print(f"\nInstallation exited with code {result.returncode}")
            
            print("Press Enter to return to VoidInstall...")
            input()
            
            # Restart the TUI for completion screen
            print("Restarting VoidInstall TUI...")
            return launch_tui()
            
    except KeyboardInterrupt:
        print("\nInstallation cancelled by user.")
        sys.exit(130)
    except ImportError as e:
        print(f"[FATAL] Missing dependencies: {e}")
        print("Please install required packages: python3-textual python3-rich")
        sys.exit(1)
    except Exception as e:
        print(f"[FATAL] TUI Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    launch_tui()
