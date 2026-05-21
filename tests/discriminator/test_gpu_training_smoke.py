"""Smoke test for §5.3.2.b GPU training script.

CUDA-only by definition. The test is automatically skipped when no GPU
is available; that's expected on CI nodes without GPUs and on Windows
boxes that don't have CUDA toolkit installed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")


@pytest.mark.skipif(not torch.cuda.is_available(), reason="no GPU")
def test_gpu_train_one_pair_with_tiny_model(tmp_path):
    pytest.importorskip("transformers")
    pytest.importorskip("sklearn")
    pytest.importorskip("safetensors")

    scripts_dir = Path(__file__).resolve().parents[2] / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    import train_register_classifier_gpu as tr

    corpus = tmp_path / "corpus" / "chemistry" / "en"
    corpus.mkdir(parents=True)

    def _row(i, label):
        return {
            "text": f"sample paragraph number {i} label {label}",
            "label": label,
            "paper_id": f"p{label}_{i}",
        }

    train = [_row(i, i % 2) for i in range(40)]
    val = [_row(100 + i, i % 2) for i in range(10)]
    test = [_row(200 + i, i % 2) for i in range(10)]
    for name, lst in (("train", train), ("val", val), ("test", test)):
        (corpus / f"{name}.jsonl").write_text(
            "\n".join(json.dumps(x) for x in lst), encoding="utf-8"
        )

    metrics = tr.train_one_pair_gpu(
        discipline="chemistry",
        language="en",
        corpus_root=tmp_path / "corpus",
        output_root=tmp_path / "out",
        model_name="google/bert_uncased_L-2_H-128_A-2",
        epochs=1,
        batch_size=4,
        grad_accum=1,
        lr=5e-5,
        fp16=False,  # disable amp for the smoke test — keeps it independent of GPU caps
        gradient_checkpointing=False,
        max_length=32,
        resume=False,
    )
    assert metrics["device_trained_on"].startswith("cuda:0")
    assert (tmp_path / "out" / "register_chemistry_en" / "model.safetensors").exists()


def test_gpu_module_imports_without_cuda():
    """The GPU script must be importable on a CPU-only machine.

    We only ever execute ``main()``/``train_one_pair_gpu`` on a CUDA box,
    but importing the module — which the auto-dispatcher does before
    deciding which path to take — must not require CUDA.
    """
    scripts_dir = Path(__file__).resolve().parents[2] / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    import importlib

    if "train_register_classifier_gpu" in sys.modules:
        importlib.reload(sys.modules["train_register_classifier_gpu"])
    mod = importlib.import_module("train_register_classifier_gpu")
    assert hasattr(mod, "train_one_pair_gpu")
    assert hasattr(mod, "main")
