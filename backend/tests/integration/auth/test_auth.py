# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.

import pytest

from src.core.db.types import MongoDatabase

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
async def database_cleanup(test_database: MongoDatabase):
    await test_database.items.drop()
    await test_database.links.delete_many({})
    await test_database.users.delete_many({})
    yield
    await test_database.items.drop()
    await test_database.links.drop()
    await test_database.users.delete_many({})


# async def test_auth(unauthenticated_client: TestClient, test_database: MongoDatabase):

#     username = "abc"
#     password = "abc"
#     email = "abc@gmail.com"

#     response = execute_request(
#         client=unauthenticated_client,
#         request=TestRequest(
#             url="/api/v1/signup",
#             method="post",
#             json={
#                 "username": username,
#                 "email": email,
#                 "password": password
#             }
#         )
#     )
#     assert response.status_code == 200
#     user = await test_database.users.find_one({"username": username})
#     assert user != None
#     assert user["email"] == email
#     user_laui = user["_id"]

#     response = execute_request(
#         client=unauthenticated_client,
#         request=TestRequest(
#             url="/api/v1/check_frontend_token_present",
#             method="get"
#         )
#     )
#     assert response.status_code == 422

#     callback_redirect_uri = "http://localhost:8001/client/callback"
#     state = str(ObjectId())

#     response = execute_request(
#         client=unauthenticated_client,
#         request=TestRequest(
#             url="/api/v1/auth",
#             method="get",
#             params={
#                 "client_id": "client",
#                 "redirect_uri": callback_redirect_uri,
#                 "state": state
#             },
#             follow_redirects=False
#         ),
#     )
#     assert response.status_code == 303
#     assert response.headers["Location"] == "http://localhost:5173/public/login"
#     oauth_flow_cookie = response.cookies.get("oauth_flow")
#     assert oauth_flow_cookie != None


#     response = execute_request(
#         client=unauthenticated_client,
#         request=TestRequest(
#             url="/api/v1/check_frontend_token_present",
#             method="get"
#         )
#     )
#     assert response.status_code == 422


#     # incorrect password
#     response = execute_request(
#         client=unauthenticated_client,
#         request=TestRequest(
#             url="/api/v1/login",
#             method="get",
#             params={
#                 "username": username,
#                 "password": password + "c"
#             }
#         )
#     )
#     assert response.status_code == 401

#     # correct password
#     response = execute_request(
#         client=unauthenticated_client,
#         request=TestRequest(
#             url="/api/v1/login",
#             method="get",
#             params={
#                 "username": username,
#                 "password": password
#             },
#             follow_redirects=False
#         ),
#     )
#     assert response.status_code == 303
#     assert response.headers["Location"] == f"http://localhost:8000/api/v1/redirect-with-code?user_laui={user_laui}"
#     session_cookie = response.cookies.get("session")
#     assert session_cookie != None

#     response = execute_request(
#         client=unauthenticated_client,
#         request=TestRequest(
#             url="/api/v1/check_frontend_token_present",
#             method="get"
#         )
#     )
#     assert response.status_code == 422


#     response = execute_request(
#         client=unauthenticated_client,
#         request=TestRequest(
#             url="/api/v1/redirect-with-code",
#             method="get",
#             params={"user_laui": user_laui},
#             follow_redirects=False
#         ),
#     )
#     assert response.status_code == 303
#     redirect_uri = response.headers["Location"]
#     redirect_uri_split = urlsplit(redirect_uri)
#     redirect_uri_query_params = parse_qs(redirect_uri_split.query)

#     uri = urlunsplit(
#         (
#             redirect_uri_split.scheme,
#             redirect_uri_split.netloc,
#             redirect_uri_split.path,
#             "", ""
#         )
#     )
#     assert uri == callback_redirect_uri
#     assert redirect_uri_query_params["state"][0] == state
#     code = redirect_uri_query_params["code"][0]


#     response = execute_request(
#         client=unauthenticated_client,
#         request=TestRequest(
#             url="/api/v1/check_frontend_token_present",
#             method="get"
#         )
#     )
#     assert response.status_code == 422

#     # invalid random code
#     response = execute_request(
#         client=unauthenticated_client,
#         request=TestRequest(
#             url="/api/v1/token",
#             method="post",
#             json={
#                 "grant_type": "authorization_code",
#                 "credentials": {
#                     "code": code + "x"
#                 }
#             }
#         )
#     )
#     assert response.status_code == 401

#     response = execute_request(
#         client=unauthenticated_client,
#         request=TestRequest(
#             url="/api/v1/token",
#             method="post",
#             json={
#                 "grant_type": "authorization_code",
#                 "credentials": {
#                     "code": code
#                 }
#             }
#         )
#     )
#     assert response.status_code == 200
#     print(response.json())

#     refresh_token = response.json()["refresh_token"]
#     access_token = response.json()["access_token"]

#     # send a request without sending access token header
#     response = execute_request(
#         client=unauthenticated_client,
#         request=TestRequest(
#             url="/api/v1/check/",
#             method="get"
#         )
#     )
#     assert response.status_code == 401

#     headers = {"Cookie": f"frontend_token={access_token}"}
#     response = execute_request(
#         client=unauthenticated_client,
#         request=TestRequest(
#             url="/api/v1/check/",
#             method="get",
#             headers=headers
#         )
#     )
#     assert response.status_code == 200

#     # get the access token from refresh token
#     response = execute_request(
#         client=unauthenticated_client,
#         request=TestRequest(
#             url="/api/v1/token",
#             method="post",
#             json={
#                 "grant_type": "refresh_token",
#                 "credentials": {
#                     "token_string": refresh_token
#                 }
#             }
#         )
#     )
#     assert response.status_code == 200

#     access_token = response.json()["access_token"]
#     headers = {"Cookie": f"frontend_token={access_token}"}
#     response = execute_request(
#         client=unauthenticated_client,
#         request=TestRequest(
#             url="/api/v1/check/",
#             method="get",
#             headers=headers
#         )
#     )
#     assert response.status_code == 200


#     response = execute_request(
#         client=unauthenticated_client,
#         request=TestRequest(
#             url="/api/v1/check_frontend_token_present",
#             method="get"
#         )
#     )
#     assert response.status_code == 200
