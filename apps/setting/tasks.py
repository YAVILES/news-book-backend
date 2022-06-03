import datetime

from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q

from newsbookbackend.celery import app


@shared_task
def send_email(subject='', body='', emails=None, content_html=None):
    from django.core.mail.message import EmailMultiAlternatives
    from django.conf import settings
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
            emails = User.objects.filter(
                groups__id__in=groups, is_active=True, email__isnull=False
            ).values_list('email', flat=True)
            send_email(instance.type_news.description, notification_recurrent.description, list(emails))
    except ObjectDoesNotExist:
        pass


@app.task
def generate_notification_not_fulfilled(notification_id: str, schedule_id: str):
    from apps.setting.models import Notification
    from apps.security.models import User
    from apps.main.models import News, Schedule, Location

    try:
        notification: Notification = Notification.objects.get(pk=notification_id)
        schedule: Schedule = Schedule.objects.get(pk=schedule_id)
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        groups = notification.groups.all().values_list('id', flat=True)
        for location in Location.objects.filter(is_active=True):
            exists = News.objects.filter(
                type_news_id=notification.type_news.id, created__date=today,
                created__time__range=(schedule.start_time, schedule.final_hour),
                location_id=location.id
            ).exists()
            if not exists:
                emails = User.objects.filter(
                    Q(groups__id__in=groups) & Q(Q(locations__in=[location.id]) | Q(is_superuser=True))
                ).values_list('email', flat=True).distinct()
                send_email(
                    notification.type_news.description,
                    notification.description + ' - NO CUMPLIDA EN ' + location.name,
                    list(emails)
                )
    except ObjectDoesNotExist:
        pass
