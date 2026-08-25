import os
import threading
import time
from pathlib import Path

from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, jsonify

from crypto_engine import encrypt_file, decrypt_file
from email_alerts import load_email_profiles, send_key_email_with_override
import json
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
ENCRYPTED_DIR = BASE_DIR / "encrypted"
DECRYPTED_DIR = BASE_DIR / "decrypted"
CONFIG_PATH = BASE_DIR / "config.json"

for d in (UPLOAD_DIR, ENCRYPTED_DIR, DECRYPTED_DIR):
    d.mkdir(exist_ok=True)


app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")  # for flash messages / demo

email_profiles = load_email_profiles()

# System email sender settings (read from environment variables)
SYSTEM_SENDER_EMAIL = os.environ.get("SYSTEM_EMAIL_SENDER", "")
SYSTEM_SENDER_PASSWORD = os.environ.get("SYSTEM_EMAIL_PASSWORD", "")

# Current email settings; set only from the web UI.
current_recipient_email = None
current_sender_email = None

def send_pin_email(pin: str) -> None:
    # Email the PIN using dynamic credentials if provided, otherwise fallback to env vars.
    global current_recipient_email, current_sender_email
    
    sender_email = current_sender_email or SYSTEM_SENDER_EMAIL
    sender_password = SYSTEM_SENDER_PASSWORD

    if not (email_profiles and sender_email and sender_password and current_recipient_email):
        return

    # Use the first email profile as SMTP template (server/port/TLS), but override sender + recipients
    template = email_profiles[0]
    send_key_email_with_override(
        template=template,
        sender_email=sender_email,
        sender_password=sender_password,
        recipients=[current_recipient_email],
        password=pin,
    )


@app.route("/")
def index():
    return render_template(
        "index.html",
        current_recipient=current_recipient_email,
        current_sender=current_sender_email,
    )


@app.route("/set_email_settings", methods=["POST"])
def set_email_settings():
    global current_recipient_email, current_sender_email
    receiver = request.form.get("recipient_email", "").strip()
    sender = request.form.get("sender_email", "").strip()

    if not receiver:
        flash("Receiver email is required.", "error")
    else:
        current_recipient_email = receiver
        if sender:
            current_sender_email = sender
            flash(f"Email settings updated. Keys will be sent from {sender} to {receiver}.", "success")
        else:
            current_sender_email = None
            flash(f"Receiver updated to {receiver}, using default sender.", "success")

    return redirect(url_for("index"))


@app.route("/encrypt", methods=["POST"])
def encrypt_route():
    if "file" not in request.files:
        flash("No file part in the request.", "error")
        return redirect(url_for("index"))

    file = request.files["file"]
    if file.filename == "":
        flash("No file selected.", "error")
        return redirect(url_for("index"))

    pin = request.form.get("pin", "").strip()
    if not pin or len(pin) != 6 or not pin.isdigit():
        flash("A 6-digit PIN is required for encryption.", "error")
        return redirect(url_for("index"))

    filename = os.path.basename(file.filename)
    upload_path = UPLOAD_DIR / filename
    file.save(upload_path)

    enc_filename = filename + ".enc"
    enc_path = ENCRYPTED_DIR / enc_filename

    try:
        encrypt_file(str(upload_path), str(enc_path), pin)
        send_pin_email(pin)
    except Exception as e:
        flash(f"Encryption failed: {e}", "error")
        return redirect(url_for("index"))

    flash(f"File encrypted successfully as {enc_filename}. 6-digit PIN emailed to receiver.", "success")
    return redirect(url_for("download_encrypted", filename=enc_filename))


@app.route("/encrypted/<path:filename>")
def download_encrypted(filename):
    return send_from_directory(ENCRYPTED_DIR, filename, as_attachment=True)


@app.route("/decrypt", methods=["POST"])
def decrypt_route():
    password = request.form.get("password", "").strip()
    if not password:
        flash("Decryption password is required.", "error")
        return redirect(url_for("index"))

    if "enc_file" not in request.files:
        flash("No encrypted file part in the request.", "error")
        return redirect(url_for("index"))

    file = request.files["enc_file"]
    if file.filename == "":
        flash("No encrypted file selected.", "error")
        return redirect(url_for("index"))

    filename = os.path.basename(file.filename)
    upload_path = UPLOAD_DIR / filename
    file.save(upload_path)

    # Build decrypted output filename: keep original extension and append _decrypted before it.
    if filename.endswith(".enc"):
        base = filename[:-4]  # drop .enc -> original name with extension
        name_root, ext = os.path.splitext(base)
        dec_filename = f"{name_root}_decrypted{ext or ''}"
    else:
        name_root, ext = os.path.splitext(filename)
        dec_filename = f"{name_root}_decrypted{ext or ''}"

    dec_path = DECRYPTED_DIR / dec_filename

    try:
        decrypt_file(str(upload_path), str(dec_path), password)
    except Exception as e:
        # Log detailed error to console for debugging (e.g., InvalidTag on wrong password)
        print("[Decrypt] Error while decrypting file:", repr(e))
        flash(
            "Decryption failed: wrong PIN or corrupted file. "
            "Use the exact 6-digit PIN provided during encryption.",
            "error",
        )
        return redirect(url_for("index"))

    flash(f"File decrypted successfully as {dec_filename}.", "success")
    return send_from_directory(DECRYPTED_DIR, dec_filename, as_attachment=True)


if __name__ == "__main__":
    # Debug mode is fine for development / academic project.
    app.run(debug=True)
