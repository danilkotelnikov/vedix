# Training the register classifier

The hybrid register discriminator (Layer A + Layer B) ships as a
6 GB pretrained model. Most users never need to retrain. This page documents
the training pipeline for the unusual case where you do.

## When to retrain

- You're working in a discipline whose register diverges from the bundled
  corpus (e.g., niche humanities subfields, novel scientific subfields).
- You want to add a new language whose locale module is in place but whose
  register conventions aren't covered.
- You've collected a private corpus you can't upload to the SaaS for
  pretraining.

## CPU vs GPU

Two trainers live in `scripts/`:

- `train_register_classifier_cpu.py` &mdash; 12&ndash;36 hours on a modern
  laptop, no GPU required.
- `train_register_classifier_gpu.py` &mdash; 1&ndash;3 hours on a single A100
  or H100.

An auto-dispatcher (`train_register_classifier.py`) picks the right one
based on CUDA visibility.

## Pipeline

1. `prepare_corpus.py` &mdash; pulls the 10 upstream sources and produces
   `data/register/v1/train.jsonl` + `val.jsonl`.
2. `train_register_classifier.py --epochs 8` &mdash; trains Layer A
   (retrieval discriminator) + Layer B (style classifier).
3. The trained checkpoint lands at `~/.vedix/models/register_classifier.bin`
   and is picked up automatically on next pipeline run.

[Full reference for the corpus pipeline is in development.]
