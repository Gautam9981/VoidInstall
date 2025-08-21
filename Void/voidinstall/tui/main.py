
import npyscreen

class VoidInstallTUI(npyscreen.NPSAppManaged):
    def onStart(self):
        self.addForm('MAIN', MainForm, name="Void Linux Installer")

class MainForm(npyscreen.FormBaseNew):
    def create(self):
        self.add(npyscreen.TitleText, name="Welcome to Void Linux Installer!", editable=False)
        self.disk = self.add(npyscreen.TitleText, name="Disk (e.g., /dev/sda):")
        self.username = self.add(npyscreen.TitleText, name="Username:")
        self.encrypt = self.add(npyscreen.TitleSelectOne, max_height=2, value=[0], name="Encrypt root?", values=["No", "Yes"], scroll_exit=True)

        self.desktop = self.add(
            npyscreen.TitleSelectOne,
            max_height=5,
            value=[0],
            name="Desktop Environment:",
            values=["XFCE", "GNOME", "KDE", "MATE", "Cinnamon"],
            scroll_exit=True
        )

        self.install_btn = self.add(npyscreen.ButtonPress, name="Install")
        self.install_btn.whenPressed = self.on_install
        self.status = self.add(npyscreen.FixedText, value="", editable=False)

    def on_install(self):
        disk = self.disk.value
        username = self.username.value
        encrypt = self.encrypt.get_selected_objects()[0] == "Yes"
        desktop = self.desktop.get_selected_objects()[0] if self.desktop.get_selected_objects() else "XFCE"
        self.status.value = f"Would install to {disk} as {username} (encrypt: {encrypt}, desktop: {desktop})"
        self.display()

def launch_tui():
    VoidInstallTUI().run()
