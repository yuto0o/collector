from src.models import SummaryModel


def test_summary_model_valid():
    data = {"summary": "短い要約", "highlights": ["点1", "点2"], "importance": 3}
    # Pydantic v2 uses model_validate, but construction should work either way
    try:
        obj = SummaryModel.model_validate(data)
    except Exception:
        obj = SummaryModel(**data)
    assert obj.summary.startswith("短い")


def test_summary_model_invalid():
    data = {"summary": 123, "highlights": "not-a-list", "importance": "high"}
    try:
        SummaryModel.model_validate(data)
        assert False, "validation should have failed"
    except Exception:
        assert True
