"""Streamlit interface for the Agentic RFP Evaluation mini project."""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from database import DB_PATH, create_run, get_criteria, get_run_ids, get_run_results, initialize_database, persist_results, update_criteria
from documents import extract_pdf_text
from evaluation import calculate_scores, demo_evaluation, evaluate_with_llm, normalize_evaluation, parse_json_response

st.set_page_config(page_title="Agentic RFP Evaluator", page_icon="📑", layout="wide")
initialize_database()

st.title("📑 Agentic RFP Evaluator")
st.caption("Evidence-grounded supplier review · transparent scoring · deterministic ranking")

with st.sidebar:
    st.header("Evaluation mode")
    mode = st.radio("Choose how proposals are assessed", ["Demo (no API key)", "Live LLM"], help="Demo mode is a deterministic keyword heuristic for testing the workflow. Live LLM mode calls the selected model API.")
    api_key = ""
    model = "gpt-4o-mini"
    if mode == "Live LLM":
        api_key = st.text_input("LLM API key", type="password", help="Used only for this session; never save it in source code or commit it.")
        model = st.text_input("Model", value="gpt-4o-mini")
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
if uploads:
    metadata_rows = []
    for uploaded in uploads:
        defaults = next((item for item in st.session_state.get("supplier_metadata", []) if item["file"] == uploaded.name), None)
        metadata_rows.append({
            "file": uploaded.name,
            "supplier_name": defaults["supplier_name"] if defaults else Path(uploaded.name).stem.replace("_", " ").title(),
            "submission_date": defaults["submission_date"] if defaults else date.today(),
            "experience_rating": defaults["experience_rating"] if defaults else 3.0,
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

    if st.button("Evaluate suppliers", type="primary", disabled=not uploads):
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
            run_id = create_run()
            scorecards = []
            warnings = []
            progress = st.progress(0, text="Starting evaluation…")
            try:
                for index, (uploaded, supplier) in enumerate(zip(uploads, metadata.to_dict(orient="records")), start=1):
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
                    progress.progress(index / len(uploads), text=f"Evaluated {index} of {len(uploads)} suppliers")
                ranked, ranking_warnings = calculate_scores(scorecards, active_criteria)
                warnings.extend(ranking_warnings)
                persist_results(run_id, ranked)
                payload = {"rfp_run_id": run_id, "warnings": warnings, "ranking_rule": "PPI descending, submission date ascending, experience rating descending, supplier name ascending", "suppliers": ranked}
                st.session_state["latest_run"] = payload
                st.success(f"Evaluation complete · run {run_id}")
            except Exception as error:
                with sqlite3.connect(str(DB_PATH)) as connection:
                    connection.execute("UPDATE rfp_runs SET status='failed' WHERE rfp_run_id=?", (run_id,))
                st.error(f"Evaluation failed: {error}")
                st.info("Check that each PDF contains selectable text, the live API key/model is valid, and active criterion weights total 100%.")

latest = st.session_state.get("latest_run")
if latest:
    st.subheader("3 · Supplier leaderboard")
    st.caption(f"Run ID: `{latest['rfp_run_id']}` · Ranking: {latest['ranking_rule']}")
    leaderboard = [{key: supplier[key] for key in ("final_rank", "supplier_name", "absolute_score", "ppi", "submission_date", "experience_rating", "evaluation_mode")} for supplier in latest["suppliers"]]
    st.dataframe(pd.DataFrame(leaderboard), hide_index=True, width="stretch")
    if latest["warnings"]:
        with st.expander(f"Validation and scoring warnings ({len(latest['warnings'])})"):
            for warning in latest["warnings"]:
                st.warning(warning)
    for supplier in latest["suppliers"]:
        with st.expander(f"Rank {supplier['final_rank']} · {supplier['supplier_name']} · PPI {supplier['ppi']:.2f}%"):
            st.markdown(f"**Summary:** {supplier['overall_summary']}")
            rows = [{key: item[key] for key in ("name", "score", "max_score", "weight", "benchmark", "gap", "relative_performance", "evidence", "justification")} for item in supplier["criteria"]]
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
            if supplier["risks"]:
                st.markdown("**Risks and gaps**")
                for risk in supplier["risks"]:
                    st.markdown(f"- {risk}")
    st.download_button("Download complete run as JSON", data=json.dumps(latest, indent=2, ensure_ascii=False), file_name=f"rfp_run_{latest['rfp_run_id']}.json", mime="application/json")

st.subheader("4 · Previous runs")
run_ids = get_run_ids()
if run_ids:
    selected_run = st.selectbox("Load a completed run", run_ids)
    if st.button("Show selected run"):
        stored = get_run_results(selected_run)
        st.json({"rfp_run_id": selected_run, "suppliers": stored})
else:
    st.caption("Completed evaluations will be available here.")

st.divider()
st.caption("Evidence is extracted from submitted PDFs. Treat model scores as decision support, not an automated procurement decision; review evidence and risks before acting.")
