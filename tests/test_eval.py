# tests/test_eval.py
# Evaluation harness using pytest and MLflow

import sys
import os

# Add src directory to PYTHONPATH so pytest can find your agent module
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

import pytest
import mlflow
from agent import run_agent  # adjust import to your agent entry-point


# Configure MLflow tracking
@pytest.fixture(scope="session", autouse=True)
def setup_mlflow():
    from pathlib import Path

    # Ensure the mlruns directory exists
    mlruns_dir = Path(__file__).resolve().parent.parent / "mlruns"
    mlruns_dir.mkdir(parents=True, exist_ok=True)
    # Use file:// URI for tracking
    tracking_uri = mlruns_dir.as_uri()
    mlflow.set_tracking_uri(tracking_uri)
    # Initialize or retrieve experiment
    try:
        mlflow.set_experiment("agent-evaluations")
    except TypeError:
        client = mlflow.tracking.MlflowClient()
        if client.get_experiment_by_name("agent-evaluations") is None:
            client.create_experiment(
                "agent-evaluations", artifact_location=tracking_uri
            )
        mlflow.set_experiment("agent-evaluations")
    yield


def eval_prompt(prompt: str, expected_tool: str, expected_args: dict = None):
    """
    Send a prompt to the agent, log to MLflow, and assert expected behavior.
    """
    with mlflow.start_run(run_name=prompt[:50]):
        # Log prompt and expectations
        mlflow.log_param("prompt", prompt)
        mlflow.log_param("expected_tool", expected_tool)

        # Execute agent
        output = run_agent(prompt)

        # Check tool selection
        actual_tool = output.get("tool")
        mlflow.log_param("actual_tool", actual_tool)
        tool_match = 1 if actual_tool == expected_tool else 0
        mlflow.log_metric("tool_match", tool_match)
        assert (
            actual_tool == expected_tool
        ), f"Tool mismatch: {actual_tool} != {expected_tool}"

        # If args expected, verify
        if expected_args is not None:
            actual_args = output.get("args", {})
            mlflow.log_param("actual_args", actual_args)
            arg_match = 1 if actual_args == expected_args else 0
            mlflow.log_metric("arg_match", arg_match)
            assert (
                actual_args == expected_args
            ), f"Args mismatch: {actual_args} != {expected_args}"


# === Example test cases ===


def test_booking_flow():
    # Agent currently replies via SendWhatsappMsg for booking prompts
    prompt = "Book a flight from New York to London on July 1"
    expected_tool = "SendWhatsappMsg"
    # No specific args check; we just want to ensure the agent attempts to reach out
    eval_prompt(prompt, expected_tool)


def test_status_query():
    prompt = "What's the status of my booking?"
    # Agent uses CheckBookingTool to fetch booking status
    expected_tool = "CheckBookingTool"
    eval_prompt(prompt, expected_tool)
