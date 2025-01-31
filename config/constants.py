"""Global constants used across the application"""

GMAIL_SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly'
]

EMAIL_DEFAULTS = {
    'imap_server': 'imap.gmail.com',
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 465,
    'max_emails': 10,
    'cache_duration': 300
}