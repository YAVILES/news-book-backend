from django.db import models
from django_tenants.models import TenantMixin
import secrets
from django.contrib.postgres.fields import ArrayField


class APIConsumer(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    token = models.CharField(max_length=64, unique=True, editable=False)
    is_active = models.BooleanField(default=True)
    has_full_access = models.BooleanField(default=False)  # Nuevo campo
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True)
    usage_count = models.PositiveIntegerField(default=0)

    class Meta:
        app_label = 'api'

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(48)
        super().save(*args, **kwargs)

    def can_access_tenant(self, tenant):
        return self.has_full_access or APIConsumerTenant.objects.filter(
            consumer=self,
            tenant=tenant
        ).exists()


class APIConsumerTenant(models.Model):
    consumer = models.ForeignKey(APIConsumer, on_delete=models.CASCADE)
    tenant = models.ForeignKey('customers.Client', on_delete=models.CASCADE)
    allowed_paths = ArrayField(
        models.CharField(max_length=200),
        default=list,
        help_text="Paths permitidos ej: ['/api/api/novelties/']"
    )
    extra_permissions = models.JSONField(default=dict, blank=True)

    class Meta:
        app_label = 'api'
        unique_together = ('consumer', 'tenant')


class FacialRecognitionEvent(models.Model):
    tenant = models.ForeignKey('customers.Client', on_delete=models.CASCADE)
    user_id = models.CharField(max_length=100)
    event_time = models.DateTimeField()
    raw_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['event_time']),
        ]
        ordering = ['-event_time']

    def __str__(self):
        return f"{self.user_id} - {self.event_time}"