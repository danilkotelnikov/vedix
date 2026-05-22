# Publisher templates

23 templates ship in the box. Pick one in the setup form; Vedix typesets the
final manuscript in that venue's house style and produces both a LaTeX
source tree and a parity Word document.

## Bundled venues

| Code | Venue family | Output |
| --- | --- | --- |
| `nature` | Nature, Nat. Comms, Sci. Reps. | LaTeX + DOCX |
| `elsevier:cas-single` | Elsevier CAS single column | LaTeX + DOCX |
| `elsevier:cell-reports-medicine` | Cell Reports Medicine | LaTeX + DOCX |
| `springer` | Springer Nature standard | LaTeX + DOCX |
| `taylor-francis` | Taylor & Francis | LaTeX + DOCX |
| `frontiers` | Frontiers in &hellip; | LaTeX + DOCX |
| `wiley` | Wiley | LaTeX + DOCX |
| `sage` | SAGE | LaTeX + DOCX |
| `plos` | PLOS One / Comp Bio | LaTeX + DOCX |
| `cell` | Cell Press | LaTeX + DOCX |
| `ieee` | IEEE journals + conferences | LaTeX |
| `acm` | ACM | LaTeX |
| `acs` | ACS journals | LaTeX + DOCX |
| `mdpi` | MDPI | LaTeX + DOCX |
| `revtex` | APS / RevTeX | LaTeX |
| `rsc` | Royal Society of Chemistry | LaTeX + DOCX |
| `cambridge` | Cambridge University Press | LaTeX + DOCX |
| `oup` | Oxford University Press | LaTeX + DOCX |
| `bmj` | BMJ | LaTeX + DOCX |
| `jama` | JAMA Network | LaTeX + DOCX |
| `gost-generic` | GOST-7.0.5 generic | LaTeX + DOCX |
| `dan-ras` | DAN RAS (Doklady) | LaTeX |
| `uspekhi` | Uspekhi Fiz. Nauk | LaTeX |
| `preprint` | Overleaf-style preprint | LaTeX + DOCX |

## Switching venues

You can retypeset an existing job into a new venue without re-running the
pipeline:

```text
/vedix retypeset <job_id> --venue elsevier:cell-reports-medicine
```

The publisher engine reuses the manuscript content and only rebuilds the
LaTeX class wiring, references, and figure environments.

## Adding a venue

Each template lives under `templates/<venue-code>/` and consists of a
class file (`.cls`), a BibLaTeX style (`.bbx` + `.cbx`), a Word parity
template (`.dotx`), and a small manifest that lists section ordering and
mandatory front matter. See `scripts/fetch_publisher_templates.py` for the
upstream sources and provenance.
