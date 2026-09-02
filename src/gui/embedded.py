import customtkinter as ctk


class EmbeddedPage(ctk.CTkFrame):
    """A view rendered inside the persistent main-window shell."""

    help_context = "overview"

    def __init__(self, master, **kwargs):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)

    @property
    def navigator(self):
        window = self.winfo_toplevel()
        return window if hasattr(window, "open_view") else None

    def open_page(self, factory, nav_key=None):
        if self.navigator:
            self.navigator.open_view(factory, nav_key)

    def finish(self):
        if self.navigator:
            self.navigator.go_back()
