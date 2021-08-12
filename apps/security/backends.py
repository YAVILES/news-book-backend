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
            user = UserModel._default_manager.get_by_natural_key(str(username).lower())
        except UserModel.DoesNotExist:
            raise exceptions.AuthenticationFailed('El usuario no existe')
        else:
            if not user.is_superuser:
                if request.data and 'security_code' in request.data:
                    security_code = request.data['security_code']
                    if user_verified_security_code(user, security_code):
                        return user
                    else:
                        raise exceptions.AuthenticationFailed('Código de seguridad inválido')
                else:
                    return user
            else:
                return user



