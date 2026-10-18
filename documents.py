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
]


def create_sample_proposals(output_dir: Path | str) -> list[dict[str, Any]]:
    """Create four fictional, multi-page supplier PDFs locally using ReportLab."""
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
            Paragraph("End of fictional proposal", styles["Italic"]),
        ]
        doc = SimpleDocTemplate(str(path), pagesize=letter, rightMargin=0.7*inch, leftMargin=0.7*inch, topMargin=0.7*inch, bottomMargin=0.7*inch)
        doc.build(story)
        profiles.append({**supplier, "path": path})
    return profiles
