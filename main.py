import os
import sys
import random
import uuid
import hashlib
import configparser
import smtplib
import requests
from email.message import EmailMessage
from datetime import datetime
from colorama import Fore, Style, init


init(autoreset=True)

__version__ = "6.0"

# Configuration
CONFIG_FILE = "config.ini"
LICENSE_URL = "https://pastebin.com/raw/4Tmd7f6H"
TOKEN_FILE = "token.dat"

def show_banner():
    print(f"""{Fore.BLUE}
_________________________________________________________
/                                                        \\
|   ██████╗███████╗ ██████╗     ██████╗███████╗ ██████╗   |
|  ██╔════╝██╔════╝██╔═══██╗   ██╔════╝██╔════╝██╔═══██╗  |
|  ██║     █████╗  ██║   ██║   ██║     █████╗  ██║   ██║  |
|  ██║     ██╔══╝  ██║   ██║   ██║     ██╔══╝  ██║   ██║  |
|  ╚██████╗██║     ╚██████╔╝   ╚██████╗██║     ╚██████╔╝  |
|   ╚═════╝╚═╝      ╚═════╝     ╚═════╝╚═╝      ╚═════╝   |
|---------------------------------------------------------|
|                 CEO-CFO SENDER  v6.0                    |
|                      ────────────                       |
|       [🔒]  Enterprise Secure Channel  [🔒]              |
|_________________________________________________________|
{Style.RESET_ALL}""")

def get_device_id():
    mac = uuid.getnode().to_bytes(6, byteorder='big').hex()
    return hashlib.sha256(mac.encode()).hexdigest()

def validate_license(license_key):
    device_id = get_device_id()
    try:
        response = requests.get(LICENSE_URL)
        if response.status_code == 200:
            return f"{license_key}:{device_id}" in response.text
        return False
    except:
        return False

def check_license():
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r") as f:
                license_key, stored_device = f.read().split(':')
                return license_key.strip() != "" and stored_device.strip() == get_device_id()
        except:
            pass
    return False

def register_flow():
    device_id = get_device_id()
    print(f"\n{Fore.CYAN}1. Login with existing license")
    print(f"2. Register new device")
    print(f"3. Exit{Style.RESET_ALL}")
    
    while True:
        choice = input(f"{Fore.YELLOW}Choose option: ").strip()
        
        if choice == '1':
            license_key = input(f"{Fore.CYAN}Enter license key: ").strip()
            if validate_license(license_key):
                with open(TOKEN_FILE, "w") as f:
                    f.write(f"{license_key}:{device_id}")
                print(f"{Fore.GREEN}✅ Login successful!")
                return True
            print(f"{Fore.RED}❌ Invalid license key!")
            
        elif choice == '2':
            print(f"\n{Fore.YELLOW}Your Device ID: {Fore.WHITE}{device_id}")
            print(f"\n{Fore.CYAN}Send this ID to @yungkiddo to receive license key")
            input(f"\n{Fore.YELLOW}Press Enter to exit...")
            sys.exit()
            
        elif choice == '3':
            sys.exit()
            
        else:
            print(f"{Fore.RED}Invalid choice")

def load_recipients(filename, config):
    """Load recipients with new format"""
    recipients = []
    use_sender = config['Email'].getboolean('use_senderemail', False)
    required_fields = 5 if use_sender else 4

    with open(filename, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            parts = line.split('|')
            if len(parts) < required_fields:
                print(f"{Fore.YELLOW}⚠️ Line {line_num}: Requires {required_fields} fields. Got: {line}")
                continue

            try:
                recipient = {
                    'email': parts[0].strip(),
                    'recipientname': parts[1].strip(),
                    'sender_name': parts[2].strip(),
                    'company_name': parts[4].strip() if use_sender else parts[3].strip()
                }
                
                if use_sender:
                    recipient['sender_email'] = parts[3].strip()
                
                recipients.append(recipient)
            except IndexError as e:
                print(f"{Fore.RED}⚠️ Line {line_num}: Invalid format ({str(e)})")
                continue
    return recipients

def send_email(smtp_cfg, recipient, subject, body_template, config):
    """Send email with new template variables"""
    try:
        msg = EmailMessage()
        use_sender = config['Email'].getboolean('use_senderemail', False)

        # Determine sender email
        from_email = recipient.get('sender_email') if use_sender else smtp_cfg.get('senderemail')
        reply_to = config['Email'].get('replyto', '')  # Always from config

        # Prepare template variables
        recipient_name = recipient.get('recipientname', '')
        email_parts = recipient['email'].split('@')
        
        template_vars = {
            'email': recipient['email'],
            'firstnm': recipient_name.split()[0] if recipient_name else '',
            'sender_name': recipient['sender_name'],
            'reply_to': reply_to,
            'sender_email': from_email,
            'company_name': recipient['company_name'],
            'current_date': datetime.now().strftime("%Y-%m-%d"),
            'email_domain': email_parts[1] if len(email_parts) > 1 else '',
            'random_id': f"{random.randint(10000000, 99999999):08d}",
        }

        # Format message body
        body = body_template.format(**template_vars)

        # Configure email headers
        msg['From'] = f"{recipient['sender_name']} <{from_email}>"
        msg['To'] = recipient['email']
        msg['Reply-To'] = reply_to
        msg['Subject'] = subject
        msg.set_content(body)

        # SMTP Connection
        if smtp_cfg.getboolean('usessl'):
            server = smtplib.SMTP_SSL(smtp_cfg.get('host'), smtp_cfg.getint('port'))
        else:
            server = smtplib.SMTP(smtp_cfg.get('host'), smtp_cfg.getint('port'))
            server.starttls()

        server.login(smtp_cfg.get('username'), smtp_cfg.get('password'))
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"{Fore.RED}✗ Failed {recipient['email']}: {str(e)}")
        return False

def main():
    show_banner()
    
    if not check_license():
        if not register_flow():
            sys.exit(1)

    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    
    try:
        recipients = load_recipients(config['Email']['recipientsfile'], config)
        with open(config['Email']['bodyfile']) as f:
            body_template = f.read()
            
        subjects = [s.strip() for s in config['Email']['subject'].split(':') if s.strip()]
        smtp_sections = [s for s in config.sections() if s.startswith('SMTP')]
        
        if not recipients:
            raise ValueError("No valid recipients found")
        if not smtp_sections:
            raise ValueError("No SMTP configurations found")

    except Exception as e:
        print(f"{Fore.RED}Config error: {str(e)}")
        sys.exit(1)

    print(f"\n{Fore.GREEN}🚀 Starting email campaign ({len(recipients)} recipients)...\n")
    
    successful = 0
    for idx, recipient in enumerate(recipients, 1):
        smtp_section = random.choice(smtp_sections)
        subject = random.choice(subjects)
        
        status = send_email(config[smtp_section], recipient, subject, body_template, config)
        if status:
            successful += 1
            status_msg = f"{Fore.GREEN}✓ Success"
        else:
            status_msg = f"{Fore.RED}✗ Failed"
            
        print(f"[{idx}/{len(recipients)}] {status_msg}: {recipient['email']}")

    print(f"\n{Fore.CYAN}Campaign complete: {successful}/{len(recipients)} emails sent successfully")

if __name__ == "__main__":
    main()