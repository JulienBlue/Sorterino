"""Secure delivery of human-readable daily reports."""

from __future__ import annotations

import base64
import html
import re
import smtplib
from datetime import date, datetime
from email.message import EmailMessage

from src.database import SorterinoDatabase
from src.mail_auth import (
    MailAuthenticationError,
    load_password,
    oauth2_auth_string,
    refresh_access_token,
    secure_ssl_context,
)
from src.profile_service import ProfileService
from src.reporting import DailyReportManager, user_reason, user_target


PROVIDER_SMTP = {
    "google": ("smtp.gmail.com", 465),
    "microsoft": ("smtp.office365.com", 587),
    "apple": ("smtp.mail.me.com", 587),
    "gmx": ("mail.gmx.net", 587),
    "webde": ("smtp.web.de", 587),
    "ionos": ("smtp.ionos.de", 465),
}
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
MAX_RECIPIENTS = 20


def normalize_recipients(values):
    if isinstance(values, str):
        values = re.split(r"[,;\n]", values)
    result = []
    for value in values or []:
        address = str(value).strip().casefold()
        if address and EMAIL_PATTERN.fullmatch(address) and address not in result:
            result.append(address)
        if len(result) >= MAX_RECIPIENTS:
            break
    return result


def _sender(config):
    mode = config.get("daily_report_sender_mode", "existing")
    if mode == "dedicated":
        sender = dict(config.get("daily_report_sender") or {})
        sender.setdefault("id", "report_sender")
        sender.setdefault("auth_method", "app_password")
        return sender
    account_id = str(config.get("daily_report_sender_account_id") or "")
    account = ProfileService(config).get_email_account(account_id)
    if not account:
        raise MailAuthenticationError("Das ausgewählte Absenderkonto wurde nicht gefunden.")
    return account


def _report_bodies(report, level="compact"):
    summary = report.get("summary", {})
    attention = int(summary.get("manual", 0)) + int(summary.get("error", 0))
    title = f"Sorterino Tagesbericht – {report.get('date')}"
    text = [title, "", f"Verarbeitet: {summary.get('total', 0)}", f"Automatisch abgelegt: {summary.get('success', 0)}", f"Handlungsbedarf: {attention}"]
    successes = [item for item in report.get("items", []) if item.get("status") == "success"]
    action_items = [item for item in report.get("items", []) if item.get("status") in {"manual", "error"}]
    success_rows = []
    action_rows = []
    if successes:
        text.extend(("", "Automatisch abgelegt"))
        for item in successes:
            name = str(item.get("final_name") or item.get("original_name") or "Dokument")
            target = user_target(item)
            text.append(f"- {name} -> {target}")
            success_rows.append(
                "<tr><td>" + html.escape(name) + "</td><td>" + html.escape(target) + "</td></tr>"
            )
    if action_items:
        text.extend(("", "Handlungsbedarf"))
        for item in action_items:
            name = str(item.get("final_name") or item.get("original_name") or "Dokument")
            reason = user_reason(item)
            text.append(f"- {name}: {reason}")
            action_rows.append(
                "<tr><td>" + html.escape(name) + "</td><td>" + html.escape(reason) + "</td></tr>"
            )
    body = f"""<!doctype html><html><body style='font-family:Arial,sans-serif;color:#202124'>
<h2>{html.escape(title)}</h2>
<table cellpadding='8' style='border-collapse:collapse'><tr><td>Verarbeitet</td><td><b>{int(summary.get('total', 0))}</b></td></tr>
<tr><td>Erfolgreich abgelegt</td><td><b>{int(summary.get('success', 0))}</b></td></tr>
<tr><td>Prüfung erforderlich</td><td><b>{int(summary.get('manual', 0))}</b></td></tr>
<tr><td>Fehler</td><td><b>{int(summary.get('error', 0))}</b></td></tr></table>
{"<h3>Automatisch abgelegt</h3><table cellpadding='7' border='1' style='border-collapse:collapse'><tr><th>Dokument</th><th>Ablageort</th></tr>" + ''.join(success_rows) + "</table>" if success_rows else ""}
{"<h3>Handlungsbedarf</h3><table cellpadding='7' border='1' style='border-collapse:collapse'><tr><th>Dokument</th><th>Hinweis</th></tr>" + ''.join(action_rows) + "</table>" if action_rows else ""}
<p style='color:#666'>Automatisch durch Sorterino erstellt.</p></body></html>"""
    return title, "\n".join(text), body


def _smtp_connection(server, port):
    context = secure_ssl_context()
    if int(port) == 465:
        return smtplib.SMTP_SSL(server, int(port), context=context, timeout=30)
    smtp = smtplib.SMTP(server, int(port), timeout=30)
    smtp.ehlo()
    smtp.starttls(context=context)
    smtp.ehlo()
    return smtp


def _authenticate(smtp, config, account):
    username = str(account.get("username") or account.get("email") or "").strip()
    if not username:
        raise MailAuthenticationError("Die Absenderadresse fehlt.")
    if account.get("auth_method") == "oauth2":
        token = refresh_access_token(config, account)
        encoded = base64.b64encode(oauth2_auth_string(username, token)).decode("ascii")
        code, response = smtp.docmd("AUTH", "XOAUTH2 " + encoded)
        if code not in {235, 250}:
            raise MailAuthenticationError("Das Postfach besitzt keine Versandberechtigung.")
    else:
        password = load_password(account.get("id"))
        if not password:
            raise MailAuthenticationError("Für den Berichtsabsender ist kein Passwort gespeichert.")
        smtp.login(username, password)
    return username


def _upsert_run(database, report_date, report_path, summary):
    with database.transaction() as connection:
        connection.execute(
            "INSERT INTO report_runs(report_date, scheduled_for, report_path, summary_json) VALUES(?,?,?,?) "
            "ON CONFLICT(report_date) DO UPDATE SET report_path=excluded.report_path, summary_json=excluded.summary_json",
            (report_date, report_date, str(report_path), database.json_value(summary)),
        )
        return connection.execute("SELECT id FROM report_runs WHERE report_date=?", (report_date,)).fetchone()[0]


def deliver_daily_report(config, day=None, *, force=False):
    day = day or date.today()
    recipients = normalize_recipients(config.get("daily_report_recipients", []))
    if not recipients:
        raise MailAuthenticationError("Es wurde keine gültige Empfängeradresse eingerichtet.")
    reporter = DailyReportManager(config.logs_root)
    report_path = reporter.generate_daily_report(day)
    report = reporter.load_report(day)
    summary = report.get("summary", {})
    if not force and config.get("daily_report_only_with_activity", True) and not summary.get("total"):
        return {"status": "skipped", "reason": "Keine Aktivität", "sent": 0, "failed": 0}
    if not force and config.get("daily_report_only_with_attention", False) and not (summary.get("manual") or summary.get("error")):
        return {"status": "skipped", "reason": "Kein Handlungsbedarf", "sent": 0, "failed": 0}

    account = _sender(config)
    provider = str(account.get("provider") or "custom")
    default_server, default_port = PROVIDER_SMTP.get(provider, ("", 587))
    server = str(account.get("smtp_server") or default_server).strip()
    port = int(account.get("smtp_port") or default_port)
    if not server:
        raise MailAuthenticationError("Für den Berichtsabsender fehlt der SMTP-Server.")

    database = SorterinoDatabase(config)
    run_id = _upsert_run(database, day.isoformat(), report_path, summary)
    title, plain, html_body = _report_bodies(report, config.get("daily_report_content_level", "compact"))
    sent = failed = 0
    with _smtp_connection(server, port) as smtp:
        sender_address = _authenticate(smtp, config, account)
        for recipient in recipients:
            with database.read() as connection:
                row = connection.execute(
                    "SELECT status FROM report_deliveries WHERE report_run_id=? AND recipient=?",
                    (run_id, recipient),
                ).fetchone()
            if row and row[0] == "delivered" and not force:
                continue
            message = EmailMessage()
            message["Subject"] = title
            message["From"] = sender_address
            message["To"] = recipient
            message.set_content(plain)
            message.add_alternative(html_body, subtype="html")
            try:
                smtp.send_message(message)
                status, error, delivered = "delivered", None, datetime.now().isoformat(timespec="seconds")
                sent += 1
            except (OSError, smtplib.SMTPException) as exc:
                status, error, delivered = "failed", str(exc)[:300], None
                failed += 1
            with database.transaction() as connection:
                connection.execute(
                    "INSERT INTO report_deliveries(report_run_id,recipient,sender_account_id,status,attempt_count,attempted_at,delivered_at,error_message) "
                    "VALUES(?,?,?,?,1,CURRENT_TIMESTAMP,?,?) ON CONFLICT(report_run_id,recipient) DO UPDATE SET "
                    "sender_account_id=excluded.sender_account_id,status=excluded.status,attempt_count=report_deliveries.attempt_count+1,"
                    "attempted_at=CURRENT_TIMESTAMP,delivered_at=excluded.delivered_at,error_message=excluded.error_message",
                    (run_id, recipient, account.get("id"), status, delivered, error),
                )
    return {"status": "delivered" if not failed else "partial", "sent": sent, "failed": failed}
