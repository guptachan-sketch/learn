"""Generate four fictional 3-page supplier proposal PDFs in sample_proposals/."""
from pathlib import Path

from documents import create_sample_proposals


if __name__ == "__main__":
    root = Path(__file__).parent / "sample_proposals"
    proposals = create_sample_proposals(root)
    for proposal in proposals:
        print(f"Created {proposal['path']}")
