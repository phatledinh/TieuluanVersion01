"""
Custom JWT Authentication for Microservices — Chapter 4.5

In a microservice architecture, each service has its own database.
The default SimpleJWT authentication tries to find the user in the local DB,
which fails in services that don't have a User table.

This custom class decodes and validates the JWT token, then creates a
lightweight user object from the token payload without hitting the DB.
"""

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


class JWTUser:
    """
    A lightweight user object built from JWT token claims.
    Used by microservices that don't have a local User table.
    """
    def __init__(self, payload):
        self.id = payload.get('user_id')
        self.pk = self.id
        self.username = payload.get('username', '')
        self.email = payload.get('email', '')
        self.role = payload.get('role', 'customer')
        self.is_authenticated = True
        self.is_active = True


class MicroserviceJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that extracts user info from token payload
    instead of looking up the user in the local database.
    """

    def get_user(self, validated_token):
        """
        Override default get_user to create a JWTUser from token payload
        instead of querying the database.
        """
        try:
            user_id = validated_token.get('user_id')
        except KeyError:
            raise InvalidToken('Token contained no recognizable user identification')

        if user_id is None:
            raise InvalidToken('Token contained no recognizable user identification')

        return JWTUser(validated_token.payload if hasattr(validated_token, 'payload') else validated_token)
