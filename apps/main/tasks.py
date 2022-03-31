from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from newsbookbackend.celery import app


@app.task
def send_email(subject='', body='', emails=None, content_html=None):
    if emails:
        try:
            email = EmailMultiAlternatives(
                subject,
                body,
                settings.EMAIL_HOST_USER,
                emails
            )
            if content_html:
                email.attach_alternative(content_html, 'text/html')
            result = email.send()
            return result
        except Exception as e:
            return e.__str__()

