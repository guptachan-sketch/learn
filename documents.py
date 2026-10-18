"""PDF text extraction and fictional sample proposal generation."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pypdf import PdfReader


def extract_pdf_text(file_or_path: Any, max_chars: int = 60000) -> str:
    """Extract text page-by-page from a PDF upload or filesystem path."""
    reader = PdfReader(file_or_path)
    if reader.is_encrypted:
        raise ValueError("The PDF is password protected; upload an unlocked copy.")
    pages = []
    for page_number, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        if page_text.strip():
            pages.append(f"[Page {page_number}]\n{page_text.strip()}")
    text = "\n\n".join(pages).strip()
    if not text:
        raise ValueError("No selectable text was found. Scanned-image PDFs need OCR before upload.")
    if len(text) > max_chars:
        text = text[:max_chars] + "\n[Text truncated for the model context limit.]"
    return text


SAMPLE_SUPPLIERS = [
    {
        "name": "Apex Systems", "date": "2026-10-01", "experience": 4.5,
        "profile": "Strong technical design and security; higher price; moderate delivery schedule.",
        "architecture": "A modular cloud architecture uses documented APIs, a scalable event-driven integration layer, and an auditable migration path. The proposed platform supports redundancy, monitoring, and future growth.",
        "plan": "A discovery phase is followed by a prototype, staged migration, and acceptance testing over 24 weeks. A named project lead and six engineers provide weekly milestones. The risk plan covers migration rollback and integration dependencies.",
        "price": "The fixed implementation fee is USD 480,000, plus an estimated USD 72,000 annual cloud cost. Assumptions and optional services are itemized; taxes and third-party licenses are excluded.",
        "security": "Security controls include encryption in transit and at rest, role-based access, annual penetration testing, audit logging, and a documented incident response plan. ISO 27001 certification is maintained.",
        "support": "24/7 priority-one support has a one-hour response SLA. Apex cites three enterprise references and twelve years of delivery experience.",
    },
    {
        "name": "BrightPath Tech", "date": "2026-10-03", "experience": 2.5,
        "profile": "Lowest price and fast timeline; weak compliance detail and limited experience.",
        "architecture": "The solution connects to existing systems through APIs and a hosted platform. Capacity can be increased as required. Detailed architecture diagrams and integration test evidence will be supplied after award.",
        "plan": "BrightPath proposes a ten-week implementation with a small delivery team. The schedule includes configuration and launch but does not describe formal milestones, staffing allocation, or a contingency plan.",
        "price": "The estimated total is USD 210,000. The short quote does not separate recurring cloud costs, optional work, taxes, or third-party licensing assumptions.",
        "security": "The platform uses standard access controls. The proposal does not specify encryption standards, audit retention, independent certifications, privacy controls, or incident response procedures.",
        "support": "Email support is available during business hours. BrightPath has two years of company history and one small-business reference; no response-time commitment is stated.",
    },
    {
        "name": "NexaWorks", "date": "2026-10-02", "experience": 4.0,
        "profile": "Balanced proposal; strongest implementation plan and support model.",
        "architecture": "A containerized service integrates with the client API gateway and identity provider. Horizontal scaling, API versioning, observability, and a staged data migration are documented. A load-test plan is included.",
        "plan": "A 16-week roadmap defines discovery, design, two delivery increments, user acceptance, and handover. The proposal names a project manager, architect, security lead, and six engineers. A RAID log, weekly steering meetings, and rollback milestones address delivery risk.",
        "price": "The proposal estimates USD 350,000 implementation and USD 54,000 annual hosting. A line-item table identifies travel, taxes, support tiers, and third-party license assumptions.",
        "security": "Controls include TLS encryption, managed keys, SSO, least-privilege roles, immutable audit logs, data-retention settings, and a 72-hour incident notification target. SOC 2 Type II evidence is available under NDA.",
        "support": "NexaWorks offers 24/7 on-call support with a 30-minute critical-incident response SLA. The proposal includes a transition plan, quarterly service reviews, four comparable references, and eight years of experience.",
    },
    {
        "name": "Orbit Digital", "date": "2026-10-02", "experience": 5.0,
        "profile": "Strong experience and references; vague integration plan; medium pricing.",
        "architecture": "Orbit proposes a modern cloud-native platform with scalable services and a broad integration catalogue. The response does not identify the exact interface mapping, API ownership, or migration sequence for the requested systems.",
        "plan": "A 20-week delivery is proposed with monthly checkpoints. The team includes senior consultants and a delivery manager. Staffing levels by phase and risk mitigations for integration dependencies are not detailed.",
        "price": "The indicative price is USD 365,000 implementation and USD 60,000 annual operations. Several assumptions are listed, but data migration and premium support are priced as later options.",
        "security": "Orbit describes encryption, access reviews, privacy training, and central audit logging. A SOC 2 report and penetration-test summary can be shared during due diligence; control ownership is not mapped in detail.",
        "support": "A named customer-success manager, 24/7 critical support, and a one-hour response target are offered. Orbit reports fifteen years of experience and five relevant enterprise references.",
    },
    {
        "name": "CedarPeak Solutions", "date": "2026-10-04", "experience": 3.5,
        "profile": "Strong governance and migration planning; moderate pricing; limited detail on round-the-clock support.",
        "architecture": "CedarPeak proposes a hybrid deployment with a documented API gateway, customer-managed identity connection, and separately monitored data import service. The design supports horizontal scaling and a sandbox for integration tests. API throttling and recovery targets need joint design approval.",
        "plan": "A 22-week delivery is organized into discovery, prototype, two migration waves, user acceptance, and handover. A delivery manager and data lead are named. Weekly risk reviews and a rollback rehearsal are planned before launch; buyer data-cleanup work is excluded.",
        "price": "The proposal estimates USD 395,000 for implementation and USD 58,000 per year for hosting and standard support. Data cleansing and premium coverage are separately priced. Confirm renewal increases, migration overages, taxes, and third-party costs.",
        "security": "CedarPeak describes encryption, quarterly access reviews, centralized audit logs, and annual independent penetration testing. A control workbook is available on request, but formal certification status is not stated. Validate remediation targets, breach notification, backup recovery, and data deletion.",
        "support": "Business-hours support is included with a two-hour critical response target. A named service manager and monthly incident reports are offered; after-hours coverage costs extra. Confirm holiday coverage, escalation contacts, severity definitions, and service credits.",
    },
    {
        "name": "Harborlight Systems", "date": "2026-10-05", "experience": 4.5,
        "profile": "Mature security evidence and service operations; higher recurring fees; phased rollout across regions.",
        "architecture": "Harborlight offers a managed cloud platform with regional deployment options, documented REST APIs, single sign-on, and centralized monitoring. Workloads are separated by environment and protected with network policies. Confirm data residency, recovery-time objectives, and integration throughput.",
        "plan": "A 26-week rollout begins with a pilot business unit, followed by two regional waves and service transition. Go/no-go criteria, rollback steps, and two-week stabilization periods are planned for each wave. The schedule depends on local data-owner availability.",
        "price": "The quoted implementation is USD 520,000 with annual platform and operations fees of USD 88,000. The estimate includes a pilot and two rollout waves; premium analytics and extra regions are optional. Review renewal terms, overage pricing, taxes, and data export fees.",
        "security": "Harborlight reports SOC 2 Type II coverage, encryption at rest and in transit, privileged-access monitoring, and tested backups. Penetration-test findings are summarized under NDA. Validate report scope and period, subprocessors, deletion commitments, and customer audit rights.",
        "support": "The service includes 24/7 critical-incident intake, a 45-minute response target, a named service manager, and monthly availability reporting. Four comparable enterprise references are available. Clarify resolution targets, service credits, maintenance notice, and escalation contacts.",
    },
]

SAMPLE_APPENDICES = {
    "Apex Systems": [
        "Discovery should confirm peak transaction volumes, interface owners, data retention, and regional hosting constraints. A sandbox integration is recommended before the final architecture baseline is approved.",
        "For acceptance, the buyer should request API contract-test results, a migration reconciliation report, a sample penetration-test summary, and evidence that the documented recovery steps were rehearsed.",
        "Key dependencies include timely access to test systems and approval of migration mappings. The fixed fee excludes taxes and third-party licenses, while cloud costs vary with actual use; contract terms should state how changes are approved.",
    ],
    "BrightPath Tech": [
        "The proposal is an early estimate. Before award, request named delivery roles, milestone exit criteria, a data migration plan, a recovery objective, and a written support escalation path.",
        "Security review should establish encryption standards, audit-log retention, independent assurance evidence, incident notification timing, data location, and how customer data is deleted at contract end.",
        "The low initial price excludes or leaves unclear recurring cloud charges, licenses, taxes, and optional work. Request a comparable multi-year total-cost schedule and written response commitments.",
    ],
    "NexaWorks": [
        "The staged design should be validated against expected peak loads and actual source-data quality. Confirm API rate limits, field-level ownership, retention rules, and who controls production encryption keys.",
        "Useful acceptance evidence includes load-test results, sample migration reconciliations, rollback rehearsal records, training completion, and a signed handover checklist for the service team.",
        "The estimate separates implementation and hosting. Confirm capacity-tier assumptions, the cost of extra migration cycles, the boundary of included support, and service-credit remedies in the final contract.",
    ],
    "Orbit Digital": [
        "The platform description is broad; a design workshop should produce a system-by-system interface map, named API owners, data-flow diagrams, error handling, and a migration sequence before the build is committed.",
        "Request a phase-based staffing plan, written acceptance criteria, a dependency register, a sample rollback runbook, and the exact evidence available from the security review.",
        "The indicative implementation price excludes some migration and premium-support options. Ask for renewal uplifts, usage limits, data-export fees, and a fully priced support schedule for the expected service period.",
    ],
    "CedarPeak Solutions": [
        "The hybrid design depends on buyer identity and network decisions. Validate data-flow boundaries, API throttling, key ownership, restore objectives, and the support split between customer and supplier.",
        "The migration plan should include signed field mappings, data-quality thresholds, two mock runs, count reconciliation, rollback evidence, and clear buyer responsibilities for cleansing source records.",
        "Standard support is limited to business hours. Compare the separate after-hours price, contract renewal assumptions, migration overage rates, incident-notification commitment, and certification evidence.",
    ],
    "Harborlight Systems": [
        "The regional rollout should confirm residency requirements, traffic profiles, recovery targets, network connectivity, localization needs, and dependencies for each business unit before the pilot begins.",
        "For each rollout wave, require go/no-go sign-off, reconciled migration totals, user training records, tested rollback steps, availability monitoring, and evidence that backups can be restored.",
        "The recurring subscription is higher than several alternatives. Validate user and storage bands, regional add-on fees, renewal increases, premium analytics costs, exit assistance, and data-export terms.",
    ],
}


def create_sample_proposals(output_dir: Path | str) -> list[dict[str, Any]]:
    """Create six fictional, detailed supplier proposal PDFs locally using ReportLab."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
    from reportlab.lib import colors

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ProposalTitle", parent=styles["Title"], textColor=colors.HexColor("#17406a")))
    profiles = []
    for supplier in SAMPLE_SUPPLIERS:
        safe_name = supplier["name"].lower().replace(" ", "_")
        path = output / f"{safe_name}_proposal.pdf"
        story = [
            Paragraph("Fictional Supplier Proposal", styles["ProposalTitle"]),
            Paragraph(f"Procurement platform implementation · {supplier['name']}", styles["Heading2"]),
            Paragraph("This synthetic document is created solely for the Agentic RFP Evaluation classroom project. All suppliers, people, prices, and claims are fictional.", styles["BodyText"]),
            Spacer(1, 0.25 * inch), Paragraph("1. Executive Summary", styles["Heading1"]),
            Paragraph(supplier["profile"], styles["BodyText"]),
            Paragraph("2. Proposed Solution and Technical Capability", styles["Heading1"]),
            Paragraph(supplier["architecture"], styles["BodyText"]), PageBreak(),
            Paragraph("3. Implementation Plan", styles["Heading1"]),
            Paragraph(supplier["plan"], styles["BodyText"]),
            Paragraph("Illustrative milestones", styles["Heading2"]),
            Table([["Milestone", "Target"], ["Discovery and design", "Weeks 1–4"], ["Build and integration", "Weeks 5–14"], ["Acceptance and handover", "Final phase"]], colWidths=[2.8 * inch, 2.2 * inch]),
            Spacer(1, 0.2 * inch), Paragraph("4. Commercial Value", styles["Heading1"]),
            Paragraph(supplier["price"], styles["BodyText"]), PageBreak(),
            Paragraph("5. Security, Compliance, and Risk Controls", styles["Heading1"]),
            Paragraph(supplier["security"], styles["BodyText"]),
            Paragraph("6. Support Model and Experience", styles["Heading1"]),
            Paragraph(supplier["support"], styles["BodyText"]),
            PageBreak(),
            Paragraph("7. Due Diligence Notes and Assumptions", styles["Heading1"]),
            Paragraph("The following questions are illustrative review prompts. They are not verified supplier claims and should be resolved with documentary evidence during procurement.", styles["BodyText"]),
            *[Paragraph(note, styles["BodyText"]) for note in SAMPLE_APPENDICES[supplier["name"]]],
            Paragraph("End of fictional proposal", styles["Italic"]),
        ]
        doc = SimpleDocTemplate(str(path), pagesize=letter, rightMargin=0.7*inch, leftMargin=0.7*inch, topMargin=0.7*inch, bottomMargin=0.7*inch)
        doc.build(story)
        profiles.append({**supplier, "path": path})
    return profiles
