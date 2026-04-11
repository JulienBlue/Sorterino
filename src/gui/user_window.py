import customtkinter as ctk
from tkinter import messagebox

from src.config import Config


class UserWindow(ctk.CTkToplevel):

    def __init__(self, master=None, config=None):
        super().__init__(master)

        self.config = config if config else Config()

        self.title("Persönliche Daten")
        self.geometry("420x650")

        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        self.after(200, lambda: self.attributes("-topmost", False))

        self.create_ui()
        self.load_values()

    def create_ui(self):
        ctk.CTkLabel(self, text="Firmenname").pack(pady=(12, 0))
        self.company_entry = ctk.CTkEntry(self, placeholder_text="Firmenname")
        self.company_entry.pack(padx=20, fill="x")

        ctk.CTkLabel(self, text="Vorname").pack(pady=(10, 0))
        self.first_name_entry = ctk.CTkEntry(self, placeholder_text="Vorname")
        self.first_name_entry.pack(padx=20, fill="x")

        ctk.CTkLabel(self, text="Nachname").pack(pady=(10, 0))
        self.last_name_entry = ctk.CTkEntry(self, placeholder_text="Nachname")
        self.last_name_entry.pack(padx=20, fill="x")

        ctk.CTkLabel(self, text="Keywords (Komma getrennt)").pack(pady=(10, 0))
        self.keywords_entry = ctk.CTkEntry(self, placeholder_text="Keywords")
        self.keywords_entry.pack(padx=20, fill="x")

        self.street_entry = ctk.CTkEntry(self, placeholder_text="Straße")
        self.street_entry.pack(pady=(10, 0), padx=20, fill="x")

        self.zip_entry = ctk.CTkEntry(self, placeholder_text="PLZ")
        self.zip_entry.pack(padx=20, fill="x")

        self.city_entry = ctk.CTkEntry(self, placeholder_text="Stadt")
        self.city_entry.pack(padx=20, fill="x")

        self.email_entry = ctk.CTkEntry(self, placeholder_text="E-Mail")
        self.email_entry.pack(pady=(10, 0), padx=20, fill="x")

        self.phone_entry = ctk.CTkEntry(self, placeholder_text="Telefon")
        self.phone_entry.pack(padx=20, fill="x")

        self.iban_entry = ctk.CTkEntry(self, placeholder_text="IBAN")
        self.iban_entry.pack(pady=(10, 0), padx=20, fill="x")

        self.tax_entry = ctk.CTkEntry(self, placeholder_text="USt.-ID")
        self.tax_entry.pack(padx=20, fill="x")

        ctk.CTkButton(self, text="Speichern", command=self.save).pack(pady=15)

    def load_values(self):
        def safe_insert(entry, value):
            if value:
                entry.insert(0, value)

        company = self.config.get("company_profile") or {}
        person = company.get("person", {})
        address = company.get("address", {})
        contact = company.get("contact", {})
        financial = company.get("financial", {})

        safe_insert(self.company_entry, company.get("name"))
        safe_insert(self.first_name_entry, person.get("first_name"))
        safe_insert(self.last_name_entry, person.get("last_name"))
        safe_insert(self.keywords_entry, ", ".join(company.get("keywords", [])))
        safe_insert(self.street_entry, address.get("street"))
        safe_insert(self.zip_entry, address.get("zip"))
        safe_insert(self.city_entry, address.get("city"))
        safe_insert(self.email_entry, contact.get("email"))
        safe_insert(self.phone_entry, contact.get("phone"))
        safe_insert(self.iban_entry, financial.get("iban"))
        safe_insert(self.tax_entry, financial.get("tax_id"))

    def save(self):
        data = {
            "name": self.company_entry.get().strip(),
            "person": {
                "first_name": self.first_name_entry.get().strip(),
                "last_name": self.last_name_entry.get().strip()
            },
            "keywords": [k.strip().lower() for k in self.keywords_entry.get().split(",") if k.strip()],
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

        self.config.set("company_profile", data)
        messagebox.showinfo("Erfolg", "Daten gespeichert")
