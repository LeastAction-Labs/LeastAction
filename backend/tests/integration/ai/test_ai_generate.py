# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import os

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from src.core.db.types import MongoDatabase
from tests.integration.schema import BaseFolders, TestRequest
from tests.integration.utils import create_base_folders, execute_request

# The pytestmark is needed for running anyio tests
pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
async def database_cleanup(test_database: MongoDatabase):
    """Clean up database before and after each test"""
    await test_database.items.drop()
    await test_database.links.delete_many({})
    yield
    await test_database.items.drop()
    await test_database.links.drop()


@pytest.fixture(autouse=True)
def base_folders_setup(client: TestClient, database_cleanup):
    base_folders = create_base_folders(client)
    yield base_folders


@pytest.fixture
async def chat_laui(
    client: TestClient, test_database: MongoDatabase, base_folders_setup: BaseFolders
) -> str:
    """Create a test ai_chat item with codeblock and connection, return its LAUI."""
    # Create folder.ai
    ai_root_response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "folder.ai",
                "name": "test_ai",
                "parent_laui": base_folders_setup.project_folder_laui,
            },
        ),
    )
    assert ai_root_response.status_code == 200
    ai_root_laui = ai_root_response.json()["item_laui"]

    # Create folder.chat under folder.ai
    chat_folder_response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={"item_type": "folder.chat", "name": "test_chat", "parent_laui": ai_root_laui},
        ),
    )
    assert chat_folder_response.status_code == 200
    chat_folder_laui = chat_folder_response.json()["item_laui"]

    # Get API key from environment
    api_key = os.getenv("CLAUDE_API_KEY")
    if not api_key:
        pytest.skip("CLAUDE_API_KEY not found in environment variables")

    # Create ai_chat item with codeblock and connection
    ai_chat_response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "agent",
                "name": "test_invoke_llm",
                "parent_laui": chat_folder_laui,
                "codeblock": {
                    "invoke_llm.py": (
                        "from langchain_anthropic import ChatAnthropic\n\n"
                        "def run(connection, messages, output_schema):\n"
                        "    api_key = connection.get('api_key', '')\n"
                        "    model = connection.get('model', '')\n"
                        "    token_limit = connection.get('token_limit', 8192)\n"
                        "    llm = ChatAnthropic(\n"
                        "        anthropic_api_key=api_key,\n"
                        "        model_name=model,\n"
                        "        max_tokens=token_limit,\n"
                        "        temperature=0.0,\n"
                        "        timeout=10000,\n"
                        "        stop=None,\n"
                        "    )\n"
                        "    llm_with_structured_output = llm.with_structured_output(output_schema, include_raw=True)\n"
                        "    return llm_with_structured_output.invoke(messages)\n"
                    )
                },
                "connection": {
                    "api_key": api_key,
                    "model": "claude-haiku-4-5-20251001",
                    "token_limit": 20000,
                },
            },
        ),
    )
    assert ai_chat_response.status_code == 200, (
        f"Failed to create ai_chat: {ai_chat_response.json()}"
    )

    chat_laui_val = ai_chat_response.json()["item_laui"]

    # Verify item was created
    item = await test_database.items.find_one({"_id": ObjectId(chat_laui_val)})
    assert item is not None

    return chat_laui_val


async def test_generate_action_success(client: TestClient, chat_laui: str):
    """Test successful AI generation for action item type"""
    generate_request = {
        "prompt": "create action to send slack notify using webhook",
        "chat_laui": chat_laui,
        "item_type": "action",
        "ai_provider": "anthropic",
        "include_guide_doc": False,
        "include_install_guide": False,
    }

    response = execute_request(
        client=client,
        request=TestRequest(url="/api/v1/ai/generate", method="post", json=generate_request),
    )

    # Should succeed with 200
    assert response.status_code == 200, f"Failed with: {response.json()}"

    response_data = response.json()

    # Verify success indicators
    assert response_data["token_limit_exceeded"] is False
    assert response_data["partial_generation"] is False
    assert "successfully" in response_data["message"].lower()

    # Verify required fields for action type
    generated_content = response_data["generated_content"]
    assert "codeblock" in generated_content
    assert "bashblock" in generated_content

    # Verify codeblock has content
    codeblock = generated_content["codeblock"]
    assert isinstance(codeblock, dict)
    assert len(codeblock) > 0

    # Verify bashblock has content
    bashblock = generated_content["bashblock"]
    assert isinstance(bashblock, dict)
    assert len(bashblock) > 0

    # Verify temp_file_path is returned
    assert "temp_file_path" in response_data

    print("\n=== Generated Content ===")
    print(f"Codeblock files: {list(codeblock.keys())}")
    print(f"Bashblock files: {list(bashblock.keys())}")
    print(f"Message: {response_data['message']}")


async def test_generate_operator_success(client: TestClient, chat_laui: str):
    """Test successful AI generation for operator item type"""
    generate_request = {
        "prompt": "Create a simple Python operator that uses requests library to make an HTTP GET request",
        "chat_laui": chat_laui,
        "item_type": "operator",
        "ai_provider": "anthropic",
        "include_guide_doc": False,
        "include_install_guide": False,
    }

    response = execute_request(
        client=client,
        request=TestRequest(url="/api/v1/ai/generate", method="post", json=generate_request),
    )

    # May return 200 (full) or 206 (partial) depending on token limits
    assert response.status_code in [200, 206], f"Failed with: {response.json()}"
    response_data = response.json()

    # Verify operator-specific required fields are present in response
    generated_content = response_data["generated_content"]
    assert "codeblock" in generated_content
    assert "bashblock" in generated_content
    assert "payload" in generated_content
    assert "connection" in generated_content

    # At minimum, codeblock should have content for a successful generation
    if response.status_code == 200:
        assert len(generated_content["codeblock"]) > 0
        assert len(generated_content["bashblock"]) > 0
        assert len(generated_content["payload"]) >= 0
        assert len(generated_content["connection"]) >= 0


async def test_generate_payload_success(client: TestClient, chat_laui: str):
    """Test successful AI generation for payload item type"""
    generate_request = {
        "prompt": "Create a JSON payload for a weather API request with temperature and location fields",
        "chat_laui": chat_laui,
        "item_type": "payload",
        "ai_provider": "anthropic",
        "include_guide_doc": False,
        "include_install_guide": False,
    }

    response = execute_request(
        client=client,
        request=TestRequest(url="/api/v1/ai/generate", method="post", json=generate_request),
    )

    assert response.status_code == 200, f"Failed with: {response.json()}"
    response_data = response.json()

    # Verify payload-specific required field
    generated_content = response_data["generated_content"]
    assert "payload" in generated_content
    assert len(generated_content["payload"]) > 0


async def test_generate_with_optional_docs(client: TestClient, chat_laui: str):
    """Test AI generation with optional guide documentation"""
    generate_request = {
        "prompt": "Create a simple calculator action",
        "chat_laui": chat_laui,
        "item_type": "action",
        "ai_provider": "anthropic",
        "include_guide_doc": True,
        "include_install_guide": True,
    }

    response = execute_request(
        client=client,
        request=TestRequest(url="/api/v1/ai/generate", method="post", json=generate_request),
    )

    # May return 200 or 206 (partial) depending on token limits
    assert response.status_code in [200, 206], f"Failed with: {response.json()}"

    response_data = response.json()
    generated_content = response_data["generated_content"]

    # Should have base required fields
    assert "codeblock" in generated_content
    assert "bashblock" in generated_content

    # May or may not have optional fields depending on completion
    # Just verify they're present in the response structure
    assert "guide" in generated_content
    assert "install_guide" in generated_content


async def test_generate_invalid_chat_laui(client: TestClient):
    """Test generation with non-existent ai_chat item"""
    fake_laui = str(ObjectId())

    generate_request = {
        "prompt": "Create something",
        "chat_laui": fake_laui,
        "item_type": "action",
        "ai_provider": "anthropic",
        "include_guide_doc": False,
        "include_install_guide": False,
    }

    response = execute_request(
        client=client,
        request=TestRequest(url="/api/v1/ai/generate", method="post", json=generate_request),
    )

    # Should fail with 404
    assert response.status_code == 404
    response_data = response.json()
    assert "detail" in response_data
    assert "not found" in str(response_data["detail"]).lower()


async def test_generate_missing_required_fields(client: TestClient, chat_laui: str):
    """Test generation with missing required fields in request"""
    # Missing item_type
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/ai/generate",
            method="post",
            json={"prompt": "Create something", "chat_laui": chat_laui},
        ),
    )

    assert response.status_code == 422

    # Missing prompt
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/ai/generate",
            method="post",
            json={"chat_laui": chat_laui, "item_type": "action"},
        ),
    )

    assert response.status_code == 422

    # Missing chat_laui
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/ai/generate",
            method="post",
            json={"prompt": "Create something", "item_type": "action"},
        ),
    )

    assert response.status_code == 422


async def test_generate_token_limit_exceeded(client: TestClient, base_folders_setup: BaseFolders):
    """Test behavior when token limit is exceeded"""
    api_key = os.getenv("CLAUDE_API_KEY")
    if not api_key:
        pytest.skip("CLAUDE_API_KEY not found in environment variables")

    # Create folder.ai
    ai_root_response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "folder.ai",
                "name": "test_low_token",
                "parent_laui": base_folders_setup.project_folder_laui,
            },
        ),
    )
    assert ai_root_response.status_code == 200
    ai_root_laui = ai_root_response.json()["item_laui"]

    # Create folder.chat under folder.ai
    chat_folder_response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "folder.chat",
                "name": "test_low_token_chat",
                "parent_laui": ai_root_laui,
            },
        ),
    )
    assert chat_folder_response.status_code == 200
    chat_folder_laui = chat_folder_response.json()["item_laui"]

    # Create ai_chat item with very low token limit
    ai_chat_response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "agent",
                "name": "low_token_invoke_llm",
                "parent_laui": chat_folder_laui,
                "codeblock": {
                    "invoke_llm.py": (
                        "from langchain_anthropic import ChatAnthropic\n\n"
                        "def run(connection, messages, output_schema):\n"
                        "    api_key = connection.get('api_key', '')\n"
                        "    model = connection.get('model', '')\n"
                        "    token_limit = connection.get('token_limit', 8192)\n"
                        "    llm = ChatAnthropic(\n"
                        "        anthropic_api_key=api_key,\n"
                        "        model_name=model,\n"
                        "        max_tokens=token_limit,\n"
                        "        temperature=0.0,\n"
                        "        timeout=10000,\n"
                        "        stop=None,\n"
                        "    )\n"
                        "    llm_with_structured_output = llm.with_structured_output(output_schema, include_raw=True)\n"
                        "    return llm_with_structured_output.invoke(messages)\n"
                    )
                },
                "connection": {
                    "api_key": api_key,
                    "model": "claude-haiku-4-5-20251001",
                    "token_limit": 100,
                },
            },
        ),
    )
    assert ai_chat_response.status_code == 200, (
        f"Failed to create ai_chat: {ai_chat_response.json()}"
    )
    chat_laui_val = ai_chat_response.json()["item_laui"]

    generate_request = {
        "prompt": "Create a very complex Python application with multiple modules, extensive documentation, tests, and deployment scripts",
        "chat_laui": chat_laui_val,
        "item_type": "action",
        "ai_provider": "anthropic",
        "include_guide_doc": True,
        "include_install_guide": True,
    }

    response = execute_request(
        client=client,
        request=TestRequest(url="/api/v1/ai/generate", method="post", json=generate_request),
    )

    # Should return 206 (Partial Content)
    assert response.status_code == 206, (
        f"Expected 206 but got {response.status_code}: {response.json()}"
    )

    response_data = response.json()

    # Verify partial generation indicators
    assert response_data["token_limit_exceeded"] is True
    assert response_data["partial_generation"] is True
    assert "token limit" in response_data["message"].lower()

    # Should still return whatever was completed
    assert "generated_content" in response_data


async def test_ai_generate_with_context_continuation(client: TestClient, chat_laui: str):
    """Test multi-turn AI generation: first prompt, then follow-up with message history and generated content"""
    # Step 1: First generation (no history)
    first_response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/ai/generate",
            method="post",
            json={
                "prompt": "write a action to write hi in a file",
                "chat_laui": chat_laui,
                "item_type": "action",
                "ai_provider": "anthropic",
                "include_guide_doc": False,
                "include_install_guide": False,
            },
        ),
    )
    assert first_response.status_code == 200, f"First generate failed: {first_response.json()}"
    first_data = first_response.json()
    first_content = first_data["generated_content"]
    assert "codeblock" in first_content

    # Step 2: Follow-up generation with message history and previous generated content
    second_response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/ai/generate",
            method="post",
            json={
                "prompt": "add a print statement after writing",
                "chat_laui": chat_laui,
                "item_type": "action",
                "ai_provider": "anthropic",
                "include_guide_doc": False,
                "include_install_guide": False,
                "messages": [
                    {"role": "user", "content": "write a action to write hi in a file"},
                    {"role": "assistant", "content": "Here is the action that writes hi to a file"},
                ],
                "generated_content": first_content,
            },
        ),
    )
    assert second_response.status_code == 200, f"Second generate failed: {second_response.json()}"
    second_data = second_response.json()
    assert "generated_content" in second_data
    assert second_data["token_limit_exceeded"] is False

    # Verify the second response also has valid content
    second_content = second_data["generated_content"]
    assert "codeblock" in second_content


async def test_ai_generate_with_message_history(client: TestClient, chat_laui: str):
    """Test that the generate endpoint accepts optional messages and generated_content fields"""
    generate_request = {
        "prompt": "now add error handling to the action",
        "chat_laui": chat_laui,
        "item_type": "action",
        "ai_provider": "anthropic",
        "include_guide_doc": False,
        "include_install_guide": False,
        "messages": [
            {"role": "user", "content": "create a slack action"},
            {"role": "assistant", "content": "Here is the action code for slack"},
        ],
        "generated_content": {"codeblock": {"main.py": "print('slack')"}},
    }

    response = execute_request(
        client=client,
        request=TestRequest(url="/api/v1/ai/generate", method="post", json=generate_request),
    )

    # Should succeed (the new optional fields don't break the API)
    assert response.status_code == 200, f"Failed with: {response.json()}"

    response_data = response.json()
    assert response_data["token_limit_exceeded"] is False
    assert "generated_content" in response_data
