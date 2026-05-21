"""Vedix — Layer B classifier training (GPU path, §5.3.2.b).

Target hardware: NVIDIA RTX 4060 8 GB or any GPU with ≥ 8 GB VRAM.
Default model: ``xlm-roberta-base`` (~278 M params, ~1.1 GB fp16
checkpoint).

Mixed precision: fp16 via ``torch.cuda.amp``. Gradient checkpointing
enabled by default to fit in 8 GB.

Reuses ``RegisterDataset`` and ``_read_jsonl`` from the CPU sibling so
the data path is identical.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import torch
from torch.utils.data import DataLoader

# Reuse the Dataset class from the CPU script — keeps the data path identical.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from train_register_classifier_cpu import RegisterDataset, _read_jsonl  # noqa: E402


def train_one_pair_gpu(
    *,
    discipline: str,
    language: str,
    corpus_root: Path,
    output_root: Path,
    model_name: str,
    epochs: int,
    batch_size: int,
    grad_accum: int,
    lr: float,
    fp16: bool,
    gradient_checkpointing: bool,
    max_length: int = 512,
    resume: bool = True,
) -> dict:
    """Train one (discipline, language) pair on a single CUDA device."""
    from transformers import (
        AutoTokenizer,
        AutoModelForSequenceClassification,
        get_linear_schedule_with_warmup,
    )
    from sklearn.metrics import precision_recall_fscore_support, accuracy_score

    pair_dir = corpus_root / discipline / language
    train_items = _read_jsonl(pair_dir / "train.jsonl")
    val_items = _read_jsonl(pair_dir / "val.jsonl")
    test_items = _read_jsonl(pair_dir / "test.jsonl")

    out = output_root / f"register_{discipline}_{language}"
    out.mkdir(parents=True, exist_ok=True)
    ckpt_dir = out / "checkpoint-best"

    try:
        tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
    except (ValueError, OSError):
        tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=False)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name, num_labels=2
    )
    if gradient_checkpointing:
        model.gradient_checkpointing_enable()
    if resume and (ckpt_dir / "model.safetensors").exists():
        from safetensors.torch import load_file

        model.load_state_dict(load_file(str(ckpt_dir / "model.safetensors")))
        print(f"[train-gpu] resumed from {ckpt_dir}")

    device = torch.device("cuda:0")
    model.to(device)

    train_ds = RegisterDataset(train_items, tokenizer, max_length)
    val_ds = RegisterDataset(val_items, tokenizer, max_length)
    test_ds = RegisterDataset(test_items, tokenizer, max_length)
    train_loader = DataLoader(
        train_ds, batch_size=batch_size, shuffle=True, num_workers=4, pin_memory=True
    )
    val_loader = DataLoader(
        val_ds, batch_size=batch_size * 2, num_workers=2, pin_memory=True
    )
    test_loader = DataLoader(
        test_ds, batch_size=batch_size * 2, num_workers=2, pin_memory=True
    )

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr)
    total_steps = max(1, len(train_loader) // max(1, grad_accum)) * epochs
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=int(0.06 * total_steps),
        num_training_steps=total_steps,
    )
    # ``torch.amp.GradScaler("cuda")`` is the v2.4+ recommended API; the
    # legacy ``torch.cuda.amp.GradScaler`` is still accepted.
    try:
        scaler = torch.amp.GradScaler("cuda", enabled=fp16)  # type: ignore[attr-defined]
    except (AttributeError, TypeError):
        scaler = torch.cuda.amp.GradScaler(enabled=fp16)

    best_val_f1 = -1.0
    log_path = out / "training_log.jsonl"
    log_path.write_text("", encoding="utf-8")

    for epoch in range(epochs):
        model.train()
        running_loss = 0.0
        for step, batch in enumerate(train_loader):
            with torch.cuda.amp.autocast(enabled=fp16):
                outputs = model(
                    input_ids=batch["input_ids"].to(device, non_blocking=True),
                    attention_mask=batch["attention_mask"].to(
                        device, non_blocking=True
                    ),
                    labels=batch["labels"].to(device, non_blocking=True),
                )
                loss = outputs.loss / grad_accum
            scaler.scale(loss).backward()
            running_loss += loss.item() * grad_accum
            if (step + 1) % grad_accum == 0:
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                scaler.step(optimizer)
                scaler.update()
                scheduler.step()
                optimizer.zero_grad(set_to_none=True)
            if step % 50 == 0:
                with log_path.open("a", encoding="utf-8") as f:
                    f.write(
                        json.dumps(
                            {
                                "epoch": epoch,
                                "step": step,
                                "loss": running_loss / (step + 1),
                                "lr": scheduler.get_last_lr()[0],
                                "gpu_mem_mb": torch.cuda.max_memory_allocated() / 1e6,
                            }
                        )
                        + "\n"
                    )

        # Validation
        model.eval()
        val_preds: list[int] = []
        val_labels: list[int] = []
        with torch.no_grad():
            for batch in val_loader:
                with torch.cuda.amp.autocast(enabled=fp16):
                    logits = model(
                        input_ids=batch["input_ids"].to(device),
                        attention_mask=batch["attention_mask"].to(device),
                    ).logits
                val_preds.extend(logits.argmax(-1).cpu().tolist())
                val_labels.extend(batch["labels"].cpu().tolist())
        p, r, f, _ = precision_recall_fscore_support(
            val_labels, val_preds, average="binary", zero_division=0
        )
        acc = accuracy_score(val_labels, val_preds)
        print(
            f"[train-gpu] epoch {epoch}: val P={p:.3f} R={r:.3f} F1={f:.3f} Acc={acc:.3f}"
        )
        if f > best_val_f1:
            best_val_f1 = float(f)
            ckpt_dir.mkdir(exist_ok=True)
            from safetensors.torch import save_file

            save_file(model.state_dict(), str(ckpt_dir / "model.safetensors"))
            tokenizer.save_pretrained(str(out))
            model.config.save_pretrained(str(out))
        if best_val_f1 < 0.78 and epoch == 0 and len(train_items) >= 200:
            print(
                f"[train-gpu] WARN val F1 {best_val_f1:.3f} < 0.78 after "
                f"epoch 0; aborting pair"
            )
            break

    # Test (with best checkpoint).
    from safetensors.torch import load_file, save_file

    model.load_state_dict(load_file(str(ckpt_dir / "model.safetensors")))
    model.eval()
    test_preds: list[int] = []
    test_labels: list[int] = []
    with torch.no_grad():
        for batch in test_loader:
            with torch.cuda.amp.autocast(enabled=fp16):
                logits = model(
                    input_ids=batch["input_ids"].to(device),
                    attention_mask=batch["attention_mask"].to(device),
                ).logits
            test_preds.extend(logits.argmax(-1).cpu().tolist())
            test_labels.extend(batch["labels"].cpu().tolist())
    tp, tr, tf, _ = precision_recall_fscore_support(
        test_labels, test_preds, average="binary", zero_division=0
    )
    tacc = accuracy_score(test_labels, test_preds)
    gpu_name = torch.cuda.get_device_properties(0).name
    metrics = {
        "precision": round(float(tp), 4),
        "recall": round(float(tr), 4),
        "f1": round(float(tf), 4),
        "accuracy": round(float(tacc), 4),
        "best_val_f1": round(best_val_f1, 4),
        "model": model_name,
        "device_trained_on": f"cuda:0 {gpu_name}",
        "discipline": discipline,
        "language": language,
        "epochs": epochs,
        "batch_size": batch_size,
        "grad_accum": grad_accum,
        "lr": lr,
    }
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    save_file(model.state_dict(), str(out / "model.safetensors"))
    return metrics


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus-root", required=True, type=Path)
    ap.add_argument("--output-root", required=True, type=Path)
    ap.add_argument("--languages", required=True)
    ap.add_argument("--disciplines", required=True)
    ap.add_argument("--only-pair", default=None)
    ap.add_argument("--model", default="xlm-roberta-base")
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--grad-accum", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--fp16", action="store_true", default=True)
    ap.add_argument(
        "--gradient-checkpointing", action="store_true", default=True
    )
    ap.add_argument("--max-length", type=int, default=512)
    ap.add_argument("--resume-from-checkpoint", default="auto")
    ap.add_argument("--log-to-tensorboard", default=None)
    args = ap.parse_args()

    args.output_root.mkdir(parents=True, exist_ok=True)
    manifest: dict = {"models": []}
    manifest_path = args.output_root / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    def _train(d: str, l: str) -> None:
        m = train_one_pair_gpu(
            discipline=d,
            language=l,
            corpus_root=args.corpus_root,
            output_root=args.output_root,
            model_name=args.model,
            epochs=args.epochs,
            batch_size=args.batch_size,
            grad_accum=args.grad_accum,
            lr=args.lr,
            fp16=args.fp16,
            gradient_checkpointing=args.gradient_checkpointing,
            max_length=args.max_length,
            resume=(args.resume_from_checkpoint == "auto"),
        )
        entry = {"name": f"register_{d}_{l}", **m, "trained_at": time.time()}
        manifest["models"] = [
            x for x in manifest["models"] if x.get("name") != entry["name"]
        ]
        manifest["models"].append(entry)
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    if args.only_pair:
        d, l = args.only_pair.split(":", 1)
        _train(d, l)
        return

    for d in args.disciplines.split(","):
        for l in args.languages.split(","):
            try:
                _train(d.strip(), l.strip())
            except Exception as e:  # pragma: no cover - top-level dispatcher
                print(f"[train-gpu] {d}/{l} FAILED: {e}")


if __name__ == "__main__":  # pragma: no cover
    main()
