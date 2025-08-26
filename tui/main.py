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
            yield Label("Filesystem:")
            yield Select([("ext4", "ext4"), ("xfs", "xfs"), ("btrfs", "btrfs")], id="filesystem")
            yield Checkbox("Enable LUKS Encryption", id="encryption")
            yield Label("Encryption Password:")
            yield Input(password=True, placeholder="Enter encryption password", id="enc_pass")
            yield Label("Confirm Encryption Password:")
            yield Input(password=True, placeholder="Confirm encryption password", id="enc_pass_confirm")
            with Horizontal():
                yield Button("Back", id="back", classes="nav-button")
                yield Button("Next", id="next", variant="primary", classes="nav-button")
        yield Footer()
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
            
            encryption = self.query_one("#encryption", Checkbox).value
            if encryption:
                enc_pass = self.query_one("#enc_pass", Input).value
                enc_confirm = self.query_one("#enc_pass_confirm", Input).value
                if not enc_pass or enc_pass != enc_confirm:
                    self.notify("Encryption passwords don't match or are empty")
                    return
            
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
                f"[bold yellow]Instructions:[/bold yellow]\n"
                f"1. Use cfdisk to create partitions on {self.disk}\n"
                f"2. After partitioning, set mount points for each partition\n"
                f"3. At minimum you need a root (/) partition",
                title="Manual Partitioning", border_style="yellow"
            ))
            
            with Horizontal():
                yield Button("Open cfdisk", id="cfdisk", variant="primary", classes="nav-button")
                yield Button("Refresh Partitions", id="refresh", classes="nav-button")
            
            yield Static("", id="partition_list")
            yield Static("Mount Point Assignment:", classes="subtitle")
            yield Static("", id="mount_assignment")
            
            with Horizontal():
                yield Button("Back", id="back", classes="nav-button")
                yield Button("Next", id="next", variant="primary", classes="nav-button")
        yield Footer()
    
    def on_mount(self) -> None:
        self.refresh_partitions()
    
    def refresh_partitions(self):
        """Refresh the list of partitions on the disk"""
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
                    partition_text += "  No partitions found. Use cfdisk to create partitions.\n"
            else:
                partition_text += "  Error reading partitions.\n"
            
            self.query_one("#partition_list", Static).update(partition_text)
            self.update_mount_assignment()
        except Exception as e:
            self.notify(f"Error refreshing partitions: {e}")
    
    def update_mount_assignment(self):
        """Update the mount point assignment interface"""
        if not self.partitions:
            self.query_one("#mount_assignment", Static).update("No partitions available for mount point assignment.")
            return
        
        mount_text = "Assign mount points to partitions:\n"
        for partition in self.partitions:
            current_mount = self.mount_points.get(partition, "")
            mount_text += f"  {partition}: {current_mount or '(not assigned)'}\n"
        
        mount_text += "\nCommon mount points: /, /boot, /home, /var, swap"
        self.query_one("#mount_assignment", Static).update(mount_text)
    
    @work(exclusive=True)
    async def launch_cfdisk(self):
        """Launch cfdisk for manual partitioning"""
        import subprocess
        import os
        try:
            self.notify("Launching cfdisk in separate terminal...")
            
            # Try to detect available terminal emulators
            terminal_commands = [
                ['konsole', '-e', 'cfdisk', self.disk],
                ['gnome-terminal', '--', 'cfdisk', self.disk],
                ['xterm', '-e', 'cfdisk', self.disk],
                ['alacritty', '-e', 'cfdisk', self.disk],
                ['kitty', '-e', 'cfdisk', self.disk],
                ['terminator', '-e', 'cfdisk', self.disk],
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
                # Fallback: Show message and let user run cfdisk manually
                self.notify("No terminal emulator found for cfdisk")
                self.notify("Please open a terminal and run: sudo cfdisk " + self.disk)
                self.notify("Then click 'Refresh Partitions' when done")
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
                self.notify("No partitions found. Please create partitions first.")
                return
            
            if "/" not in self.mount_points.values():
                self.notify("You must assign a root (/) mount point.")
                return
            
            # Store partition configuration and continue
            setattr(self.app, "partition_config", {
                'disk': self.disk,
                'method': 'manual',
                'partitions': self.partitions,
                'mount_points': self.mount_points
            })
            self.app.push_screen(MountPointScreen(self.partitions))

class MountPointScreen(Screen):
    def __init__(self, partitions: list):
        super().__init__()
        self.partitions = partitions
        self.mount_inputs = {}
    
    def compose(self) -> ComposeResult:
        yield Header()
        with ScrollableContainer():
            yield Static("Mount Point Assignment", classes="title")
            yield Static("Assign mount points to your partitions:")
            
            for partition in self.partitions:
                yield Label(f"{partition}:")
                yield Input(placeholder="e.g., /, /boot, /home, swap", id=f"mount_{partition}")
            
            yield Static(Panel(
                "[bold]Common mount points:[/bold]\n"
                "/ - Root filesystem (required)\n"
                "/boot - Boot partition\n"
                "/home - User home directories\n"
                "/var - Variable data\n"
                "swap - Swap partition",
                title="Mount Point Reference", border_style="blue"
            ))
            
            with Horizontal():
                yield Button("Back", id="back", classes="nav-button")
                yield Button("Next", id="next", variant="primary", classes="nav-button")
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "next":
            # Collect mount points
            mount_points = {}
            has_root = False
            
            for partition in self.partitions:
                mount_input = self.query_one(f"#mount_{partition}", Input)
                mount_point = mount_input.value.strip()
                
                if mount_point:
                    if mount_point == "/":
                        has_root = True
                    mount_points[partition] = mount_point
            
            if not has_root:
                self.notify("You must assign a root (/) mount point to one partition.")
                return
            
            # Store mount points and continue to user setup
            app = self.app
            if hasattr(app, 'partition_config') and isinstance(getattr(app, 'partition_config', None), dict):
                # Cast self.app to VoidInstallApp to access partition_config
                from typing import cast
                app_typed = cast(VoidInstallApp, self.app)
                app_typed.partition_config['mount_points'] = mount_points
            
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
    
    def compose(self) -> ComposeResult:
        yield Header()
        with ScrollableContainer():
            yield Static("Installing Void Linux", classes="title")
            yield Static("", id="current_task", classes="subtitle")
            yield Static("Setting up your system, please wait...", id="status_text")
            yield Static("", id="progress_text", classes="progress-info")
            yield ProgressBar(total=100, show_eta=True, show_percentage=True, id="progress", classes="large-progress")
            yield Log(id="log", classes="install-log")
            with Horizontal():
                yield Button("Cancel", id="cancel", variant="error", classes="install-button")
        yield Footer()
    
    def on_mount(self) -> None:
        self.call_later(self.do_install)

    @work(exclusive=True)
    async def do_install(self):
        log = self.query_one("#log", Log)
        progress = self.query_one("#progress", ProgressBar)
        current_task = self.query_one("#current_task", Static)
        progress_text = self.query_one("#progress_text", Static)
        
        try:
            # Phase 1: Dependencies and base system (0-20%)
            current_task.update("Installing Dependencies")
            progress_text.update("Setting up package manager and dependencies...")
            log.write_line("Installing dependencies...")
            
            # Smooth progress animation
            for i in range(0, 15, 2):
                progress.update(progress=i)
                await asyncio.sleep(0.2)
            
            # Run blocking functions in thread pool
            if install_partitioning_tools:
                await asyncio.to_thread(install_partitioning_tools)
            if install_all_dependencies:
                await asyncio.to_thread(install_all_dependencies)
            
            progress.update(progress=20)
            
            # Phase 2: Disk preparation (20-40%)
            current_task.update("Preparing Disk")
            progress_text.update("Partitioning and formatting disk...")
            log.write_line("Partitioning disk...")
            
            # Check if we have manual partition config
            from typing import cast
            app_typed = cast(VoidInstallApp, self.app)
            if hasattr(app_typed, 'partition_config') and app_typed.partition_config:
                config = app_typed.partition_config
                log.write_line(f"Using manual partitioning on {config.get('disk', 'unknown')}")
                for partition, mount_point in config.get('mount_points', {}).items():
                    log.write_line(f"  {partition} -> {mount_point}")
            else:
                log.write_line("Using automatic partitioning...")
            
            for i in range(20, 40, 3):
                progress.update(progress=i)
                await asyncio.sleep(0.25)
            
            # Phase 3: Base system installation (40-60%)
            current_task.update("Installing Base System")
            progress_text.update("Installing Void Linux base system...")
            log.write_line("Installing base system...")
            
            for i in range(40, 60, 2):
                progress.update(progress=i)
                await asyncio.sleep(0.3)
            
            # Phase 4: Graphics and desktop (60-80%)
            from typing import cast
            app_typed = cast(VoidInstallApp, self.app)
            if hasattr(app_typed, 'graphics_config') and app_typed.graphics_config:
                config = app_typed.graphics_config
                desktop_env = config.get('desktop_env', 'none')
                selected_profile = config.get('profile')
                
                if desktop_env != 'none' and selected_profile:
                    current_task.update(f"Installing {desktop_env.upper()}")
                    progress_text.update(f"Setting up {desktop_env} desktop environment...")
                    log.write_line(f"Installing {selected_profile.get('description', desktop_env)} profile...")
                    
                    # Install base packages from profile
                    base_packages = config.get('base_packages', [])
                    if base_packages:
                        log.write_line(f"Installing base packages: {', '.join(base_packages[:5])}{'...' if len(base_packages) > 5 else ''}")
                    
                    # Install additional packages
                    additional_packages = config.get('additional_packages', [])
                    if additional_packages:
                        log.write_line(f"Installing additional packages: {', '.join(additional_packages[:3])}{'...' if len(additional_packages) > 3 else ''}")
                
                graphics_driver = config.get('graphics_driver', 'auto')
                if graphics_driver != 'auto':
                    log.write_line(f"Installing {graphics_driver} graphics drivers...")
                
                audio_system = config.get('audio_system', 'none')
                if audio_system != 'none':
                    log.write_line(f"Setting up {audio_system} audio system...")
                
                # Log specific software installations
                if config.get('firefox'):
                    log.write_line("Installing Firefox web browser...")
                if config.get('libreoffice'):
                    log.write_line("Installing LibreOffice office suite...")
                if config.get('steam'):
                    log.write_line("Installing Steam gaming platform...")
                if config.get('cups'):
                    log.write_line("Setting up printing support (CUPS)...")
                if config.get('multimedia_codecs'):
                    log.write_line("Installing multimedia codecs...")
                if config.get('dev_tools'):
                    log.write_line("Installing development tools...")
                    
                for i in range(60, 80, 2):
                    progress.update(progress=i)
                    await asyncio.sleep(0.25)
            else:
                current_task.update("Configuring System")
                for i in range(60, 80, 4):
                    progress.update(progress=i)
                    await asyncio.sleep(0.15)
            
            # Phase 5: Bootloader and finalization (80-100%)
            current_task.update("Configuring Bootloader")
            progress_text.update("Installing and configuring GRUB bootloader...")
            log.write_line("Configuring bootloader...")
            
            for i in range(80, 95, 3):
                progress.update(progress=i)
                await asyncio.sleep(0.2)
            
            current_task.update("Finalizing Installation")
            progress_text.update("Completing installation and cleaning up...")
            log.write_line("Finishing up...")
            
            for i in range(95, 100, 1):
                progress.update(progress=i)
                await asyncio.sleep(0.1)
            
            progress.update(progress=100)
            current_task.update("Installation Complete!")
            progress_text.update("Void Linux has been successfully installed.")
            log.write_line("[green]Installation complete![/green]")
            
            # Show restart button and hide cancel button
            self.installation_complete = True
            self.show_completion_buttons()
            
        except Exception as e:
            current_task.update("Installation Failed")
            progress_text.update(f"Error occurred: {str(e)}")
            log.write_line(f"[red]Error: {e}[/red]")
    
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
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel" and not self.installation_complete:
            self.app.exit()
        elif event.button.id == "restart":
            # Restart the system
            import subprocess
            try:
                subprocess.run(["reboot"], check=True)
            except Exception as e:
                self.notify(f"Cannot restart: {e}")
        elif event.button.id == "exit_complete":
            self.app.exit()

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
