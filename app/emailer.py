import smtplib
import ssl
from email.message import EmailMessage
from .utils_cfg import get_cfg

def send_code(email: str, code: str) -> bool:
    provider = get_cfg("SMTP_PROVIDER").lower()
    presets = {
        "gmail": {"host": "smtp.gmail.com", "port": 465, "tls": "ssl"},
        "qq": {"host": "smtp.qq.com", "port": 465, "tls": "ssl"},
        "outlook": {"host": "smtp.office365.com", "port": 587, "tls": "starttls"},
        "sendgrid": {"host": "smtp.sendgrid.net", "port": 465, "tls": "ssl"},
    }
    preset = presets.get(provider, {})
    host = get_cfg("SMTP_HOST") or preset.get("host") or ""
    port = int(get_cfg("SMTP_PORT") or preset.get("port") or 465)
    tls_mode = (get_cfg("SMTP_TLS") or preset.get("tls") or "ssl").lower()
    user = get_cfg("SMTP_USER") or ("apikey" if provider == "sendgrid" else "")
    pwd = get_cfg("SMTP_PASS")
    sender = get_cfg("SMTP_FROM") or user
    timeout = int(get_cfg("SMTP_TIMEOUT") or "10")
    debug = get_cfg("SMTP_DEBUG") == "1"
    if not host or not user or not pwd or not sender:
        return False
    msg = EmailMessage()
    msg["Subject"] = "Your verification code"
    msg["From"] = sender
    msg["To"] = email
    msg.set_content(f"Your verification code is: {code}")
    try:
        verify = (get_cfg("SMTP_VERIFY") or "1") != "0"
        context = ssl.create_default_context() if verify else ssl._create_unverified_context()
        if tls_mode == "starttls":
            server = smtplib.SMTP(host, port, timeout=timeout)
            server.ehlo()
            server.starttls(context=context)
        else:
            server = smtplib.SMTP_SSL(host, port, context=context, timeout=timeout)
        server.login(user, pwd)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        if debug:
            try:
                print("SMTP_SEND_FAIL", str(e))
            except Exception:
                pass
        return False
