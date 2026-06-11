# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from anthropic import APIError, APIStatusError
from pydantic import ValidationError

from src.common.config import Config
from src.common.exceptions import AIError, NotFoundError, PartialGenerationError
from src.common.logger.logger import get_logger_manager, initialize_logger
from src.core.ai.schema import (
    ActionPromptSchema,
    ChatMessage,
    GeneratedContent,
    GenerateRequest,
    ItemType,
    OperatorPromptSchema,
    PayloadPromptSchema,
)
from src.core.ai.service import AIService
from src.core.catalog.service import CatalogService
from src.core.validation.service import CodeblockValidator


class DummyAiChatItem:
    """Stand-in for a catalog ai_chat item with codeblock and connection."""

    def __init__(self, codeblock=None, connection=None):
        self.codeblock = codeblock or {
            "invoke_llm.py": "def run(connection, messages, output_schema): pass"
        }
        self.connection = connection or {"api_key": "key", "model": "model", "token_limit": 500}


class DummySessionItem:
    """Stand-in for an ai_history session item."""

    def __init__(self, temp_file_path=None):
        self.temp_file_path = temp_file_path


def _make_module_run(parsed_model, stop_reason=None, capture=None):
    """Return a run() function that produces a structured response like module.run()."""

    def run(connection, messages, output_schema):
        if capture is not None:
            capture.extend(messages)
        return {
            "raw": SimpleNamespace(response_metadata={"stop_reason": stop_reason}),
            "parsed": parsed_model,
        }

    return run


def _make_run_raising(exception):
    """Return a run() function that raises the given exception."""

    def run(connection, messages, output_schema):
        raise exception

    return run


def _build_request(
    item_type: ItemType,
    ai_chat_id: str = "507f1f77bcf86cd799439011",
    include_guide_doc: bool = False,
    include_install_guide: bool = False,
    messages: list[ChatMessage] | None = None,
    generated_content: dict | None = None,
    session_id: str | None = None,
):
    return GenerateRequest(
        prompt="write something",
        chat_laui=ai_chat_id,
        item_type=item_type,
        ai_provider="anthropic",
        include_guide_doc=include_guide_doc,
        include_install_guide=include_install_guide,
        messages=messages,
        generated_content=generated_content,
        session_id=session_id,
    )


def _patch_module_loading(monkeypatch, service, run_func):
    """Patch create_module_from_codeblock and load_module to return a fake module with the given run()."""
    fake_module = ModuleType("fake_ai_module")
    fake_module.run = run_func

    monkeypatch.setattr(
        "src.core.ai.service.create_module_from_codeblock",
        lambda codeblock, dir: ["/tmp/fake_module.py"],
    )
    monkeypatch.setattr(
        "src.core.ai.service.load_module",
        lambda path: fake_module,
    )


class TestAIServiceGenerate:
    """Unit tests for AIService.generate with ai_chat module loading."""

    @pytest.fixture
    def real_config(self):
        config = Config()
        config.logs_dir.mkdir(parents=True, exist_ok=True)
        return config

    @pytest.fixture(autouse=True)
    def setup_logger(self, real_config):
        initialize_logger(real_config)
        yield
        get_logger_manager().clear_loggers()

    @pytest.fixture
    def mock_catalog_service(self):
        service = AsyncMock(spec=CatalogService)
        service.safe_find_item = AsyncMock()
        return service

    @pytest.mark.asyncio
    async def test_generate_success_filters_completed_fields(
        self, mock_catalog_service, monkeypatch
    ):
        mock_catalog_service.safe_find_item.return_value = DummyAiChatItem(), None
        service = AIService(mock_catalog_service, CodeblockValidator())

        parsed = ActionPromptSchema(
            codeblock=GeneratedContent(completed=True, code="print('hi')"),
            bashblock=GeneratedContent(completed=True, bash="echo hi"),
        )
        _patch_module_loading(monkeypatch, service, _make_module_run(parsed, stop_reason=None))

        request = _build_request(ItemType.ACTION)
        response = await service.generate(request)

        assert response.partial_generation is False
        assert response.token_limit_exceeded is False
        assert response.generated_content == {
            "codeblock": {"code": "print('hi')"},
            "bashblock": {"bash": "echo hi"},
        }
        assert response.temp_file_path is not None

    @pytest.mark.asyncio
    async def test_generate_raises_partial_when_incomplete(self, mock_catalog_service, monkeypatch):
        mock_catalog_service.safe_find_item.return_value = DummyAiChatItem(), None
        service = AIService(mock_catalog_service, CodeblockValidator())

        parsed = ActionPromptSchema(
            codeblock=GeneratedContent(completed=True, code="ok"),
            bashblock=GeneratedContent(completed=False),
        )
        _patch_module_loading(monkeypatch, service, _make_module_run(parsed, stop_reason=None))

        request = _build_request(ItemType.ACTION)
        with pytest.raises(PartialGenerationError) as err:
            await service.generate(request)

        detail = err.value.detail
        assert detail["partial_generation"] is True
        assert detail["token_limit_exceeded"] is False
        assert detail["generated_content"]["codeblock"] == {"code": "ok"}
        assert detail["generated_content"]["bashblock"] == {}

    @pytest.mark.asyncio
    async def test_generate_token_limit_exceeded(self, mock_catalog_service, monkeypatch):
        mock_catalog_service.safe_find_item.return_value = (
            DummyAiChatItem(connection={"api_key": "key", "model": "model", "token_limit": 10}),
            None,
        )
        service = AIService(mock_catalog_service, CodeblockValidator())

        parsed = ActionPromptSchema(
            codeblock=GeneratedContent(completed=True, code="short"),
            bashblock=GeneratedContent(completed=False),
        )
        _patch_module_loading(
            monkeypatch, service, _make_module_run(parsed, stop_reason="max_tokens")
        )

        request = _build_request(ItemType.ACTION)
        with pytest.raises(PartialGenerationError) as err:
            await service.generate(request)

        detail = err.value.detail
        assert detail["token_limit_exceeded"] is True
        assert detail["partial_generation"] is True
        assert "codeblock" in detail["generated_content"]

    @pytest.mark.asyncio
    async def test_generate_missing_ai_chat_item(self, mock_catalog_service):
        mock_catalog_service.safe_find_item.return_value = None, NotFoundError
        service = AIService(mock_catalog_service, CodeblockValidator())

        request = _build_request(ItemType.ACTION)
        with pytest.raises(NotFoundError):
            await service.generate(request)

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self, mock_catalog_service, monkeypatch):
        mock_catalog_service.safe_find_item.return_value = (
            DummyAiChatItem(connection={"api_key": "", "model": "model", "token_limit": 100}),
            None,
        )
        service = AIService(mock_catalog_service, CodeblockValidator())

        request = _build_request(ItemType.ACTION)
        with pytest.raises(NotFoundError):
            await service.generate(request)

    @pytest.mark.asyncio
    async def test_generate_missing_model(self, mock_catalog_service, monkeypatch):
        mock_catalog_service.safe_find_item.return_value = (
            DummyAiChatItem(connection={"api_key": "key", "model": "", "token_limit": 100}),
            None,
        )
        service = AIService(mock_catalog_service, CodeblockValidator())

        request = _build_request(ItemType.ACTION)
        with pytest.raises(NotFoundError):
            await service.generate(request)

    @pytest.mark.asyncio
    async def test_generate_no_codeblock(self, mock_catalog_service):
        mock_catalog_service.safe_find_item.return_value = DummyAiChatItem(codeblock=None), None
        service = AIService(mock_catalog_service, CodeblockValidator())

        request = _build_request(ItemType.ACTION)
        with pytest.raises(AIError):
            await service.generate(request)

    @pytest.mark.asyncio
    async def test_generate_no_connection(self, mock_catalog_service):
        mock_catalog_service.safe_find_item.return_value = DummyAiChatItem(connection=None)
        mock_catalog_service.safe_find_item.return_value.connection = None
        service = AIService(mock_catalog_service, CodeblockValidator())

        request = _build_request(ItemType.ACTION)
        with pytest.raises(AIError):
            await service.generate(request)

    @pytest.mark.asyncio
    async def test_generate_missing_schema_map_entry(self, mock_catalog_service, monkeypatch):
        mock_catalog_service.safe_find_item.return_value = DummyAiChatItem(), None
        service = AIService(mock_catalog_service, CodeblockValidator())
        monkeypatch.setattr(service, "schema_map", {})

        _patch_module_loading(monkeypatch, service, _make_module_run(None))

        request = _build_request(ItemType.ACTION)
        with pytest.raises(NotFoundError):
            await service.generate(request)

    @pytest.mark.asyncio
    async def test_generate_missing_system_prompt_entry(self, mock_catalog_service, monkeypatch):
        mock_catalog_service.safe_find_item.return_value = DummyAiChatItem(), None
        service = AIService(mock_catalog_service, CodeblockValidator())
        monkeypatch.setattr(service, "system_prompt_map", {})

        _patch_module_loading(monkeypatch, service, _make_module_run(None))

        request = _build_request(ItemType.ACTION)
        with pytest.raises(NotFoundError):
            await service.generate(request)

    @pytest.mark.asyncio
    async def test_generate_complete_success(self, mock_catalog_service, monkeypatch):
        mock_catalog_service.safe_find_item.return_value = DummyAiChatItem(), None
        service = AIService(mock_catalog_service, CodeblockValidator())

        parsed = ActionPromptSchema(
            codeblock=GeneratedContent(completed=True, code="print('done')"),
            bashblock=GeneratedContent(completed=True, bash="echo done"),
        )
        _patch_module_loading(monkeypatch, service, _make_module_run(parsed, stop_reason=None))

        request = _build_request(ItemType.ACTION)
        response = await service.generate(request)

        assert response.partial_generation is False
        assert response.token_limit_exceeded is False
        assert response.generated_content["codeblock"]["code"] == "print('done')"

    @pytest.mark.asyncio
    async def test_generate_model_context_window_exceeded(self, mock_catalog_service, monkeypatch):
        mock_catalog_service.safe_find_item.return_value = DummyAiChatItem(), None
        service = AIService(mock_catalog_service, CodeblockValidator())

        parsed = ActionPromptSchema(
            codeblock=GeneratedContent(completed=True, code="x"),
            bashblock=GeneratedContent(completed=False),
        )
        _patch_module_loading(
            monkeypatch,
            service,
            _make_module_run(parsed, stop_reason="model_context_window_exceeded"),
        )

        request = _build_request(ItemType.ACTION)
        with pytest.raises(PartialGenerationError) as err:
            await service.generate(request)

        detail = err.value.detail
        assert detail["token_limit_exceeded"] is True
        assert detail["partial_generation"] is True

    @pytest.mark.asyncio
    async def test_generate_partial_on_incomplete_fields(self, mock_catalog_service, monkeypatch):
        mock_catalog_service.safe_find_item.return_value = DummyAiChatItem(), None
        service = AIService(mock_catalog_service, CodeblockValidator())

        parsed = ActionPromptSchema(
            codeblock=GeneratedContent(completed=True, code="a"),
            bashblock=GeneratedContent(completed=False),
        )
        _patch_module_loading(monkeypatch, service, _make_module_run(parsed, stop_reason=None))

        request = _build_request(ItemType.ACTION)
        with pytest.raises(PartialGenerationError):
            await service.generate(request)

    @pytest.mark.asyncio
    async def test_generate_context_limit_api_error(self, mock_catalog_service, monkeypatch):
        mock_catalog_service.safe_find_item.return_value = DummyAiChatItem(), None
        service = AIService(mock_catalog_service, CodeblockValidator())

        _patch_module_loading(
            monkeypatch,
            service,
            _make_run_raising(APIError("context limit exceeded", request=None, body=None)),
        )

        request = _build_request(ItemType.ACTION)
        with pytest.raises(AIError) as err:
            await service.generate(request)

        assert "context window" in str(err.value).lower()

    @pytest.mark.asyncio
    async def test_generate_validation_error(self, mock_catalog_service, monkeypatch):
        mock_catalog_service.safe_find_item.return_value = DummyAiChatItem(), None
        service = AIService(mock_catalog_service, CodeblockValidator())

        _patch_module_loading(
            monkeypatch,
            service,
            _make_run_raising(ValidationError.from_exception_data("TestModel", [])),
        )

        request = _build_request(ItemType.ACTION)
        with pytest.raises(AIError):
            await service.generate(request)

    def test_filter_completed_fields_with_optional_and_connection(self, mock_catalog_service):
        service = AIService(mock_catalog_service, CodeblockValidator())
        result = ActionPromptSchema(
            codeblock=GeneratedContent(completed=True, code="c"),
            bashblock=GeneratedContent(completed=False),
            connection=GeneratedContent(completed=True, conn="cfg"),
            guide=GeneratedContent(completed=True, guide="g"),
            install_guide=GeneratedContent(completed=False),
        )

        filtered, all_done = service._filter_completed_fields(
            result,
            ItemType.ACTION,
            include_guide_doc=True,
            include_install_guide=True,
        )

        assert filtered["codeblock"] == {"code": "c"}
        assert filtered["bashblock"] == {}
        assert filtered["connection"] == {"conn": "cfg"}
        assert filtered["guide"] == {"guide": "g"}
        assert filtered["install_guide"] == {}
        assert all_done is False

    def test_enhance_system_prompt_without_flags(self, mock_catalog_service):
        service = AIService(mock_catalog_service, CodeblockValidator())
        base = "base prompt"
        prompt = service._enhance_system_prompt(
            base, include_guide_doc=False, include_install_guide=False
        )
        assert prompt == base

    def test_enhance_system_prompt_appends_instructions(self, mock_catalog_service):
        service = AIService(mock_catalog_service, CodeblockValidator())
        base = "base prompt"
        prompt = service._enhance_system_prompt(
            base, include_guide_doc=True, include_install_guide=True
        )
        assert "guide" in prompt
        assert "install_guide" in prompt

    @pytest.mark.asyncio
    async def test_generate_handles_max_output_tokens(self, mock_catalog_service, monkeypatch):
        mock_catalog_service.safe_find_item.return_value = DummyAiChatItem(), None
        service = AIService(mock_catalog_service, CodeblockValidator())

        parsed = ActionPromptSchema(
            codeblock=GeneratedContent(completed=True, code="ok"),
            bashblock=GeneratedContent(completed=False),
        )
        _patch_module_loading(
            monkeypatch, service, _make_module_run(parsed, stop_reason="max_output_tokens")
        )

        request = _build_request(ItemType.ACTION)
        with pytest.raises(PartialGenerationError) as err:
            await service.generate(request)

        assert err.value.detail["token_limit_exceeded"] is True
        assert err.value.detail["partial_generation"] is True

    @pytest.mark.asyncio
    async def test_generate_operator_success_with_optionals(
        self, mock_catalog_service, monkeypatch
    ):
        mock_catalog_service.safe_find_item.return_value = DummyAiChatItem(), None
        service = AIService(mock_catalog_service, CodeblockValidator())

        parsed = OperatorPromptSchema(
            codeblock=GeneratedContent(completed=True, code="c"),
            bashblock=GeneratedContent(completed=True, bash="b"),
            payload=GeneratedContent(completed=True, payload={"p": 1}),
            connection=GeneratedContent(completed=True, conn="cfg"),
            guide=GeneratedContent(completed=True, guide="g"),
            install_guide=GeneratedContent(completed=True, install="i"),
        )
        _patch_module_loading(monkeypatch, service, _make_module_run(parsed, stop_reason=None))

        request = _build_request(
            ItemType.OPERATOR,
            include_guide_doc=True,
            include_install_guide=True,
        )
        response = await service.generate(request)

        assert response.partial_generation is False
        assert response.generated_content["connection"] == {"conn": "cfg"}
        assert response.generated_content["install_guide"] == {"install": "i"}

    @pytest.mark.asyncio
    async def test_generate_operator_missing_required_field(
        self, mock_catalog_service, monkeypatch
    ):
        mock_catalog_service.safe_find_item.return_value = DummyAiChatItem(), None
        service = AIService(mock_catalog_service, CodeblockValidator())

        parsed = OperatorPromptSchema(
            codeblock=GeneratedContent(completed=True, code="c"),
            bashblock=GeneratedContent(completed=True, bash="b"),
            payload=GeneratedContent(completed=True, payload={"p": 1}),
            connection=GeneratedContent(completed=False),
        )
        _patch_module_loading(monkeypatch, service, _make_module_run(parsed, stop_reason=None))

        request = _build_request(ItemType.OPERATOR)
        with pytest.raises(PartialGenerationError) as err:
            await service.generate(request)

        detail = err.value.detail
        assert detail["partial_generation"] is True
        assert detail["token_limit_exceeded"] is False
        assert detail["generated_content"]["connection"] == {}

    @pytest.mark.asyncio
    async def test_generate_payload_success(self, mock_catalog_service, monkeypatch):
        mock_catalog_service.safe_find_item.return_value = DummyAiChatItem(), None
        service = AIService(mock_catalog_service, CodeblockValidator())

        parsed = PayloadPromptSchema(payload=GeneratedContent(completed=True, data={"k": "v"}))
        _patch_module_loading(monkeypatch, service, _make_module_run(parsed, stop_reason=None))

        request = _build_request(ItemType.PAYLOAD)
        response = await service.generate(request)

        assert response.partial_generation is False
        assert response.generated_content == {"payload": {"k": "v"}}

    @pytest.mark.asyncio
    async def test_generate_non_context_api_error(self, mock_catalog_service, monkeypatch):
        mock_catalog_service.safe_find_item.return_value = DummyAiChatItem(), None
        service = AIService(mock_catalog_service, CodeblockValidator())

        fake_response = SimpleNamespace(
            request=SimpleNamespace(),
            status_code=500,
            headers={"request-id": "req123"},
        )
        _patch_module_loading(
            monkeypatch,
            service,
            _make_run_raising(APIStatusError(message="oops", response=fake_response, body=None)),
        )

        request = _build_request(ItemType.ACTION)
        with pytest.raises(AIError) as err:
            await service.generate(request)

        assert "ai service provider error" in str(err.value).lower()

    @pytest.mark.asyncio
    async def test_generate_with_message_history(self, mock_catalog_service, monkeypatch):
        mock_catalog_service.safe_find_item.return_value = DummyAiChatItem(), None
        service = AIService(mock_catalog_service, CodeblockValidator())
        captured_messages = []

        parsed = ActionPromptSchema(
            codeblock=GeneratedContent(completed=True, code="updated"),
            bashblock=GeneratedContent(completed=True, bash="echo updated"),
        )
        _patch_module_loading(
            monkeypatch,
            service,
            _make_module_run(parsed, stop_reason=None, capture=captured_messages),
        )

        request = _build_request(
            ItemType.ACTION,
            messages=[
                ChatMessage(role="user", content="first prompt"),
                ChatMessage(role="assistant", content="first response"),
            ],
        )
        await service.generate(request)

        # Should have: SystemMessage + HumanMessage(history) + AIMessage(history) + HumanMessage(current)
        assert len(captured_messages) == 4
        assert captured_messages[0].__class__.__name__ == "SystemMessage"
        assert captured_messages[1].__class__.__name__ == "HumanMessage"
        assert captured_messages[1].content == "first prompt"
        assert captured_messages[2].__class__.__name__ == "AIMessage"
        assert captured_messages[2].content == "first response"
        assert captured_messages[3].__class__.__name__ == "HumanMessage"
        assert captured_messages[3].content == "write something"

    @pytest.mark.asyncio
    async def test_generate_reuses_temp_file_from_session(
        self, mock_catalog_service, monkeypatch, tmp_path
    ):
        """When session_id is provided with a cached temp_file_path, module loading should reuse it."""
        # Create an actual temp file so Path.exists() returns True naturally
        cached_file = tmp_path / "cached_module.py"
        cached_file.write_text("def run(c, m, s): pass")

        ai_chat_item = DummyAiChatItem()
        session_item = DummySessionItem(temp_file_path=str(cached_file))

        # First call returns ai_chat item, second returns session item
        mock_catalog_service.safe_find_item.return_value = (ai_chat_item, None)
        mock_catalog_service.find_item.return_value = session_item
        service = AIService(mock_catalog_service, CodeblockValidator())

        parsed = ActionPromptSchema(
            codeblock=GeneratedContent(completed=True, code="cached"),
            bashblock=GeneratedContent(completed=True, bash="echo cached"),
        )
        fake_module = ModuleType("cached_module")
        fake_module.run = _make_module_run(parsed, stop_reason=None)

        monkeypatch.setattr("src.core.ai.service.load_module", lambda path: fake_module)

        request = _build_request(
            ItemType.ACTION,
            session_id="507f1f77bcf86cd799439012",
        )
        response = await service.generate(request)

        assert response.temp_file_path == str(cached_file)
        assert response.generated_content["codeblock"]["code"] == "cached"

    @pytest.mark.asyncio
    async def test_generate_missing_run_function(self, mock_catalog_service, monkeypatch):
        """Module without run() should raise AIError."""
        mock_catalog_service.safe_find_item.return_value = DummyAiChatItem(), None
        service = AIService(mock_catalog_service, CodeblockValidator())

        fake_module = ModuleType("no_run_module")
        # No run attribute

        monkeypatch.setattr(
            "src.core.ai.service.create_module_from_codeblock",
            lambda codeblock, dir: ["/tmp/fake.py"],
        )
        monkeypatch.setattr("src.core.ai.service.load_module", lambda path: fake_module)

        request = _build_request(ItemType.ACTION)
        with pytest.raises(AIError, match="500 Missing run function"):
            await service.generate(request)

        monkeypatch.setattr(
            "src.core.ai.service.create_module_from_codeblock",
            lambda codeblock, dir: ["/tmp/fake.py"],
        )
        monkeypatch.setattr("src.core.ai.service.load_module", lambda path: fake_module)

        request = _build_request(ItemType.ACTION)
        with pytest.raises(AIError, match="500 Missing run function"):
            await service.generate(request)
