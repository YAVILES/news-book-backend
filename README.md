# news-book-backend
Libro de Novedades backend Django tenancy

# migrate_schemas
Migrate inicial: python manage.py migrate_schemas --shared
python manage.py migrate_schemas --schema=dev
python manage.py migrate_schemas --executor=parallel
El parallelejecutor acepta las siguientes configuraciones:

# Crear un inquilino
# create your public tenant
tenant = Client(schema_name='public', name='Schemas Inc.', paid_until='2025-12-05',on_trial=False)
tenant.save()

# Add one or more domains for the tenant
domain = Domain()
domain.domain = 'my-domain.com' # don't add your port or www here! on a local server you'll want to use localhost here
domain.tenant = tenant
domain.is_primary = True
domain.save()

# create your first real tenant
python manage.py tenant_command loaddata --schema=public --name='Fonzy Tenant' --paid_until=2020-12-05 --on_trial=True
from apps.customers.models import Client, Domain
tenant = Client(schema_name='tenant1', name='Fonzy Tenant', paid_until='2025-12-05', on_trial=True)
tenant.save() # migrate_schemas automatically called, your tenant is ready to be used!

# Add one or more domains for the tenant
domain = Domain()
domain.domain = 'tenant.my-domain.com' # don't add your port or www here!
domain.tenant = tenant
domain.is_primary = True
domain.save()

# Comandos de gestión
foo/management/commands/do_foo.py
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    def handle(self, *args, **options):
        do_foo()
        
./manage.py tenant_command do_foo --schema=customer1
Si omite el schemaargumento, el shell interactivo le pedirá que seleccione uno.


TENANT_PARALLEL_MIGRATION_MAX_PROCESSES (predeterminado: 2): número máximo de procesos para el grupo de migración (esto es para evitar agotar el grupo de conexiones de la base de datos)
TENANT_PARALLEL_MIGRATION_CHUNKS (predeterminado: 2): número de migraciones que se enviarán a la vez a cada trabajador

# tenant_command
python manage.py tenant_command loaddata --schema=customer1

# Crea superusuario
python manage.py tenant_command createsuperuser --code=admin --schema=public

# Señales
Hay varias señales

`post_schema_sync` se llamará después de que se cree un esquema a partir del método de guardar en la clase de inquilino.

`schema_needs_to_be_sync`se llamará si es necesario migrar el esquema. `auto_create_schema`(en el modelo de inquilino) debe establecerse en False para que se llame a esta señal. Esta señal es muy útil cuando los inquilinos se crean a través de un proceso en segundo plano como el apio.

`schema_migrated` se llamará una vez que las migraciones terminen de ejecutarse para un esquema.

`schema_migrate_message`se llamará después de cada migración con el mensaje de la migración. Esta señal es muy útil cuando se trata de barras de proceso / estado.

Ejemplo

@receiver(schema_needs_to_be_sync, sender=TenantMixin)
def created_user_client_in_background(sender, **kwargs):
    client = kwargs['tenant']
    print ("created_user_client_in_background %s" % client.schema_name)
    from clients.tasks import setup_tenant
    task = setup_tenant.delay(client)

@receiver(post_schema_sync, sender=TenantMixin)
def created_user_client(sender, **kwargs):

    client = kwargs['tenant']

    # send email to client to as tenant is ready to use

@receiver(schema_migrated, sender=run_migrations)
def handle_schema_migrated(sender, **kwargs):
    schema_name = kwargs['schema_name']

    # recreate materialized views in the schema

@receiver(schema_migrate_message, sender=run_migrations)
def handle_schema_migrate_message(**kwargs):
    message = kwargs['message']
    # recreate materialized views in the schema
    
# PostGIS
Si desea ejecutar PostGIS, agregue lo siguiente a su archivo de configuración de Django

ORIGINAL_BACKEND = "django.contrib.gis.db.backends.postgis"


# migrate_schemas en paralelo
Puede ejecutar migraciones de inquilinos en paralelo de esta manera:

python manage.py migrate_schemas --executor=multiprocessing

# collectstatic
python manage.py collectstatic_schemas --schema=your_tenant_schema_name