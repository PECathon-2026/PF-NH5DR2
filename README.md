# F:\Hackthon

**PrivacyLens** — Privacy-Preserving AI Browser Agent · PECathon 2026 · Hackathon Project

> Compute what is sensitive locally. Reason globally only on sanitized data.
>
> Build a system that lets an AI agent interact with digital interfaces (webpages,
> forms, dashboards) while detecting, redacting, and sanitizing sensitive user information
> before anything leaves the machine. Demonstrable, measurable, local-first.

## Team Charter (4 roles)

| Role | Person | Focus | Deliverable |
|---|---|---|---|
| **A — Detection** | | Regex + DOM structural + detection API | Pattern Layer, eval corpus, `detect()` service |
| **B — Local classifier** | | On-device PII classifier training | Fine-tuned local model + recall/precision eval |
| **C — Pipeline** | | Sanitization + reasoning + UI | Redaction pipeline, local LLM reasoning, demo UI |
| **D — Security + docs** | | Leakage proof + video + README | Canary tests, eval scripts, demo video, README |

```text
Client / Agent input (DOM, form, page)  ──►  Detection Layer  ──►  Sanitization  ──►  Local LLM reasoning
   (screenshots, DOM tree, form fields)        (regex + NER model)      (mask/placeholder)     (action validation)
        │                                              │                       │                       │
        ▼                                              ▼                       ▼                       ▼
   Capture raw data                              Sensitive masked        Clean context          Act on sanitized
   (for test/leak audit)                         regions                  (with placeholders)    interface
        │                                              │                       │                       │
        └──────────────────────►  Canary leakage audit  ◄──────────────────────┘                       │
        └──────────────────────►  eval results (D)  ──►  README / video ──────────────────────────────┘
```

## Core Rules (head approval)
1. **Nothing sensitive leaves the machine** — every detection + redaction runs locally. No cloud calls on raw data.
2. **Canary-verified** — inject fake fake-values; require `leakage_count == 0` to claim "no leakage".
3. **Fail-closed** — on detection/sanitization failure, block the action; do not silently pass raw data.
4. **Measure everything** — recall, precision, leakage rate, task-success, latency on every dev build.

## Repo Layout

```text
F:/Hackthon
├─ README.md
├─ requirements.txt          # project dependencies
├─ .gitignore
├─ src/
│  ├─ detection/             # pattern + DOM structural layer
│  ├─ model/                 # local PII classifier + training
│  ├─ pipeline/              # redaction + reasoning + UI
│  └─ eval/                  # canary leakage tests + eval harness
├─ data/
│  ├─ corpus/                # training corpus (dlptest + Faker-generated)
│  └─ dlptest/               # downloaded sample data
├─ models/                   # local model weights
├─ demo/                     # demo UI + assets
├─ video/                    # demo video + assets
└─ doc/                      # architecture, threat model, security docs
```

## Quick Start (after 12–24h)

```bash
# 1. create venv + install
python -m venv .venv && .\.venv\Scripts\activate
pip install -r requirements.txt

The default configuration uses the Transformers engine, so the GGUF runtime is
optional. If you switch `config.yaml` to a GGUF engine, install it separately:

```powershell
python -m pip install -r requirements-gguf.txt
```

On Windows with Python 3.13, `llama-cpp-python` may not have a compatible
prebuilt wheel and pip will fall back to compiling it. Use Python 3.11 or 3.12
for a prebuilt wheel when available, or install the Visual C++ build tools and
CMake before running the optional install.

# 2. generate synthetic corpus (Person B)
python src/model/corpus/build_corpus.py --out F:/Hackthon/data/corpus

# 3. train local classifier (Person B)
python src/model/train.py --corpus F:/Hackthon/data/corpus --out models/pii_classifier

# 4. run detection + sanitization (Person A/C)
python src/pipeline/sanitize.py --corpus F:/Hackthon/data/corpus
```

## Current Status

| Phase | Status |
|---|---|
| Repo scaffolding | ✅ Done (this file) |
| Detection layer | ⏳ Pending (start 2nd) |
| Local classifier | ⏳ Pending |
| Sanitization + reasoning | ⏳ Pending |
| Evaluation + demo | ⏳ Pending |

## Sources used

- **dlptest.com/sample-data** — synthetic PII/PCI corpus for training + eval
- **bigcode/starpii** — pre-fine-tuned NER fallback for code-domain PII (gated; optional)
- **amazon-science/fraud-dataset-benchmark** — card-fraud context (not raw-card training data)
