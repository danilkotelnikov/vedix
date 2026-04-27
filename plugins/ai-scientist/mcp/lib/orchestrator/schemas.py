"""Strict JSON schemas per phase output. Per spec §4.3.

Two enforcement points:
  1. `strict: true` on the agent's tool-use schema (where the host supports it)
  2. validate_against() called on the parsed output before commit
On schema violation: re-prompt with the validator error inlined, max 2 retries.
"""
from __future__ import annotations
import jsonschema


def validate_against(obj, schema):
    """Raise jsonschema.ValidationError if obj fails the schema."""
    jsonschema.validate(obj, schema)


IDEATION_SCHEMA = {
    "type": "object",
    "required": ["Name", "Title", "Short_Hypothesis", "Related_Work",
                 "Abstract", "Experiments", "Risks"],
    "properties": {
        "Name":             {"type": "string", "minLength": 1},
        "Title":            {"type": "string", "minLength": 1},
        "Short_Hypothesis": {"type": "string", "minLength": 1},
        "Related_Work":     {"type": "string"},
        "Abstract":         {"type": "string", "minLength": 50},
        "Experiments":      {"type": "array", "minItems": 1,
                             "items": {"type": "object", "required": ["name", "metric"]}},
        "Risks":            {"type": "array"},
    },
}

HYPOTHESIS_SCHEMA = {
    "type": "object",
    "required": ["hypothesis", "math_models", "statistical_framework",
                 "methodology", "dependencies"],
    "properties": {
        "hypothesis":            {"type": "string", "minLength": 10},
        "math_models":           {"type": "string"},
        "statistical_framework": {"type": "object"},
        "methodology":           {"type": "string"},
        "dependencies":          {"type": "array", "items": {"type": "string"}},
    },
}

REVIEW_SCHEMA = {
    "type": "object",
    "required": ["Summary", "Strengths", "Weaknesses",
                 "Originality", "Quality", "Clarity", "Significance",
                 "Soundness", "Presentation", "Contribution",
                 "Overall", "Confidence", "Decision",
                 "Questions", "Limitations", "Actionable_Fixes"],
    "properties": {
        "Summary":     {"type": "string"},
        "Strengths":   {"type": "array", "items": {"type": "string"}},
        "Weaknesses":  {"type": "array", "items": {"type": "string"}},
        "Originality": {"type": "integer", "minimum": 1, "maximum": 4},
        "Quality":     {"type": "integer", "minimum": 1, "maximum": 4},
        "Clarity":     {"type": "integer", "minimum": 1, "maximum": 4},
        "Significance":{"type": "integer", "minimum": 1, "maximum": 4},
        "Soundness":   {"type": "integer", "minimum": 1, "maximum": 4},
        "Presentation":{"type": "integer", "minimum": 1, "maximum": 4},
        "Contribution":{"type": "integer", "minimum": 1, "maximum": 4},
        "Overall":     {"type": "integer", "minimum": 1, "maximum": 10},
        "Confidence":  {"type": "integer", "minimum": 1, "maximum": 5},
        "Decision":    {"type": "string"},
        "Questions":   {"type": "array"},
        "Limitations": {"type": "array"},
        "Actionable_Fixes": {"type": "array", "items": {"type": "string"}},
    },
}

EXPERIMENT_RESULT_SCHEMA = {
    "type": "object",
    "required": ["exit_code", "results_csv_present", "npy_files", "figures",
                 "fix_attempts", "stdout_summary", "stderr_summary"],
    "properties": {
        "exit_code":           {"type": "integer"},
        "results_csv_present": {"type": "boolean"},
        "npy_files":           {"type": "array", "items": {"type": "string"}},
        "figures":             {"type": "array", "items": {"type": "string"}},
        "fix_attempts":        {"type": "integer", "minimum": 0},
        "stdout_summary":      {"type": "string"},
        "stderr_summary":      {"type": "string"},
    },
}
