import customtkinter as ctk


# Explicit two-theme palette. Text pairs are checked in tests against the
# backgrounds on which Sorterino uses them (normal text >= 4.5:1).
PRIMARY_TEXT = ("#1A1A1A", "#F2F2F2")
SECONDARY_TEXT = ("#4A4A4A", "#C2C2C2")
SURFACE_BG = ("#EBEBEB", "#242424")
CONTROL_BG = ("#DCE3E8", "#343A40")
CONTROL_BUTTON = ("#C3CDD5", "#46515A")
CONTROL_HOVER = ("#B2BEC8", "#56636E")
DANGER_BG = ("#E8E8E8", "#353535")
DANGER_TEXT = ("#762F2B", "#F0AAA4")


def contrast_ratio(foreground, background):
    def luminance(color):
        value = color.lstrip("#")
        channels = [int(value[index:index + 2], 16) / 255 for index in (0, 2, 4)]
        channels = [
            channel / 12.92 if channel <= 0.04045
            else ((channel + 0.055) / 1.055) ** 2.4
            for channel in channels
        ]
        return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]

    lighter, darker = sorted(
        (luminance(foreground), luminance(background)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


THEME_CONTRAST_PAIRS = {
    "Primärtext": (PRIMARY_TEXT, SURFACE_BG),
    "Sekundärtext": (SECONDARY_TEXT, SURFACE_BG),
    "Auswahltext": (PRIMARY_TEXT, CONTROL_BG),
    "Warntext": (DANGER_TEXT, DANGER_BG),
}


APPEARANCE_LABELS = {
    "Wie System": "system",
    "Hell": "light",
    "Dunkel": "dark",
}


def apply_appearance(mode):
    normalized = mode if mode in APPEARANCE_LABELS.values() else "system"
    ctk.set_appearance_mode(normalized)
    return normalized


def appearance_label(mode):
    return next((label for label, value in APPEARANCE_LABELS.items() if value == mode), "Wie System")
