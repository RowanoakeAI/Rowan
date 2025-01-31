"""Constants used for email configuration"""

SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly'
]

DEFAULT_EMAIL_CONFIG = {
    'imap_server': 'imap.gmail.com',
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 465,
    'max_emails': 10,
    'cache_duration': 300
}