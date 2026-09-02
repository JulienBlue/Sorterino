"""Pure decisions used by the GUI without depending on Tk widgets."""

import os
from pathlib import Path


def clamp_window_geometry(saved, bounds, default=(1280, 820), minimum=(1080, 700)):
    left, top, screen_width, screen_height = bounds
    try:
        width = int(saved.get("width", default[0]))
        height = int(saved.get("height", default[1]))
        x = int(saved.get("x", left + max(0, (screen_width - width) // 2)))
        y = int(saved.get("y", top + max(0, (screen_height - height) // 2)))
    except (AttributeError, TypeError, ValueError):
        width, height = default
        x = left + max(0, (screen_width - width) // 2)
        y = top + max(0, (screen_height - height) // 2)
    width = min(max(minimum[0], width), max(minimum[0], screen_width))
    height = min(max(minimum[1], height), max(minimum[1], screen_height))
    right = left + screen_width
    bottom = top + screen_height
    if x + width < left + 120 or x > right - 120:
        x = min(max(x, left), left + max(0, screen_width - width))
    if y < top or y > bottom - 80:
        y = min(max(y, top), top + max(0, screen_height - height))
    return width, height, x, y


def attention_title(count):
    if count == 1:
        return "1 Dokument braucht deine Aufmerksamkeit"
    return f"{count} Dokumente brauchen deine Aufmerksamkeit"


def attention_tab(stats):
    if stats.get("manual", 0):
        return "Zu prüfen"
    if stats.get("error", 0):
        return "Fehler"
    return "Neu"


def overview_summary(stats):
    needs_attention = int(stats.get("manual", 0)) + int(stats.get("error", 0))
    incoming = int(stats.get("incoming", 0))
    if needs_attention:
        return (
            attention_title(needs_attention),
            f"{stats.get('manual', 0)} zu prüfen · "
            f"{stats.get('error', 0)} technische Fehler",
            needs_attention,
        )
    if incoming:
        title = (
            "1 Dokument wartet auf Verarbeitung"
            if incoming == 1
            else f"{incoming} Dokumente warten auf Verarbeitung"
        )
        return (
            title,
            "Die Dokumente liegen im Eingangsordner und können jetzt verarbeitet werden.",
            incoming,
        )
    return "Alles erledigt", "Sorterino hat momentan keine offenen Dokumente.", 0


def same_document_path(first, second):
    if first is None or second is None:
        return False
    try:
        return os.path.normcase(str(Path(first).resolve())) == os.path.normcase(
            str(Path(second).resolve())
        )
    except OSError:
        return os.path.normcase(str(first)) == os.path.normcase(str(second))


def live_status_decision(
    running,
    incoming,
    manual,
    errors,
    readiness_issues,
    new_incoming=False,
):
    if running:
        return "Verarbeitung läuft …", "running"
    issue_count = len(readiness_issues or [])
    if issue_count:
        label = "Einrichtung prüfen" if issue_count == 1 else f"Einrichtung prüfen · {issue_count} Punkte"
        return label, "configuration"
    attention = int(manual or 0) + int(errors or 0)
    if attention:
        label = (
            "1 Dokument braucht Aufmerksamkeit"
            if attention == 1
            else f"{attention} Dokumente brauchen Aufmerksamkeit"
        )
        return label, "attention"
    if incoming:
        label = "1 neues Dokument" if new_incoming and incoming == 1 else f"{incoming} Dokumente im Eingang"
        return label, "incoming"
    return "Sorterino ist einsatzbereit", "ready"
