import pytest
from pydantic import ValidationError

from operator_demo.runtime import create_demo_runtime


def test_registry_exposes_demo_operators_with_json_schemas():
    runtime = create_demo_runtime()

    specs = runtime.registry.list()
    names = {(spec.name, spec.version) for spec in specs}

    assert names == {
        ("data_access", "1.0.0"),
        ("clean", "1.0.0"),
        ("quality_eval", "1.0.0"),
    }

    clean_spec = runtime.registry.get("clean", "1.0.0")
    assert "dataset" in clean_spec.input_schema["properties"]
    assert "cleaned_dataset" in clean_spec.output_schema["properties"]


def test_executor_validates_operator_input_before_running():
    runtime = create_demo_runtime()

    with pytest.raises(ValidationError):
        runtime.executor.execute(
            name="clean",
            version="1.0.0",
            payload={"rules": ["deduplicate"]},
            ctx=runtime.context(source="api"),
        )


def test_default_workflow_reads_cleans_and_scores_sample_dataset():
    runtime = create_demo_runtime()

    result = runtime.run_default_workflow(source="scheduler")

    assert result.status == "success"
    assert [step.operator for step in result.steps] == [
        "data_access",
        "clean",
        "quality_eval",
    ]

    access_output = result.outputs["access_users"]
    clean_output = result.outputs["clean_users"]
    quality_output = result.outputs["score_users"]

    assert access_output["rows_loaded"] == 6
    assert clean_output["removed_rows"] == 2
    assert clean_output["changed_rows"] == 3
    assert quality_output["passed"] is True
    assert quality_output["metrics"]["duplicate_rate"] == 0
    assert quality_output["score"] >= 0.8
    assert len(result.lineage) == 3
