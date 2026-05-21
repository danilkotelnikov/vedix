"""Tests for §5.3.2 Layer B trained-classifier inference + HybridDiscriminator.

Both layers and the combined HybridDiscriminator are exercised here.
Layer B's transformer load is heavy, so we stub
``AutoModelForSequenceClassification.from_pretrained`` and
``AutoTokenizer.from_pretrained`` with simple fakes that return
deterministic logits.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("chromadb")
pytest.importorskip("torch")


@pytest.fixture
def fake_model_dir(tmp_path):
    """A directory shaped like a trained Layer B output."""
    d = tmp_path / "register_chemistry_en"
    d.mkdir()
    (d / "config.json").write_text(
        json.dumps({"model_type": "bert", "num_labels": 2}), encoding="utf-8"
    )
    (d / "metrics.json").write_text(json.dumps({"f1": 0.91}), encoding="utf-8")
    return d


def _stub_logits(positive_prob: float):
    """Return a stub Tensor-like that surfaces argmax + softmax in the shape the
    real ``logits`` tensor would.
    """
    import torch

    return torch.tensor([[1.0 - positive_prob, positive_prob]])


def _patch_transformers(positive_prob: float):
    """Return a context manager that fakes AutoTokenizer + AutoModel."""
    import torch

    class _FakeModel:
        def __init__(self):
            self.config = MagicMock()
            self.eval_called = False

        def to(self, device):
            return self

        def eval(self):
            self.eval_called = True
            return self

        def __call__(self, input_ids=None, attention_mask=None):
            logits = _stub_logits(positive_prob)
            return MagicMock(logits=logits)

    class _FakeTokenizer:
        def __call__(self, text, **kw):
            max_length = kw.get("max_length", 8)
            return {
                "input_ids": torch.zeros((1, max_length), dtype=torch.long),
                "attention_mask": torch.ones((1, max_length), dtype=torch.long),
            }

    return patch(
        "plugins.vedix.mcp.lib.orchestrator.register_discriminator."
        "AutoModelForSequenceClassification.from_pretrained",
        return_value=_FakeModel(),
    ), patch(
        "plugins.vedix.mcp.lib.orchestrator.register_discriminator."
        "AutoTokenizer.from_pretrained",
        return_value=_FakeTokenizer(),
    )


def test_layer_b_passes_when_confidence_high(fake_model_dir):
    from plugins.vedix.mcp.lib.orchestrator.register_discriminator import LayerB

    p_model, p_tok = _patch_transformers(positive_prob=0.9)
    with p_model, p_tok:
        layer = LayerB(model_dir=fake_model_dir)
        v = layer.judge("Some scientific paragraph.")
        assert v.layer == "B"
        assert v.pass_ is True
        assert v.score >= 0.5


def test_layer_b_fails_when_confidence_low(fake_model_dir):
    from plugins.vedix.mcp.lib.orchestrator.register_discriminator import LayerB

    p_model, p_tok = _patch_transformers(positive_prob=0.1)
    with p_model, p_tok:
        layer = LayerB(model_dir=fake_model_dir)
        v = layer.judge("AI-stylistic mush.")
        assert v.layer == "B"
        assert v.pass_ is False
        assert v.score < 0.5


def test_hybrid_overall_requires_both_layers(tmp_path, fake_model_dir):
    from plugins.vedix.mcp.lib.orchestrator.register_discriminator import (
        HybridDiscriminator,
    )
    import hashlib

    class _FakeEncoder:
        def encode(self, texts, normalize_embeddings: bool = True):
            out = []
            for t in texts:
                stem = t.split(": ", 1)[1] if ": " in t else t
                vec = [0.0] * 64
                for tok in stem.lower().split():
                    h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
                    vec[h % 64] += 1.0
                norm = sum(v * v for v in vec) ** 0.5 or 1.0
                out.append([v / norm for v in vec])

            class _AsList(list):
                def tolist(self_inner):
                    return list(self_inner)

            return _AsList(out)

    # Set up: classifiers_root → contains the fake model dir under the
    # expected name; corpus_root → the chroma corpus for Layer A.
    classifiers_root = fake_model_dir.parent

    p_model, p_tok = _patch_transformers(positive_prob=0.9)
    with p_model, p_tok:
        hyb = HybridDiscriminator(
            corpus_root=tmp_path,
            classifiers_root=classifiers_root,
            discipline="chemistry",
            language="en",
        )
        # Stub Layer A's encoder so we don't need multilingual-e5.
        hyb.layer_a._encoder = _FakeEncoder()
        hyb.layer_a.add_corpus(
            [
                "The compound was prepared by reflux in ethanol.",
                "NMR confirmed the structure of compound 1.",
            ]
        )
        out = hyb.judge("The compound was prepared by reflux in ethanol.")
        assert "layer_a" in out
        assert "layer_b" in out
        assert "overall_pass" in out
        # Both passed → overall pass
        assert out["overall_pass"] is True


def test_hybrid_without_layer_b_uses_only_layer_a(tmp_path):
    from plugins.vedix.mcp.lib.orchestrator.register_discriminator import (
        HybridDiscriminator,
    )

    classifiers_root = tmp_path / "classifiers"
    classifiers_root.mkdir()
    hyb = HybridDiscriminator(
        corpus_root=tmp_path / "corpus",
        classifiers_root=classifiers_root,
        discipline="chemistry",
        language="en",
    )
    assert hyb.layer_b is None
    # Stub Layer A so we don't need multilingual-e5.
    import hashlib

    class _Enc:
        def encode(self, texts, normalize_embeddings=True):
            out = [[1.0 / 8] * 64 for _ in texts]

            class _AsList(list):
                def tolist(self_inner):
                    return list(self_inner)

            return _AsList(out)

    hyb.layer_a._encoder = _Enc()
    hyb.layer_a.add_corpus(["alpha bravo charlie delta echo"])
    out = hyb.judge("alpha bravo charlie delta echo")
    assert "layer_a" in out
    assert "layer_b" not in out
    assert "overall_pass" in out


# -- vedix_model CLI -------------------------------------------------------- #


def test_vedix_model_list_returns_local_classifiers(tmp_path):
    from plugins.vedix.scripts import vedix_model

    pair = tmp_path / "register_chemistry_en"
    pair.mkdir()
    (pair / "metrics.json").write_text(
        json.dumps({"f1": 0.91}), encoding="utf-8"
    )
    rows = vedix_model.list_local(out_root=tmp_path)
    assert len(rows) == 1
    assert rows[0]["name"] == "register_chemistry_en"
    assert rows[0]["f1"] == 0.91


def test_vedix_model_publish_refuses_low_f1(tmp_path):
    from plugins.vedix.scripts import vedix_model

    pair = tmp_path / "register_chemistry_en"
    pair.mkdir()
    (pair / "metrics.json").write_text(
        json.dumps({"f1": 0.50}), encoding="utf-8"
    )
    with pytest.raises(SystemExit, match="refusing to publish"):
        vedix_model.publish(name="register_chemistry_en", model_dir=pair)


def test_vedix_model_publish_requires_metrics(tmp_path):
    from plugins.vedix.scripts import vedix_model

    pair = tmp_path / "register_chemistry_en"
    pair.mkdir()
    with pytest.raises(SystemExit, match="missing metrics.json"):
        vedix_model.publish(name="register_chemistry_en", model_dir=pair)


def test_vedix_model_fetch_writes_files(tmp_path, monkeypatch):
    pytest.importorskip("httpx")
    import httpx
    from plugins.vedix.scripts import vedix_model

    file_bytes = {
        "model.safetensors": b"FAKE_MODEL_BYTES",
        "config.json": b"{}",
        "tokenizer.json": b'{"version": "1.0"}',
        "metrics.json": b'{"f1": 0.9}',
    }

    def _handler(request):
        for fn, content in file_bytes.items():
            if request.url.path.endswith(f"/{fn}"):
                return httpx.Response(200, content=content)
        return httpx.Response(404)

    transport = httpx.MockTransport(_handler)
    _real_client_cls = httpx.Client

    def _fake_client_factory(*args, **kwargs):
        kwargs.pop("timeout", None)
        return _real_client_cls(transport=transport)

    monkeypatch.setattr(httpx, "Client", _fake_client_factory)

    out = tmp_path / "classifiers"
    statuses = vedix_model.fetch(
        languages=["en"],
        disciplines=["chemistry"],
        registry_url="https://reg.example/v1",
        out_root=out,
    )
    pair = out / "register_chemistry_en"
    for fn, content in file_bytes.items():
        assert (pair / fn).read_bytes() == content
    assert statuses["register_chemistry_en"]["model.safetensors"] == "ok"
