from documents import SAMPLE_SUPPLIERS, create_sample_proposals, extract_pdf_text


def test_sample_proposals_are_detailed_and_extractable(tmp_path):
    proposals = create_sample_proposals(tmp_path)

    assert len(SAMPLE_SUPPLIERS) == 6
    assert len(proposals) == 6
    for proposal in proposals:
        text = extract_pdf_text(proposal["path"])
        assert "Fictional Supplier Proposal" in text
        assert "Due Diligence Notes and Assumptions" in text
        assert len(text) > 2400
