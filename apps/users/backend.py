from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()

        email = username or kwargs.get('email')
        if email and password:
            email = User.objects.normalize_email(email).lower()

            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return None
            else:
                if user.check_password(password) and self.user_can_authenticate(user):
                    return user
        return None
