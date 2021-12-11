from django.db import models
from django.dispatch.dispatcher import receiver
from django_tenants.models import TenantMixin, DomainMixin
from django_tenants.signals import post_schema_sync
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


@receiver(post_schema_sync, sender=TenantMixin)
def created_superuser_client(sender, **kwargs):
    client: TenantMixin = kwargs['tenant']
    connection = connections[get_tenant_database_alias()]
    connection.set_tenant(client, True)
    user = User(code=client.schema_name, name="Super", last_name="User", is_superuser=True, is_staff=True)
    user.set_password("superuser123")
    user.save()
