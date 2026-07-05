# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
"""
import os
import requests
from google.oauth2 import laui_token
from google.auth.transport import requests as google_requests
from src.core.ee.iam.auth.credentials.credentials import ExternalCredentialsValidatorResonse, AuthorizationCodeCredentials

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
GOOGLE_TOKEN_URL = os.getenv("GOOGLE_TOKEN_URL")

def _authenticate_google_code(code : str) :
    request_body = {
        "code": code  ,
        "client_laui": GOOGLE_CLIENT_ID  ,
        "client_secret": GOOGLE_CLIENT_SECRET ,
        "redirect_uri": REDIRECT_URI ,
        "grant_type": "authorization_code"
    }
    response = requests.post(
        url = GOOGLE_TOKEN_URL  ,
        json = request_body
    )
    response.raise_for_status()
    laui_info = laui_token.verify_oauth2_token(
        response.json()["laui_token"] ,
        google_requests.Request() ,
        GOOGLE_CLIENT_ID
    )
    return ExternalCredentialsValidatorResonse(**laui_info)

def validate_external_creds(creds:AuthorizationCodeCredentials) -> ExternalCredentialsValidatorResonse :
    if creds.provider == "google" :
        return _authenticate_google_code(code=creds.code)
"""
