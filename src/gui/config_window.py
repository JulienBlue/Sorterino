import customtkinter as ctk
from src.gui.storage_window import StorageWindow
from src.infrastructure.config.config_service import ConfigService
from src.infrastructure.system.autostart_service import AutostartService


class ConfigWindow(ctk.CTkToplevel):

    def __init__(self):
        super().__init__()

        self.config_service = ConfigService()
        self.autostart_service = AutostartService()

        self.title("Konfiguration")
        self.geometry("400x600")

        self.create_ui()
        self.load_values()

    def create_ui(self):

        # ---------------- Speicher ----------------
        self.storage_btn = ctk.CTkButton(
            self,
            text="Speicherort",
            command=self.open_storage
        )
        self.storage_btn.pack(pady=10)

        # ---------------- Automatik ----------------
        self.auto_mode_checkbox = ctk.CTkCheckBox(
            self,
            text="Automatikmodus",
            command=self.toggle_auto_mode
        )
        self.auto_mode_checkbox.pack(pady=5)

        self.autostart_checkbox = ctk.CTkCheckBox(
            self,
            text="Autostart",
            command=self.toggle_autostart
        )
        self.autostart_checkbox.pack(pady=5)

        # ---------------- Firmenprofil ----------------
        self.company_label = ctk.CTkLabel(self, text="Firmenname")
        self.company_label.pack(pady=(15, 0))

        self.company_entry = ctk.CTkEntry(self)
        self.company_entry.pack(padx=20, fill="x")

        self.keywords_label = ctk.CTkLabel(self, text="Keywords (Komma getrennt)")
        self.keywords_label.pack(pady=(10, 0))

        self.keywords_entry = ctk.CTkEntry(self)
        self.keywords_entry.pack(padx=20, fill="x")

        # Adresse
        self.street_entry = ctk.CTkEntry(self, placeholder_text="Straße")
        self.street_entry.pack(pady=(10, 0), padx=20, fill="x")

        self.zip_entry = ctk.CTkEntry(self, placeholder_text="PLZ")
        self.zip_entry.pack(padx=20, fill="x")

        self.city_entry = ctk.CTkEntry(self, placeholder_text="Stadt")
        self.city_entry.pack(padx=20, fill="x")

        # Kontakt
        self.email_entry = ctk.CTkEntry(self, placeholder_text="E-Mail")
        self.email_entry.pack(pady=(10, 0), padx=20, fill="x")

        self.phone_entry = ctk.CTkEntry(self, placeholder_text="Telefon")
        self.phone_entry.pack(padx=20, fill="x")

        # Finanzen
        self.iban_entry = ctk.CTkEntry(self, placeholder_text="IBAN")
        self.iban_entry.pack(pady=(10, 0), padx=20, fill="x")

        self.tax_entry = ctk.CTkEntry(self, placeholder_text="Steuer-ID")
        self.tax_entry.pack(padx=20, fill="x")

        # Speichern
        self.save_btn = ctk.CTkButton(
            self,
            text="Firmenprofil speichern",
            command=self.save_company_profile
        )
        self.save_btn.pack(pady=15)

    def load_values(self):
        if self.config_service.get("auto_mode"):
            self.auto_mode_checkbox.select()

        if self.config_service.get("autostart"):
            self.autostart_checkbox.select()

        company = self.config_service.get("company_profile") or {}

        address = company.get("address", {})
        contact = company.get("contact", {})
        financial = company.get("financial", {})

        # 🔥 KEIN delete() mehr für leere Felder!

        name = company.get("name", "")
        if name:
            self.company_entry.delete(0, "end")
            self.company_entry.insert(0, name)

        keywords = ", ".join(company.get("keywords", []))
        if keywords:
            self.keywords_entry.delete(0, "end")
            self.keywords_entry.insert(0, keywords)

        street = address.get("street", "")
        if street:
            self.street_entry.delete(0, "end")
            self.street_entry.insert(0, street)

        zip_code = address.get("zip", "")
        if zip_code:
            self.zip_entry.delete(0, "end")
            self.zip_entry.insert(0, zip_code)

        city = address.get("city", "")
        if city:
            self.city_entry.delete(0, "end")
            self.city_entry.insert(0, city)

        email = contact.get("email", "")
        if email:
            self.email_entry.delete(0, "end")
            self.email_entry.insert(0, email)

        phone = contact.get("phone", "")
        if phone:
            self.phone_entry.delete(0, "end")
            self.phone_entry.insert(0, phone)

        iban = financial.get("iban", "")
        if iban:
            self.iban_entry.delete(0, "end")
            self.iban_entry.insert(0, iban)

        tax = financial.get("tax_id", "")
        if tax:
            self.tax_entry.delete(0, "end")
            self.tax_entry.insert(0, tax)

    def save_company_profile(self):
        name = self.company_entry.get().strip()
        keywords = [k.strip().lower() for k in self.keywords_entry.get().split(",") if k.strip()]

        data = {
            "name": name,
            "keywords": keywords,
            "address": {
                "street": self.street_entry.get().strip(),
                "zip": self.zip_entry.get().strip(),
                "city": self.city_entry.get().strip()
            },
            "contact": {
                "email": self.email_entry.get().strip(),
                "phone": self.phone_entry.get().strip()
            },
            "financial": {
                "iban": self.iban_entry.get().strip(),
                "tax_id": self.tax_entry.get().strip()
            }
        }

        self.config_service.set("company_profile", data)
        print("✅ Firmenprofil gespeichert:", data)

    def toggle_auto_mode(self):
        self.config_service.set("auto_mode", self.auto_mode_checkbox.get() == 1)

    def toggle_autostart(self):
        value = self.autostart_checkbox.get() == 1
        self.config_service.set("autostart", value)

        if value:
            self.autostart_service.enable()
        else:
            self.autostart_service.disable()

    def open_storage(self):
        StorageWindow(self)