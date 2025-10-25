import re
import dns.resolver
import socket
import smtplib

# Load disposable domains (expandable list)
DISPOSABLE_DOMAINS = {
    "mailinator.com",
    "tempmail.com",
    "10minutemail.com",
    "guerrillamail.com"
}

def is_valid_syntax(email):
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None

def is_disposable(email):
    domain = email.split("@")[1].lower()
    return domain in DISPOSABLE_DOMAINS

def get_mx_record(domain):
    try:
        answers = dns.resolver.resolve(domain, "MX")
        return sorted(answers, key=lambda r: r.preference)[0].exchange.to_text()
    except Exception:
        return None

def smtp_handshake_verify(mx_record, email):
    try:
        # Establish connection
        server = smtplib.SMTP(mx_record, 25, timeout=10)
        server.ehlo_or_helo_if_needed()

        # Fake sender (just for handshake)
        server.mail("check@example.com")

        # Check recipient
        code, _ = server.rcpt(email)

        server.quit()

        # 250 means OK / accepted
        return code == 250
    except Exception:
        return False

def verify_email(email):
    if not is_valid_syntax(email):
        return False, "Invalid syntax"

    if is_disposable(email):
        return False, "Disposable email address"

    domain = email.split("@")[1]
    mx = get_mx_record(domain)
    if not mx:
        return False, "No MX record found"

    if not smtp_handshake_verify(mx, email):
        return False, "Mailbox does not exist or SMTP check failed"

    return True, "Email is valid and mailbox exists"

if __name__ == "__main__":
    test_email = "gouravbirwaz@gmail.com"
    status, message = verify_email(test_email)
    print(f"Email: {test_email}\nStatus: {status}\nInfo: {message}")