import pytest

from evaluation import calculate_scores, normalize_evaluation, parse_json_response


@pytest.fixture
def criteria():
    return [
        {"criterion_id": 1, "name": "Technical", "description": "Tech fit", "weight": 60.0, "max_score": 10.0, "is_active": 1},
        {"criterion_id": 2, "name": "Support", "description": "Support", "weight": 40.0, "max_score": 10.0, "is_active": 1},
    ]


def test_normalization_fills_missing_and_clips_scores(criteria):
    normalized, warnings = normalize_evaluation(
        {"criteria": [{"criterion_id": 1, "score": 14, "evidence": "page 2"}]},
        criteria,
        "Supplier A",
    )
    assert normalized["criteria"][0]["score"] == 10
    assert normalized["criteria"][1]["score"] == 0
    assert normalized["criteria"][0]["evidence"] == "page 2"
    assert any("clipped" in warning for warning in warnings)
    assert any("missing" in warning for warning in warnings)


def test_ranking_is_deterministic_and_tie_breaks_by_date_then_name(criteria):
    evaluations = [
        {"supplier_name": "Zulu", "submission_date": "2026-05-02", "experience_rating": 5, "criteria": [{"criterion_id": 1, "score": 8}, {"criterion_id": 2, "score": 8}]},
        {"supplier_name": "Alpha", "submission_date": "2026-05-01", "experience_rating": 1, "criteria": [{"criterion_id": 1, "score": 8}, {"criterion_id": 2, "score": 8}]},
        {"supplier_name": "Beta", "submission_date": "2026-05-01", "experience_rating": 4, "criteria": [{"criterion_id": 1, "score": 8}, {"criterion_id": 2, "score": 8}]},
    ]
    ranked, _ = calculate_scores(evaluations, criteria)
    assert [row["supplier_name"] for row in ranked] == ["Beta", "Alpha", "Zulu"]
    assert [row["final_rank"] for row in ranked] == [1, 2, 3]
    assert ranked[0]["absolute_score"] == 80
    assert ranked[0]["ppi"] == 100


def test_zero_benchmark_is_safe(criteria):
    evaluations = [{"supplier_name": "No evidence", "criteria": [{"criterion_id": 1, "score": 0}, {"criterion_id": 2, "score": 0}]}]
    ranked, warnings = calculate_scores(evaluations, criteria)
    assert ranked[0]["ppi"] == 0
    assert all(item["relative_performance"] == 0 for item in ranked[0]["criteria"])
    assert len(warnings) == 2


def test_active_weights_must_total_one_hundred(criteria):
    criteria[0]["weight"] = 50
    with pytest.raises(ValueError, match="100%"):
        calculate_scores([], criteria)


def test_parse_json_with_fence():
    assert parse_json_response('```json\n{"ok": true}\n```') == {"ok": True}
