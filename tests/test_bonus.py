"""Regression checks for the custom ontology; original grading tests are unchanged."""
from src.graph import canonical_substance, penalty_frame


def test_chemical_names_merge_case_but_not_different_substances():
    assert canonical_substance(" ketamine ") == canonical_substance("Ketamine") == "Ketamine"
    assert canonical_substance("methamphetamine") == "Methamphetamine"
    assert canonical_substance("MDMA") != canonical_substance("Methamphetamine")
    assert canonical_substance("ma túy") == "ma túy"  # no guessed specific chemical


def test_penalty_excludes_numbers_from_conditions_and_supplemental_sanctions():
    clause = {"id": "article clause", "penalty": "phạt tù từ 02 năm đến 07 năm",
              "text": "100 gam, 18 tuổi, 500 triệu đồng"}
    assert penalty_frame(clause)["max_years"] == 7
    clause["penalty"] = "phạt tiền 500 triệu đồng, cấm hành nghề 05 năm"
    assert penalty_frame(clause) is None


def test_unbounded_penalties_are_separate_from_finite_years():
    frame = penalty_frame({"id": "a4", "penalty": "phạt tù 20 năm, tù chung thân hoặc tử hình"})
    assert frame["max_years"] == 20 and frame["life"] and frame["death"]
    frame = penalty_frame({"id": "a1", "penalty": "phạt tù chung thân"})
    assert frame["max_years"] is None and frame["life"] and not frame["death"]
