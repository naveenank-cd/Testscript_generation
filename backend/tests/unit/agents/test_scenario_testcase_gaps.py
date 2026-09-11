import uuid
import pytest

from app.agents.base_agent import ExecutionContext
from app.agents.scenario_generation_agent import deduplicate_scenarios
from app.agents.testcase_generation_agent import deduplicate_test_cases, TestCaseGenerationAgent
from app.agents.testcase_validation_agent import TestCaseValidationAgent
from app.schemas.scenario_schema import Scenario, ScenarioBatch
from app.schemas.testcase_schema import TestCase, TestCaseBatch, TestStep


@pytest.mark.asyncio
async def test_multiple_test_cases_per_scenario_preserved():
    """Verify that multiple distinct test cases for the same scenario are NOT eliminated."""
    project_id = uuid.uuid4()
    scenario_id = uuid.uuid4()

    tc1 = TestCase(
        scenario_id=scenario_id,
        project_id=project_id,
        title="Valid Login with Standard Credentials",
        description="Verify user logs in with valid email and password",
        steps=[TestStep(step_number=1, action='Fill "Email" with "user@example.com"', expected_result="Email accepted"),
               TestStep(step_number=2, action='Fill "Password" with "Secret123"', expected_result="Password accepted"),
               TestStep(step_number=3, action='Click "Login"', expected_result="Dashboard displays successfully")],
    )
    tc2 = TestCase(
        scenario_id=scenario_id,
        project_id=project_id,
        title="Negative Login with Incorrect Password",
        description="Verify user receives error message on invalid password",
        steps=[TestStep(step_number=1, action='Fill "Email" with "user@example.com"', expected_result="Email accepted"),
               TestStep(step_number=2, action='Fill "Password" with "WrongPass"', expected_result="Password accepted"),
               TestStep(step_number=3, action='Click "Login"', expected_result="Error message 'Invalid credentials' is displayed")],
    )
    tc3 = TestCase(
        scenario_id=scenario_id,
        project_id=project_id,
        title="Boundary Login with Empty Email",
        description="Verify validation warning when email is left blank",
        steps=[TestStep(step_number=1, action='Fill "Email" with ""', expected_result="Email is blank"),
               TestStep(step_number=2, action='Click "Login"', expected_result="Field validation 'Email is required' is shown")],
    )

    deduped = deduplicate_test_cases([tc1, tc2, tc3])
    # All 3 test cases for the same scenario must be preserved
    assert len(deduped) == 3
    assert {tc.title for tc in deduped} == {
        "Valid Login with Standard Credentials",
        "Negative Login with Incorrect Password",
        "Boundary Login with Empty Email",
    }


@pytest.mark.asyncio
async def test_positive_and_negative_scenarios_not_deduplicated():
    """Verify positive and negative scenarios with similar titles are not merged."""
    project_id = uuid.uuid4()
    sc_pos = Scenario(
        project_id=project_id,
        title="User logs in with valid credentials",
        description="Verify that an existing user logs in with valid email and password",
        scenario_type="positive",
        expected_business_outcome="User dashboard is displayed",
        user_story_ids=["US-1"],
        requirement_ids=["REQ-1"],
    )
    sc_neg = Scenario(
        project_id=project_id,
        title="User logs in with invalid credentials",
        description="Verify that an existing user logs in with invalid email and password",
        scenario_type="negative",
        expected_business_outcome="Error alert is displayed",
        user_story_ids=["US-1"],
        requirement_ids=["REQ-1"],
    )

    deduped = deduplicate_scenarios([sc_pos, sc_neg])
    assert len(deduped) == 2
    types = {s.scenario_type for s in deduped}
    assert "positive" in types
    assert "negative" in types


@pytest.mark.asyncio
async def test_testcase_schema_preserves_user_story_and_feature_ids():
    """Verify TestCase schema includes user_story_ids and feature_ids."""
    tc = TestCase(
        title="Test Story Linkage",
        description="Verify user stories persist on test cases",
        user_story_ids=["US-10", "US-11"],
        feature_ids=["FEAT-5"],
        steps=[TestStep(step_number=1, action='Click "Submit"', expected_result="Form submitted successfully")],
    )
    assert tc.user_story_ids == ["US-10", "US-11"]
    assert tc.feature_ids == ["FEAT-5"]


@pytest.mark.asyncio
async def test_validation_passes_when_acceptance_criteria_absent():
    """Verify that test case validation does not artificially fail when no ACs are in context."""
    scenario_id = uuid.uuid4()
    project_id = uuid.uuid4()
    scenario = Scenario(
        scenario_id=scenario_id,
        project_id=project_id,
        title="Checkout cart items",
        description="Verify items in cart can be checked out",
        scenario_type="positive",
        expected_business_outcome="Order confirmation displayed",
        requirement_ids=["REQ-1"],
        user_story_ids=["US-1"],
        acceptance_criteria_ids=[],  # No ACs
    )
    tc = TestCase(
        scenario_id=scenario_id,
        project_id=project_id,
        title="Complete Checkout with standard shipping",
        description="Verify that cart checkout completes with standard shipping",
        requirement_ids=["REQ-1"],
        user_story_ids=["US-1"],
        steps=[
            TestStep(step_number=1, action='Navigate to "/cart" and review items', expected_result="Items listed with prices"),
            TestStep(step_number=2, action='Click "Proceed to Checkout" button', expected_result="Shipping details page loaded"),
            TestStep(step_number=3, action='Click "Place Order" button', expected_result="Order confirmation page displayed with order number"),
        ],
    )
    agent = TestCaseValidationAgent()
    result = await agent.execute(
        {
            "scenarios": {"scenarios": [scenario.model_dump(mode="json")]},
            "test_cases": {"test_cases": [tc.model_dump(mode="json")]},
            "confidence_threshold": 0.90,
        },
        ExecutionContext(request_id="test", workflow_id="test"),
    )
    assert result.confidence_score >= 0.90
    assert result.score_breakdown["acceptance_criteria_coverage"] == 1.0
    assert result.status.value == "passed"
