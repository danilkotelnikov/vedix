import pytest

pytest.importorskip("openai")

from plugins.vedix.mcp.lib.orchestrator.byok.adapters.deepseek_adapter import (  # noqa: E402
    DeepSeekAdapter,
)
from plugins.vedix.mcp.lib.orchestrator.byok.adapters.local_adapter import LocalAdapter  # noqa: E402
from plugins.vedix.mcp.lib.orchestrator.byok.adapters.moonshot_adapter import (  # noqa: E402
    MoonshotAdapter,
)
from plugins.vedix.mcp.lib.orchestrator.byok.adapters.openrouter_adapter import (  # noqa: E402
    OpenRouterAdapter,
)
from plugins.vedix.mcp.lib.orchestrator.byok.adapters.together_adapter import (  # noqa: E402
    TogetherAdapter,
)
from plugins.vedix.mcp.lib.orchestrator.byok.adapters.zhipu_adapter import ZhipuAdapter  # noqa: E402


@pytest.mark.parametrize(
    "AdapterCls, expected_name, expected_region, expected_base_url_substring",
    [
        (OpenRouterAdapter, "openrouter", "global", "openrouter.ai"),
        (TogetherAdapter, "together", "global", "together.xyz"),
        (DeepSeekAdapter, "deepseek", "cn", "deepseek.com"),
        (MoonshotAdapter, "moonshot", "cn", "moonshot.cn"),
        (ZhipuAdapter, "zhipu", "cn", "bigmodel.cn"),
    ],
)
def test_openai_compatible_adapter_capabilities(
    AdapterCls, expected_name, expected_region, expected_base_url_substring
):
    adapter = AdapterCls(api_key="test")
    caps = adapter.capabilities()
    assert caps.name == expected_name
    assert caps.region == expected_region
    assert expected_base_url_substring in adapter._client.base_url.host


def test_local_adapter_takes_custom_url():
    adapter = LocalAdapter(api_key="none", base_url="http://localhost:8000/v1")
    caps = adapter.capabilities()
    assert caps.name == "local"
    assert caps.region == "self-hosted"
