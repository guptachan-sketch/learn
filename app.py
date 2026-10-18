"""Streamlit interface for the Agentic RFP Evaluation mini project."""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from database import DB_PATH, create_run, get_criteria, get_run_ids, get_run_results, initialize_database, mark_run_failed, persist_results, update_criteria
from documents import SAMPLE_SUPPLIERS, extract_pdf_text
from evaluation import calculate_scores, demo_evaluation, evaluate_with_llm, normalize_evaluation, parse_json_response

st.set_page_config(page_title="Agentic RFP Evaluator", page_icon="📑", layout="wide")

PUBLIC_OWNER_ID = "public"


def performance_style(value: object) -> str:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return ""
    if score >= 80:
        return "background-color: #dcfce7; color: #166534; font-weight: 700"
    if score >= 60:
        return "background-color: #fef3c7; color: #92400e; font-weight: 700"
    return "background-color: #fee2e2; color: #991b1b; font-weight: 700"


def relative_style(value: object) -> str:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return ""
    if score >= 90:
        return "background-color: #dcfce7; color: #166534; font-weight: 700"
    if score >= 70:
        return "background-color: #fef3c7; color: #92400e; font-weight: 700"
    return "background-color: #fee2e2; color: #991b1b; font-weight: 700"


initialize_database()

st.title("📑 Agentic RFP Evaluator")
st.caption("Evidence-grounded supplier review · transparent scoring · deterministic ranking")

with st.sidebar:
    st.warning("Public app: evaluation history and criteria are shared with all visitors.")
    st.header("Evaluation mode")
    mode = st.radio("Choose how proposals are assessed", ["Demo (no API key)", "Live LLM"], help="Demo mode is a deterministic keyword heuristic for testing the workflow. Live LLM mode calls the selected model API.")
    api_key = ""
    model = "gpt-4o-mini"
    if mode == "Live LLM":
        api_key = st.text_input("LLM API key", type="password", help="Used only for this session; never save it in source code or commit it.")
        model = st.text_input("Model", value="gpt-4o-mini")
        st.warning("Live mode sends proposal text to the selected model provider. Verify evidence before relying on scores.")
    else:
        st.success("Demo mode uses a keyword heuristic; no LLM or API key is used.")
    st.divider()
    st.caption("Live LLM evaluations incur provider charges and can vary. Arithmetic and supplier ordering are computed deterministically in Python.")

st.subheader("1 · Evaluation criteria")
criteria = get_criteria(active_only=False)
criteria_frame = pd.DataFrame(criteria)
if not criteria_frame.empty:
    edited_criteria = st.data_editor(
        criteria_frame,
        column_config={
            "criterion_id": st.column_config.NumberColumn("ID", disabled=True),
            "name": st.column_config.TextColumn("Criterion", disabled=True),
            "description": st.column_config.TextColumn("What to assess", width="large"),
            "weight": st.column_config.NumberColumn("Weight (%)", min_value=0.0, max_value=100.0, step=1.0),
            "max_score": st.column_config.NumberColumn("Maximum score", min_value=0.1, max_value=100.0, step=0.5),
            "is_active": st.column_config.CheckboxColumn("Active"),
        },
        hide_index=True, width="stretch", key="criteria_editor",
    )
    active_weight = float(edited_criteria.loc[edited_criteria["is_active"], "weight"].sum())
    st.caption(f"Active weights total: **{active_weight:g}%** (must equal 100%).")
    if st.button("Save criteria", key="save_criteria"):
        try:
            update_criteria(edited_criteria.to_dict(orient="records"))
            st.success("Criteria saved to SQLite.")
            st.rerun()
        except (ValueError, sqlite3.Error) as error:
            st.error(str(error))

st.subheader("2 · Supplier proposals")
uploads = st.file_uploader("Upload supplier proposal PDFs", type=["pdf"], accept_multiple_files=True, help="Text-based PDFs are supported; scanned documents need OCR before upload.")
use_sample_proposals = st.checkbox("Try the six bundled fictional proposals")
sample_files = sorted(Path(__file__).with_name("sample_proposals").glob("*.pdf"))
proposal_files = sample_files if use_sample_proposals else (uploads or [])
if use_sample_proposals and uploads:
    st.info("Bundled fictional proposals are selected; uploaded files are ignored for this run.")
if proposal_files:
    sample_metadata = {item["name"].lower().replace(" ", "_") + "_proposal.pdf": item for item in SAMPLE_SUPPLIERS}
    metadata_rows = []
    for proposal in proposal_files:
        proposal_name = proposal.name
        defaults = next((item for item in st.session_state.get("supplier_metadata", []) if item["file"] == proposal_name), None)
        sample = sample_metadata.get(proposal_name)
        metadata_rows.append({
            "file": proposal_name,
            "supplier_name": defaults["supplier_name"] if defaults else sample["name"] if sample else Path(proposal_name).stem.replace("_", " ").title(),
            "submission_date": defaults["submission_date"] if defaults else date.fromisoformat(sample["date"]) if sample else date.today(),
            "experience_rating": defaults["experience_rating"] if defaults else sample["experience"] if sample else 3.0,
        })
    metadata = st.data_editor(
        pd.DataFrame(metadata_rows), hide_index=True, width="stretch",
        column_config={
            "file": st.column_config.TextColumn("Uploaded PDF", disabled=True),
            "supplier_name": st.column_config.TextColumn("Supplier name", required=True),
            "submission_date": st.column_config.DateColumn("Submission date", required=True),
            "experience_rating": st.column_config.NumberColumn("Historical experience (0–5)", min_value=0.0, max_value=5.0, step=0.5),
        }, key="supplier_metadata_editor",
    )
    st.session_state["supplier_metadata"] = metadata.to_dict(orient="records")

    if st.button("Evaluate suppliers", type="primary", disabled=not proposal_files):
        active_criteria = get_criteria(active_only=True)
        if not active_criteria:
            st.error("Activate at least one criterion before evaluating suppliers.")
        elif abs(sum(float(item["weight"]) for item in active_criteria) - 100.0) > 0.01:
            st.error("Active criteria must have weights totaling exactly 100%.")
        elif mode == "Live LLM" and not api_key:
            st.error("Enter your API key for Live LLM mode, or use Demo mode without a key.")
        elif metadata["supplier_name"].astype(str).str.strip().eq("").any():
            st.error("Every uploaded PDF needs a supplier name.")
        elif metadata["supplier_name"].astype(str).str.casefold().duplicated().any():
            st.error("Supplier names must be unique within one evaluation batch.")
        else:
            run_id = create_run(PUBLIC_OWNER_ID)
            scorecards = []
            warnings = []
            progress = st.progress(0, text="Starting evaluation…")
            try:
                for index, (uploaded, supplier) in enumerate(zip(proposal_files, metadata.to_dict(orient="records")), start=1):
                    supplier_name = str(supplier["supplier_name"]).strip()
                    with st.status(f"Evaluating {supplier_name}…", expanded=False) as status:
                        proposal_text = extract_pdf_text(uploaded)
                        raw = demo_evaluation(supplier_name, proposal_text, active_criteria) if mode.startswith("Demo") else evaluate_with_llm(supplier_name, proposal_text, active_criteria, api_key, model)
                        normalized, supplier_warnings = normalize_evaluation(raw, active_criteria, supplier_name)
                        normalized.update({
                            "submission_date": str(supplier["submission_date"]),
                            "experience_rating": float(supplier["experience_rating"]),
                            "source_file": uploaded.name,
                            "evaluation_mode": "demo" if mode.startswith("Demo") else f"llm:{model}",
                        })
                        scorecards.append(normalized)
                        warnings.extend(supplier_warnings)
                        status.update(label=f"Evaluated {supplier_name}", state="complete")
                    progress.progress(index / len(proposal_files), text=f"Evaluated {index} of {len(proposal_files)} suppliers")
                ranked, ranking_warnings = calculate_scores(scorecards, active_criteria)
                warnings.extend(ranking_warnings)
                persist_results(run_id, PUBLIC_OWNER_ID, ranked)
                payload = {"rfp_run_id": run_id, "warnings": warnings, "ranking_rule": "PPI descending, submission date ascending, experience rating descending, supplier name ascending", "suppliers": ranked}
                st.session_state["latest_run"] = payload
                st.success(f"Evaluation complete · run {run_id}")
            except Exception as error:
                mark_run_failed(run_id, PUBLIC_OWNER_ID)
                st.error(f"Evaluation failed: {error}")
                st.info("Check that each PDF contains selectable text, the live API key/model is valid, and active criterion weights total 100%.")

latest = st.session_state.get("latest_run")
if latest:
    st.subheader("3 · Supplier leaderboard")
    st.caption(f"Run ID: `{latest['rfp_run_id']}` · Ranking: {latest['ranking_rule']}")
    leaderboard = [{key: supplier[key] for key in ("final_rank", "supplier_name", "absolute_score", "ppi", "submission_date", "experience_rating", "evaluation_mode")} for supplier in latest["suppliers"]]
    leaderboard_frame = pd.DataFrame(leaderboard)
    st.caption("Color key: green = strong, amber = review, red = needs attention.")
    styled_leaderboard = leaderboard_frame.style.map(
        performance_style, subset=["absolute_score"]
    ).map(relative_style, subset=["ppi"])
    st.dataframe(styled_leaderboard, hide_index=True, width="stretch")
    if latest["warnings"]:
        with st.expander(f"Validation and scoring warnings ({len(latest['warnings'])})"):
            for warning in latest["warnings"]:
                st.warning(warning)
    for supplier in latest["suppliers"]:
        with st.expander(f"Rank {supplier['final_rank']} · {supplier['supplier_name']} · PPI {supplier['ppi']:.2f}%"):
            st.markdown(f"**Summary:** {supplier['overall_summary']}")
            metric_columns = st.columns(3)
            metric_columns[0].metric("Weighted score", f"{supplier['absolute_score']:.2f} / 100")
            metric_columns[1].metric("Peer performance", f"{supplier['ppi']:.2f}%")
            metric_columns[2].metric("Historical experience", f"{supplier['experience_rating']:.1f} / 5")
            rows = [{
                "Criterion": item["name"],
                "Score (%)": round(item["score"] / item["max_score"] * 100, 2) if item["max_score"] else 0,
                "Score": item["score"],
                "Maximum": item["max_score"],
                "Weight (%)": item["weight"],
                "Benchmark": item["benchmark"],
                "Gap": item["gap"],
                "Relative performance (%)": item["relative_performance"],
                "Evidence": item["evidence"],
                "Justification": item["justification"],
            } for item in supplier["criteria"]]
            criteria_frame = pd.DataFrame(rows)
            styled_criteria = criteria_frame.style.map(
                performance_style, subset=["Score (%)"]
            ).map(relative_style, subset=["Relative performance (%)"])
            st.dataframe(styled_criteria, hide_index=True, width="stretch")
            if supplier["risks"]:
                st.warning("Risks and gaps to review")
                for risk in supplier["risks"]:
                    st.markdown(f"- {risk}")
    st.download_button("Download complete run as JSON", data=json.dumps(latest, indent=2, ensure_ascii=False), file_name=f"rfp_run_{latest['rfp_run_id']}.json", mime="application/json")

st.subheader("4 · Previous runs")
run_ids = get_run_ids(PUBLIC_OWNER_ID)
if run_ids:
    selected_run = st.selectbox("Load a completed run", run_ids)
    if st.button("Show selected run"):
        stored = get_run_results(selected_run, PUBLIC_OWNER_ID)
        st.json({"rfp_run_id": selected_run, "suppliers": stored})
else:
    st.caption("Completed evaluations will be available here.")

st.divider()
st.caption("Evidence is extracted from submitted PDFs. Treat model scores as decision support, not an automated procurement decision; review evidence and risks before acting.")
