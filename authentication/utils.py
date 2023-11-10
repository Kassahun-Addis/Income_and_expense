from django.contrib.auth.tokens import PasswordResetTokenGenerator
from six import text_type


class token_generator(PasswordResetTokenGenerator):
#class AppToxkenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return (text_type(user.is_active) + text_type(user.pk) + text_type(timestamp))


account_activation_token = token_generator()
#account_activation_token = AppToxkenGenerator()