from django.db import models
from django.dispatch.dispatcher import receiver
from django_tenants.migration_executors.base import run_migrations
from django_tenants.models import TenantMixin, DomainMixin
from django_tenants.signals import post_schema_sync, schema_migrated
from django.db import connections
from django_tenants.utils import get_tenant_database_alias
from apps.security.models import User


class Client(TenantMixin):
    name = models.CharField(max_length=100)
    paid_until = models.DateField()
    on_trial = models.BooleanField()
    created_on = models.DateField(auto_now_add=True)

    # default true, schema will be automatically created and synced when it is saved
    auto_create_schema = True

    def __str__(self):
        return self.name


class Domain(DomainMixin):

    def __str__(self):
        return self.domain


@receiver(schema_migrated, sender=run_migrations)
def handle_schema_migrated(sender, **kwargs):
    schema_name = kwargs['schema_name']
    connection = connections[get_tenant_database_alias()]
    connection.set_tenant(Client.objects.get(schema_name=schema_name), True)
    code = 'admin@' + schema_name
    user, created = User.objects.get_or_create(
        code=code, name="Super", last_name="User", schema_name=schema_name, is_superuser=True, is_staff=True
    )
    if created:
        user.set_password("admin")
        user.save()

