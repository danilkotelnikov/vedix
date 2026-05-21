# SGCA Gold Set — protocol

Per spec §8.2, the gold set is 50 papers across the niche-coverage benchmark,
each with hand-extracted KG fragments by 2 domain experts (>=1 chemistry, >=1
biology).

This directory ships with 3 starter papers as a scaffold so the benchmark
runner is testable today. The full 50-paper curation is a separate data-
collection task (track it as a follow-up; not in v3.0 critical path).

## Layout

```
tests/sgca/gold_set/
├── README.md          (this file)
├── _seed.yaml         (3 starter papers — KG fragments + raw text references)
├── papers/
│   └── <paper_id>/
│       ├── raw.txt
│       └── gold_kg.yaml
└── verifier_pairs.jsonl  (500 hand-labeled (sentence, anchor) pairs)
```

## Production gate

- claim_f1 >= 0.85
- verbatim_quote_exact_match_rate = 1.0
