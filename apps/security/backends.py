from django.contrib.auth.backends import ModelBackend
from rest_framework import exceptions
from django.contrib.auth import get_user_model
UserModel = get_user_model()


def user_verified_security_code(user, security_code: str = None):
    """
    Reject users with is_active=False. Custom user models that don't have
    that attribute are allowed.
    """
    user_security_code = getattr(user, 'security_code', None)
    return user_security_code == security_code


class CustomAuthenticationBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        if username is None or password is None:
            return
        try:
            user = UserModel._default_manager.get_by_natural_key(username)
        except UserModel.DoesNotExist:
            raise exceptions.AuthenticationFailed({"error": 'El usuario no existe'})
        else:
            if hasattr(request, 'data'):
                security_code = request.data.get('security_code', None)
                if user_verified_security_code(user, security_code) or not security_code:
                    return user
                else:
                    raise exceptions.AuthenticationFailed({"error": 'Código de seguridad inválido'})
            else:
                return user



