# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import jwt
from fastapi import Request

from src.common.secrets import get_secret
from src.core.ee.iam.session.claims import AccessTokenClaims
from src.core.ee.iam.user.schema import User


class SessionService:
    def __init__(self, public_key: str, private_key: str):
        self.private_key = private_key
        self.public_key = public_key

    @staticmethod
    def load_private_key() -> str:
        private_key = get_secret("PRIVATE_KEY", None)
        if private_key:
            return private_key

        private_key_path = "keys/private_key.pem"
        try:
            with open(private_key_path) as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Private key not found at {private_key_path}")

    @staticmethod
    def load_public_key() -> str:
        public_key = get_secret("PUBLIC_KEY", None)
        if public_key:
            return public_key

        public_key_path = "keys/public_key.pem"
        try:
            with open(public_key_path) as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Public key not found at {public_key_path}")

    def generate_access_token(self, user: User, expires_in_hours: int = 24) -> str:
        import datetime

        payload: AccessTokenClaims = AccessTokenClaims(
            sub=str(user.laui),
            exp=int(datetime.datetime.now(datetime.UTC).timestamp()) + (expires_in_hours * 3600),
            iat=int(datetime.datetime.now(datetime.UTC).timestamp()),
            iss="LeastAction-API-Org1",
        )

        return jwt.encode(payload.model_dump(mode="json"), self.private_key, algorithm="RS256")

    def verify_jwt_token(self, token: str) -> AccessTokenClaims:
        try:
            decoded = jwt.decode(
                token,
                self.public_key,
                algorithms=["RS256"],
                options={"verify_exp": True},
            )
            return AccessTokenClaims(**decoded)
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {str(e)}")


def get_session_service(request: Request) -> SessionService:
    return request.app.state.session_service
