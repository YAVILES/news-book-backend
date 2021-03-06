import uuid

import jsonfield
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from django_tenants.postgresql_backend.base import _check_schema_name

from apps.main.models import ModelBase


class UserManager(BaseUserManager):
    def system(self):
        user, _ = self.get_or_create(
            code='system',
            name='SYSTEM',
            last_name='SYSTEM',
            # Como es plain text deberia ser suficiente para que el usuario no haga login
            password='SYSTEM',
            status=User.INACTIVE
        )
        return user

    def web(self):
        user, _ = self.get_or_create(
            code='web',
            name='WEB',
            last_name='WEB',
            # Como es plain text deberia ser suficiente para que el usuario no haga login
            password='WEB',
            status=User.INACTIVE
        )
        return user

    def _create_user(self, code, name, last_name, password, schema_name, database='default', **extra_fields):
        """
        Creates and saves a User with the given username, email and password.
        """
        if not code:
            raise ValueError(_('The Code must be set'))
        obj = User(code=code, name=name, last_name=last_name, schema_name=schema_name, **extra_fields)
        obj.set_password(password)
        obj.save(using=database)
        return obj

    def create_user(self, code, name=None, last_name=None, password=None, schema_name="public", **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(code, name, last_name, password, schema_name, **extra_fields)

    def create_superuser(self, code, name, last_name, password, schema_name, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(code+"@"+schema_name, name, last_name, password, schema_name, **extra_fields)


class LocationUser(ModelBase):
    location = models.ForeignKey("main.Location", verbose_name=_('location'), on_delete=models.PROTECT)
    user = models.ForeignKey('User', verbose_name=_('user'), on_delete=models.PROTECT)


class User(ModelBase, AbstractBaseUser, PermissionsMixin):
    SUPERVISOR = 'SUPERVISOR'
    AUDITOR = 'AUDITOR'
    USER = 'USER'
    ADMINISTRATOR = 'ADMIN'

    TYPES_USER = (
        (SUPERVISOR, 'SUPERVISOR'),
        (AUDITOR, 'AUDITOR'),
        (USER, 'USER'),
        (ADMINISTRATOR, 'ADMINISTRADOR'),
    )
    username = None
    code = models.CharField(max_length=255, verbose_name=_('code'), null=False, unique=True, blank=True)
    email = models.EmailField(verbose_name=_('email'), null=True, blank=True, unique=False)
    name = models.CharField(max_length=255, verbose_name=_('name'), null=True)
    last_name = models.CharField(max_length=50, verbose_name=_('last name'))
    ficha = models.CharField(max_length=20, verbose_name=_('ficha'), null=True, blank=True,
                             help_text="Ficha para comparar con plataformas externas, Ej: IBARTI")
    identification_number = models.CharField(max_length=50, blank=True, verbose_name=_('identification number'))
    password = models.CharField(max_length=128, verbose_name=_('password'))
    address = models.CharField(null=True, max_length=255, verbose_name=_('address'))
    phone = models.CharField(null=True, max_length=20, verbose_name=_('phone'))
    security_code = models.CharField(null=True, max_length=20, verbose_name=_('security_code'))
    photo = models.ImageField(upload_to='photos/', null=True)
    security_user = models.ForeignKey('User', verbose_name=_('security_user'), on_delete=models.PROTECT,
                                      help_text="Usuario de seguridad", blank=True, null=True)
    type_user = models.CharField(max_length=50, choices=TYPES_USER, default=ADMINISTRATOR,
                                 verbose_name=_('type user'),
                                 help_text="Tipo de usuario. Representa el rol del usuario en el sistema")
    is_staff = models.BooleanField(verbose_name=_('is staff'), default=False)
    is_superuser = models.BooleanField(verbose_name=_('is superuser'), default=False)
    is_active = models.BooleanField(verbose_name=_('is active'), default=True)
    locations = models.ManyToManyField("main.Location", verbose_name=_('locations'), related_name='users',
                                       through=LocationUser, blank=True)
    schema_name = models.CharField(max_length=63, default="public", db_index=True, validators=[_check_schema_name])
    info = jsonfield.JSONField(default=dict)
    is_oesvica = models.BooleanField(default=False)
    last_login = models.DateTimeField(blank=True, null=True, verbose_name=_('last login'))
    last_password_change = models.DateTimeField(blank=True, null=True, auto_now_add=True,
                                                verbose_name=_('last password change'))
    jwt_id = models.UUIDField(default=uuid.uuid4, blank=True, null=True)
    last_sync_date = models.DateTimeField(null=True, blank=True, verbose_name=_('last sync date'))

    USERNAME_FIELD = 'code'
    REQUIRED_FIELDS = ['name', 'last_name', 'phone', 'schema_name']
    objects = UserManager()

    @property
    def last_ip_address(self):
        try:
            return self.info['ip']
        except (ValueError, KeyError):
            return None

    def get_short_name(self):
        return self.name

    def __str__(self):
        return "{full_name}".format(full_name=self.get_full_name())

    def get_full_name(self):
        return "{name} {last_name}".format(name=self.name, last_name=self.last_name)

    @cached_property
    def full_name(self):
        return self.get_full_name()

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
