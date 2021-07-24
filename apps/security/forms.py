from django import forms
from django.utils.text import capfirst
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import urls, views

from django.utils.translation import gettext_lazy as _


class FormLogin(AuthenticationForm):
    security_code = forms.CharField(
        label=_("Código de seguridad"),
        strip=False,
        widget=forms.TextInput()
    )

    def __init__(self, request=None, *args, **kwargs):
        super(FormLogin, self).__init__(*args, *kwargs)
        security_code_max_length = self.security_code.max_length or 8
        self.fields['security_code'].max_length = security_code_max_length
        self.fields['username'].widget.attrs['maxlength'] = security_code_max_length
        if self.fields['security_code'].label is None:
            self.fields['security_code'].label = capfirst(self.security_code.verbose_name)
