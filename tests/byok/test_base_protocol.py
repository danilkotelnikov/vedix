from plugins.vedix.mcp.lib.orchestrator.byok.base import (
    ProviderAdapter, ChatRequest, ChatResponse, Message
)


def test_chat_request_dataclass_shape():
    req = ChatRequest(
        messages=[Message(role="user", content="hi")],
        model="claude-opus-4",
        max_tokens=100,
    )
    assert req.messages[0].content == "hi"
    assert req.max_tokens == 100


def test_provider_adapter_protocol_has_required_methods():
    methods = {m for m in dir(ProviderAdapter) if not m.startswith("_")}
    assert {"chat", "stream", "count_tokens", "capabilities", "name"}.issubset(methods)
