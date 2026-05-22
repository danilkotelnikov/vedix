# Languages

Vedix treats seven languages as first-class: each has a locale module that
governs hyphenation, citation conventions, journal house style, numerical
notation, and any language-specific rigor heuristics (for example, the
Russian locale applies GOST-7.0.5 reference formatting and turns off em-dash
typesetting that some Russian style guides discourage).

## Supported languages

| Code | Language | Citation style | Notes |
| --- | --- | --- | --- |
| `en` | English | Numeric / author-year | Default |
| `ru` | Russian | GOST-7.0.5 | Includes VAK perechen' compliance |
| `es` | Spanish | RAE conventions | |
| `de` | German | DIN-1505 | |
| `fr` | French | Norme typographique | Non-breaking spaces before `;:?!` |
| `zh` | Simplified Chinese | GB/T 7714 | |
| `ja` | Japanese | SIST 02 | |

## Selecting a language

In the setup form, the `Language` field accepts any of the codes above.
Vedix routes locale-specific behaviour through `plugins/vedix/locale/<code>.py`
modules.

## Adding a language

A locale module is roughly 200 lines: hyphenation rules, a reference
formatter, a small list of language-specific prompt overrides, and any
publishing-tradition glyph substitutions. See
`plugins/vedix/locale/protocol.py` for the contract every locale implements.

[Full per-language reference is in development.]
