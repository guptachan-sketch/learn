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
    mode = st.radio(
        "Choose how proposals are assessed",
        ["Demo (no API key)", "OpenAI API"],
        help="Demo mode uses a deterministic keyword heuristic. OpenAI API mode sends proposal text to the selected OpenAI model.",
    )
    api_key = ""
    model = "gpt-4o-mini"
    if mode == "OpenAI API":
        api_key = st.text_input(
            "OpenAI API key",
            type="password",
            help="Used only for this session; never save it in source code or commit it.",
        )
        model = st.text_input("OpenAI model", value="gpt-4o-mini")
        st.warning("Proposal text is sent to OpenAI. Verify evidence before relying on scores.")
    else:
        st.success("Demo mode uses a keyword heuristic; no LLM or API key is used.")
    st.divider()
    st.caption("OpenAI API evaluations may incur charges and can vary. Arithmetic and supplier ordering are computed deterministically in Python.")

section_overview, section_criteria, section_evaluate, section_leaderboard, section_scorecards, section_history = st.tabs(
    ["Overview", "1 · Criteria", "2 · Evaluate suppliers", "3 · Leaderboard", "4 · Scorecards", "5 · History"]
)

criteria = get_criteria(active_only=False)
criteria_frame = pd.DataFrame(criteria)
latest = st.session_state.get("latest_run")

with section_overview:
    with st.container(border=True):
        intro, mode_summary = st.columns([3, 1])
        with intro:
            st.subheader("A clearer view of every proposal")
            st.write(
                "Compare suppliers against weighted criteria, inspect their evidence, "
                "and review risks before making a decision."
            )
        with mode_summary:
            if mode == "Demo (no API key)":
                st.success("Demo mode · no API key")
            else:
                st.warning(f"OpenAI API · {model}")

    active_criteria = [item for item in criteria if item["is_active"]]
    if latest and latest.get("suppliers"):
        best_supplier = latest["suppliers"][0]
        summary_columns = st.columns(4)
        summary_columns[0].metric("Suppliers evaluated", len(latest["suppliers"]))
        summary_columns[1].metric("Leading supplier", best_supplier["supplier_name"])
        summary_columns[2].metric("Top peer performance", f"{best_supplier['ppi']:.1f}%")
        summary_columns[3].metric("Active criteria", len(active_criteria))

        with st.container(border=True):
            st.markdown("#### At-a-glance comparison")
            st.caption("Scores are normalized to each criterion's maximum. Select Leaderboard for the full ranked view.")
            comparison_rows = [
                {
                    "Criterion": item["name"],
                    supplier["supplier_name"]: round(
                        float(item["score"]) / float(item["max_score"]) * 100, 1
                    ) if float(item["max_score"]) else 0.0,
                }
                for supplier in latest["suppliers"]
                for item in supplier["criteria"]
            ]
            comparison_data = (
                pd.DataFrame(comparison_rows)
                .groupby("Criterion", sort=False)
                .first()
            )
            st.bar_chart(
                comparison_data,
                horizontal=True,
                x_label="Score (% of criterion maximum)",
                y_label="Criterion",
                height=max(260, 52 * len(comparison_data)),
            )
    else:
        summary_columns = st.columns(3)
        summary_columns[0].metric("Active criteria", len(active_criteria))
        summary_columns[1].metric("Bundled examples", len(SAMPLE_SUPPLIERS))
        summary_columns[2].metric("Ready to evaluate", "Yes" if active_criteria else "No")
        with st.container(border=True):
            st.markdown("#### Get started")
            st.write("Open **Evaluate suppliers** and select the bundled fictional proposals for a quick end-to-end demo, or upload your own text-based PDFs.")
            st.caption("Demo scores are keyword-based examples, not AI judgments. Do not upload confidential supplier documents to this public app.")

with section_criteria:
    st.subheader("Evaluation criteria")
    st.caption("Set the active criteria and their weights. Active weights must total 100%.")
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
        st.caption(f"Active weights total: **{active_weight:g}%**")
        if st.button("Save criteria", key="save_criteria"):
            try:
                update_criteria(edited_criteria.to_dict(orient="records"))
                st.success("Criteria saved to SQLite.")
                st.rerun()
            except (ValueError, sqlite3.Error) as error:
                st.error(str(error))

with section_evaluate:
    st.subheader("Supplier proposals")
    st.caption("Choose the bundled fictional examples or upload text-based proposal PDFs.")
    uploads = st.file_uploader(
        "Upload supplier proposal PDFs",
        type=["pdf"],
        accept_multiple_files=True,
        help="Scanned PDFs need OCR before upload.",
    )
    use_sample_proposals = st.checkbox("Try the six bundled fictional proposals")
    sample_files = sorted(Path(__file__).with_name("sample_proposals").glob("*.pdf"))
    proposal_files = sample_files if use_sample_proposals else (uploads or [])
    if use_sample_proposals and uploads:
        st.info("Bundled fictional proposals are selected; uploaded files are ignored for this run.")
    if proposal_files:
        sample_metadata = {
            item["name"].lower().replace(" ", "_") + "_proposal.pdf": item
            for item in SAMPLE_SUPPLIERS
        }
        metadata_rows = []
        for proposal in proposal_files:
            proposal_name = proposal.name
            defaults = next(
                (item for item in st.session_state.get("supplier_metadata", []) if item["file"] == proposal_name),
                None,
            )
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
            },
            key="supplier_metadata_editor",
        )
        st.session_state["supplier_metadata"] = metadata.to_dict(orient="records")
        st.caption(f"{len(proposal_files)} proposal(s) ready to evaluate.")

        if st.button("Evaluate suppliers", type="primary", disabled=not proposal_files):
            active_criteria = get_criteria(active_only=True)
            if not active_criteria:
                st.error("Activate at least one criterion before evaluating suppliers.")
            elif abs(sum(float(item["weight"]) for item in active_criteria) - 100.0) > 0.01:
                st.error("Active criteria must have weights totaling exactly 100%.")
            elif mode == "OpenAI API" and not api_key:
                st.error("Enter your OpenAI API key, or choose Demo mode without a key.")
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
                    for index, (uploaded, supplier) in enumerate(
                        zip(proposal_files, metadata.to_dict(orient="records")), start=1
                    ):
                        supplier_name = str(supplier["supplier_name"]).strip()
                        with st.status(f"Evaluating {supplier_name}…", expanded=False) as status:
                            proposal_text = extract_pdf_text(uploaded)
                            raw = (
                                demo_evaluation(supplier_name, proposal_text, active_criteria)
                                if mode.startswith("Demo")
                                else evaluate_with_llm(supplier_name, proposal_text, active_criteria, api_key, model)
                            )
                            normalized, supplier_warnings = normalize_evaluation(
                                raw, active_criteria, supplier_name
                            )
                            normalized.update({
                                "submission_date": str(supplier["submission_date"]),
                                "experience_rating": float(supplier["experience_rating"]),
                                "source_file": uploaded.name,
                                "evaluation_mode": "demo" if mode.startswith("Demo") else f"openai:{model}",
                            })
                            scorecards.append(normalized)
                            warnings.extend(supplier_warnings)
                            status.update(label=f"Evaluated {supplier_name}", state="complete")
                        progress.progress(
                            index / len(proposal_files),
                            text=f"Evaluated {index} of {len(proposal_files)} suppliers",
                        )
                    ranked, ranking_warnings = calculate_scores(scorecards, active_criteria)
                    warnings.extend(ranking_warnings)
                    persist_results(run_id, PUBLIC_OWNER_ID, ranked)
                    latest = {
                        "rfp_run_id": run_id,
                        "warnings": warnings,
                        "ranking_rule": "PPI descending, submission date ascending, experience rating descending, supplier name ascending",
                        "suppliers": ranked,
                    }
                    st.session_state["latest_run"] = latest
                    st.success(f"Evaluation complete · run {run_id}")
                except Exception as error:
                    mark_run_failed(run_id, PUBLIC_OWNER_ID)
                    st.error(f"Evaluation failed: {error}")
                    st.info("Check the PDF text, live API key/model, and active criterion weights.")

with section_leaderboard:
    st.subheader("Supplier leaderboard")
    if latest:
        st.caption(f"Run ID: `{latest['rfp_run_id']}` · Sorted by {latest['ranking_rule']}.")
        leaderboard = [
            {
                "Rank": supplier["final_rank"],
                "Supplier": supplier["supplier_name"],
                "Weighted score": supplier["absolute_score"],
                "Peer performance (%)": supplier["ppi"],
                "Submission date": supplier["submission_date"],
                "Experience (0–5)": supplier["experience_rating"],
                "Evaluation": supplier["evaluation_mode"],
            }
            for supplier in latest["suppliers"]
        ]
        leaderboard_frame = pd.DataFrame(leaderboard)
        st.caption("Color key: green = strong, amber = review, red = needs attention.")
        chart_frame = leaderboard_frame.set_index("Supplier")[["Weighted score", "Peer performance (%)"]]
        with st.container(border=True):
            st.markdown("#### Score comparison")
            st.bar_chart(
                chart_frame,
                horizontal=True,
                x_label="Score",
                y_label="Supplier",
                height=max(260, 52 * len(chart_frame)),
            )
        styled_leaderboard = leaderboard_frame.style.map(
            performance_style, subset=["Weighted score"]
        ).map(relative_style, subset=["Peer performance (%)"])
        st.dataframe(styled_leaderboard, hide_index=True, width="stretch")
        if latest["warnings"]:
            with st.expander(f"Validation and scoring warnings ({len(latest['warnings'])})"):
                for warning in latest["warnings"]:
                    st.warning(warning)
        st.download_button(
            "Download complete run as JSON",
            data=json.dumps(latest, indent=2, ensure_ascii=False),
            file_name=f"rfp_run_{latest['rfp_run_id']}.json",
            mime="application/json",
        )
    else:
        st.info("No evaluation loaded yet. Choose proposals in the Evaluate suppliers tab.")

with section_scorecards:
    st.subheader("Detailed supplier scorecards")
    if latest and latest["suppliers"]:
        suppliers = latest["suppliers"]
        scorecard_tabs = st.tabs([
            f"{supplier['final_rank']} · {supplier['supplier_name']}"
            for supplier in suppliers
        ])
        for supplier, scorecard_tab in zip(suppliers, scorecard_tabs):
            with scorecard_tab:
                st.markdown(f"### {supplier['supplier_name']}")
                st.caption(f"Rank {supplier['final_rank']} · {supplier['evaluation_mode']}")
                st.write(supplier["overall_summary"])
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
                criteria_details = pd.DataFrame(rows)
                styled_details = criteria_details.style.map(
                    performance_style, subset=["Score (%)"]
                ).map(relative_style, subset=["Relative performance (%)"])
                st.dataframe(styled_details, hide_index=True, width="stretch")
                if supplier["risks"]:
                    st.warning("Risks and gaps to review")
                    for risk in supplier["risks"]:
                        st.markdown(f"- {risk}")
                st.caption(supplier["tie_break_explanation"])
    else:
        st.info("Supplier scorecards will appear here after an evaluation.")

with section_history:
    st.subheader("Previous runs")
    run_ids = get_run_ids(PUBLIC_OWNER_ID)
    if run_ids:
        selected_run = st.selectbox("Select a completed run", run_ids)
        if st.button("Load selected run"):
            stored = get_run_results(selected_run, PUBLIC_OWNER_ID)
            st.session_state["latest_run"] = {
                "rfp_run_id": selected_run,
                "warnings": [],
                "ranking_rule": "PPI descending, submission date ascending, experience rating descending, supplier name ascending",
                "suppliers": stored,
            }
            st.rerun()
    else:
        st.info("Completed evaluations will appear here.")

st.divider()
st.caption("Evidence is extracted from submitted PDFs. Treat model scores as decision support, not an automated procurement decision; verify source evidence before acting.")
