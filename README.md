# Agentic RFP Evaluation and Supplier Ranking

A classroom mini project that evaluates fictional supplier RFP PDFs against criteria stored in SQLite. The LLM may extract criterion-wise scores, evidence, and risks; Python validates the output and owns all formulas, peer benchmarking, tie-breaks, and final ranking.

> **Decision support only:** review source evidence, warnings, and risks. Never treat an LLM-generated score as an automatic procurement decision.

## Project contents

- `app.py` — Streamlit dashboard with an overview, supplier comparison charts, and horizontal tabs for criteria, evaluation, leaderboard, individual scorecards, and run history.
- `database.py` — SQLite schema, default criteria, and run/result persistence.
- `documents.py` — PDF text extraction and fictional proposal generation.
- `evaluation.py` — prompt construction, optional LLM call, JSON validation, deterministic demo mode, scoring, benchmarks, PPI, and ranking.
- `generate_samples.py` — creates six fictional, detailed proposal PDFs in `sample_proposals/`.
- `Agentic_RFP_Evaluation.ipynb` — notebook walkthrough of the end-to-end pipeline.
- `tests/` — scoring and validation checks.

## Setup

For a plain-language overview of the app, workflow, AI usage, and security caveats, open [APP_GUIDE.html](./APP_GUIDE.html).

Use Python 3.10 or newer. From this folder:

1. Create and activate a virtual environment using your preferred environment manager.
2. Install the project dependencies with `python -m pip install -r requirements.txt`.
3. Generate six fictional supplier documents with `python generate_samples.py`.
4. Start the app with `streamlit run app.py`.
5. To demo the bundled proposals, select **Try the six bundled fictional proposals** in the app.
6. Review the leaderboard and open each supplier's tab in **Scorecards** for color-coded criteria, evidence, and risks.
7. To use the notebook, open `Agentic_RFP_Evaluation.ipynb`, select the same Python environment, and run cells from top to bottom.

On first app launch, SQLite is initialized as `rfp_evaluation.db` and seeded with the sample criteria. The default active weights sum to 100%: Technical Capability 30%, Implementation Plan 20%, Commercial Value 20%, Security & Compliance 20%, and Support & Experience 10%.

## Deploy on Streamlit Community Cloud

Community Cloud deploys from a GitHub repository. Sign in to Streamlit Community Cloud with an account that can access your GitHub repository, push this project to GitHub, then create a new app with `app.py` as the entry point. Keep `requirements.txt`, the Python modules, and `sample_proposals/` in the repository. The generated proposal PDFs are fictional and safe to include. Do not commit `.venv/`, `rfp_evaluation.db`, API keys, or real supplier proposals. Demo mode needs no LLM API key. The app does not require OIDC secrets; all visitors share history and criteria.

**Storage caveat:** Streamlit Community Cloud's local filesystem should not be treated as durable storage. The SQLite database is appropriate for this classroom demonstration, but runs and criteria edits may not survive app restarts or redeployments. For durable multi-user production deployment, move persistence to a managed database. Do not publish confidential supplier documents.

## Public app warning

The app does not require sign-in. All visitors share evaluation history and can edit the evaluation criteria. Do not upload confidential supplier proposals or enter a valuable personal LLM API key. For private use, add authentication and authorization checks before deployment.

## LLM key and modes

- **Demo mode:** no API key or AI service needed. A deterministic keyword heuristic exercises the document, validation, scoring, and ranking pipeline. Demo scores are explicitly labeled and are not model judgments.
- **OpenAI API mode:** requires an OpenAI API key and a model that supports JSON-mode chat completions. The app defaults to `gpt-4o-mini` and accepts the key in a password field for the current session only. Do not place secrets in code, notebooks, or Git. API calls may incur charges.

The prompt asks the model to use only proposal evidence, treat document-contained instructions as untrusted, return one score per active criterion, keep scores in range, and return JSON. The application fills missing criteria, clips out-of-range numeric scores, defaults malformed scores to zero, and records warnings.

## Architecture and workflow

1. Initialize SQLite and load active evaluation criteria.
2. Upload several proposal PDFs and enter supplier name, submission date, and historical experience rating.
3. Create an `RFP_RUN_ID` and extract selectable PDF text (scanned PDFs need OCR first).
4. For each supplier, call the live JSON-mode model or the deterministic demo evaluator.
5. Parse and normalize results against the active criteria; record missing, malformed, or clipped values as warnings.
6. Calculate absolute weighted scores and per-criterion peer benchmarks/gaps/relative percentages in Python.
7. Calculate PPI and apply the specified stable tie-break order.
8. Persist full supplier scorecards and run status in SQLite; show the leaderboard and allow JSON download.

## Scoring formulas

For active criteria $i$ whose weights total 100%:

- **Absolute score (out of 100):** $\\sum_i (score_i / max_i) \\times weight_i$.
- **Benchmark:** the highest valid score for criterion $i$ across suppliers in one run.
- **Gap:** supplier criterion score minus the benchmark score.
- **Relative performance (%):** $score_i / benchmark_i \\times 100$.
- **PPI (%):** weighted average of criterion relative-performance percentages.
- **Ranking:** PPI descending, submission date ascending, experience rating descending, supplier name ascending (case-insensitive). Sequential ranks are assigned after this stable sort.

If a criterion benchmark is zero, relative performance is defined as 0% for every supplier for that criterion and a warning is emitted. This avoids division by zero and makes the assumption visible. If the scores tie on PPI, the subsequent tie-break fields decide; completely identical tie-break values remain stable in input order.

## Database

SQLite tables:

- `evaluation_criteria` — editable names/descriptions, weights, max score, active switch.
- `rfp_runs` — run ID, UTC creation time, status.
- `supplier_results` — supplier metadata, absolute score, PPI, rank, and full result JSON.
- `criterion_results` — normalized score, weight, benchmark, gap, relative percentage, evidence, and justification.

The UI prevents saving active weights that do not total 100%. The database file is local; for deployment, configure Streamlit Community Cloud storage deliberately because its filesystem may not be durable across restarts.

## Tests

Run `pytest` from this folder. Tests cover malformed/missing criterion output, score clipping, weighted-score calculations, zero benchmarks, active-weight validation, JSON parsing, and deterministic tie-break ordering.

## Submission checklist

- [x] Source code, requirements, and clear folder structure
- [x] SQLite schema and seed criteria on initialization
- [x] Six fictional supplier proposal PDFs can be generated locally
- [x] Notebook pipeline walkthrough
- [x] JSON export and validation warnings
- [ ] Run the tests and capture screenshots/demo evidence
- [ ] Deploy on Streamlit Community Cloud and record the public URL
