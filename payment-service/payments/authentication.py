from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

class JWTUser:
    def __init__(self, payload):
        self.id = payload.get('user_id')
        self.pk = self.id
        self.username = payload.get('username', '')
        self.email = payload.get('email', '')
        self.role = payload.get('role', 'customer')
        self.is_authenticated = True
        self.is_active = True

class MicroserviceJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        try:
            user_id = validated_token.get('user_id')
        except KeyError:
            raise InvalidToken('Token contained no recognizable user identification')

        if user_id is None:
            raise InvalidToken('Token contained no recognizable user identification')

        return JWTUser(validated_token.payload if hasattr(validated_token, 'payload') else validated_token)
