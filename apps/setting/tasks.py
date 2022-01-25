from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings

from newsbookbackend.celery import app

@app.task
def send_email(subject='', body='', emails=None, content_html=None):
    from django.core.mail.message import EmailMultiAlternatives
    if emails:
        email = EmailMultiAlternatives(
            subject,
            body,
            settings.EMAIL_HOST_USER,
            emails
        )
        if content_html:
            email.attach_alternative(content_html, 'text/html')
        email.send()


@app.task
def generate_notification_async(news_id):
    from apps.security.models import User
    from apps.setting.models import Notification
    from apps.main.models import News
    instance: News = News.objects.get(id=news_id)
    try:
        notifications_recurrent: Notification = Notification.objects.filter(
            type=Notification.RECURRENT,
            type_news=instance.type_news
        )
        for notification_recurrent in notifications_recurrent:
            groups = notification_recurrent.groups.all().values_list('id', flat=True)
            emails = User.objects.filter(groups__in=groups).values_list('email', flat=True)
            send_email.delay(instance.type_news.description, notification_recurrent.description, list(emails))
    except ObjectDoesNotExist:
        pass
