import imaplib
import email
from pathlib import Path
from email.header import decode_header
import keyring


ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}



# HELPER

def decode_filename(name):
    if not name:
        return None

    decoded, encoding = decode_header(name)[0]

    if isinstance(decoded, bytes):
        return decoded.decode(encoding or "utf-8", errors="ignore")

    return decoded



# MAIN

def fetch_attachments(config):
    print("\n[MAIL] =============================")
    print("[MAIL] Starte Abruf")

    email_cfg = config.get("email", {}) or {}
    print(f"[MAIL CONFIG] {email_cfg}")

    if not email_cfg.get("enabled"):
        print("[MAIL] deaktiviert")
        return

    server = email_cfg.get("imap_server")

    user = keyring.get_password("SorterinoMail", "email_user")
    password = keyring.get_password("SorterinoMail", "email_pass")

    print(f"[MAIL] Server: {server}")
    print(f"[MAIL] User: {user}")

    if not server or not user or not password:
        print("[MAIL] Konfiguration unvollständig")
        return

    if not config.incoming_root:
        print("[MAIL] incoming_root fehlt")
        return

    incoming = config.incoming_root
    incoming.mkdir(parents=True, exist_ok=True)

    mail = None

    try:
        
        # CONNECT
        
        print("[MAIL] Verbinde...")
        mail = imaplib.IMAP4_SSL(server)

        mail.login(user, password)
        print("[MAIL] Login erfolgreich")

        status, _ = mail.select("INBOX")
        print(f"[MAIL] Mailbox Status: {status}")

        if status != "OK":
            print("[MAIL] Konnte INBOX nicht öffnen")
            return

        
        # SEARCH (UID!)
        
        status, messages = mail.uid("search", None, '(UNSEEN UNFLAGGED)')
        print(f"[MAIL DEBUG] MATCHING: {messages}")

        if status != "OK" or not messages or not messages[0]:
            print("[MAIL] Keine neuen Mails")
            return

        mail_ids = messages[0].split()
        print(f"[MAIL] Verarbeite {len(mail_ids)} Mail(s)")

        
        # LOOP
        
        for uid in mail_ids:
            print(f"\n[MAIL] ===== Mail UID {uid.decode()} =====")

            status, msg_data = mail.uid("fetch", uid, "(BODY.PEEK[])")

            if status != "OK":
                print("[MAIL] Fetch Fehler")
                continue

            try:
                msg = email.message_from_bytes(msg_data[0][1])
            except Exception as e:
                print(f"[MAIL] Parsing Fehler: {e}")
                continue

            saved_any = False

            
            # ATTACHMENTS
            
            for part in msg.walk():

                disposition = part.get_content_disposition()
                if disposition != "attachment":
                    continue

                filename = decode_filename(part.get_filename())
                print(f"[MAIL] Attachment gefunden: {filename}")

                if not filename:
                    print("[MAIL] Kein Dateiname → skip")
                    continue

                ext = Path(filename).suffix.lower()

                if ext not in ALLOWED_EXTENSIONS:
                    print(f"[MAIL] Extension ignoriert: {ext}")
                    continue

                filepath = incoming / filename

                # UNIQUE NAME
                counter = 1
                while filepath.exists():
                    filepath = incoming / f"{filepath.stem}_{counter}{filepath.suffix}"
                    counter += 1

                try:
                    payload = part.get_payload(decode=True)

                    if not payload:
                        print("[MAIL] Leerer Payload → skip")
                        continue

                    with open(filepath, "wb") as f:
                        f.write(payload)

                    print(f"[MAIL] gespeichert: {filepath}")
                    saved_any = True

                except Exception as e:
                    print(f"[MAIL] Speicherfehler: {e}")

            
            # FLAGGING (UID!)
            
            if saved_any:
                try:
                    mail.uid("store", uid, "+FLAGS", "(\\Flagged)")
                    print("[MAIL] Mail als verarbeitet markiert")

                    # DEBUG FLAGS
                    status, flags = mail.uid("fetch", uid, "(FLAGS)")
                    print(f"[MAIL DEBUG] FLAGS: {flags}")

                except Exception as e:
                    print(f"[MAIL] Flag Fehler: {e}")

        print("\n[MAIL] Fertig")

    except Exception as e:
        print(f"[MAIL ERROR] {e}")

    finally:
        try:
            if mail:
                mail.logout()
                print("[MAIL] Logout")
        except Exception:
            pass