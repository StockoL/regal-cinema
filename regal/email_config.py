"""Email settings, read from the environment like every other secret.
Django 6.1 configures sending through MAILERS rather than the older
EMAIL_* settings."""

CONSOLE = 'django.core.mail.backends.console.EmailBackend'
SMTP = 'django.core.mail.backends.smtp.EmailBackend'


def email_settings(environ):
    """Gmail when its app password is set, the console otherwise. The
    console prints each email instead of sending it, so local work and
    tests never send anything by accident."""
    user = environ.get('EMAIL_HOST_USER', '')
    password = environ.get('EMAIL_HOST_PASSWORD', '')
    if password:
        mailer = {
            'BACKEND': SMTP,
            'OPTIONS': {
                'host': 'smtp.gmail.com',
                'port': 587,
                'use_tls': True,
                'username': user,
                'password': password,
            },
        }
    else:
        mailer = {'BACKEND': CONSOLE}
    sender = user or 'webmaster@localhost'
    return {
        'DEFAULT_FROM_EMAIL': f'Regal Cinema <{sender}>',
        'MAILERS': {'default': mailer},
    }
