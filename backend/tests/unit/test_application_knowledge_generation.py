import uuid
from unittest.mock import AsyncMock, patch
import pytest

from app.models.project import Project
from app.services.project_service import ProjectService
from app.services.application_knowledge_service import (
    extract_relevant_application_knowledge,
    map_test_case_steps_to_crawl_evidence,
)
from app.agents.context_preparation_agent import ContextPreparationAgent
from app.agents.base_agent import ExecutionContext
from app.schemas.context_schema import StructuredContext
from app.schemas.scenario_schema import Scenario
from app.schemas.testcase_schema import TestCase, TestStep


@pytest.mark.asyncio
async def test_extract_relevant_application_knowledge_filters_focused_context():
    """Verify application knowledge extraction is focused, deterministic, and avoids raw dumping."""
    user_stories = [
        {"id": "US-1", "text": "As an admin I want to manage caregiver appointments and auto renew schedules"}
    ]
    acceptance_criteria = [
        {"id": "AC-1", "text": "Navigate to appointments and verify Auto Renew button is enabled"}
    ]
    crawl_knowledge = {
        "crawl_id": "crawl-123",
        "application_url": "https://caregiver.app.internal",
        "page_title": "Caregiver Portal",
        "application_map": {
            "pages": [
                {"url": "https://caregiver.app.internal/dashboard", "title": "Dashboard"},
                {"url": "https://caregiver.app.internal/appointments", "title": "Appointments Overview"},
                {"url": "https://caregiver.app.internal/unrelated-billing", "title": "Billing Settings"},
            ],
            "relationships": [
                {"from": "https://caregiver.app.internal/dashboard", "to": "https://caregiver.app.internal/appointments", "action": "click 'Appointments'"},
            ],
        },
        "discovered_elements": [
            {
                "page_url": "https://caregiver.app.internal/appointments",
                "role": "button",
                "name": "Auto Renew",
                "locator": "button:has-text('Auto Renew')",
                "test_id": "btn-auto-renew",
            },
            {
                "page_url": "https://caregiver.app.internal/unrelated-billing",
                "role": "button",
                "name": "Export Invoices",
                "locator": "button#export-invoices",
            },
        ],
    }

    result = extract_relevant_application_knowledge(user_stories, acceptance_criteria, crawl_knowledge)

    assert result is not None
    assert result["application_url"] == "https://caregiver.app.internal"
    assert result["crawl_id"] == "crawl-123"

    # Appointments page must be prioritized due to keyword matching
    page_urls = [p["url"] for p in result["pages"]]
    assert "https://caregiver.app.internal/appointments" in page_urls

    # Discovered elements should include the Auto Renew button with verified locator
    appt_page = next(p for p in result["pages"] if "appointments" in p["url"])
    element_names = [e["name"] for e in appt_page["elements"]]
    assert "Auto Renew" in element_names
    auto_renew_el = next(e for e in appt_page["elements"] if e["name"] == "Auto Renew")
    assert auto_renew_el["locator"] == "button:has-text('Auto Renew')"

    # Navigation flow connecting Dashboard -> Appointments must be captured
    assert len(result["navigation_flows"]) >= 1
    assert result["navigation_flows"][0]["to"] == "https://caregiver.app.internal/appointments"


@pytest.mark.asyncio
async def test_context_preparation_agent_attaches_application_knowledge():
    """Verify ContextPreparationAgent injects application_knowledge into StructuredContext."""
    agent = ContextPreparationAgent()
    project_id = uuid.uuid4()
    crawl_knowledge = {
        "crawl_id": "crawl-xyz",
        "application_url": "https://test.app",
        "page_title": "Test Portal",
        "application_map": {
            "pages": [{"url": "https://test.app/login", "title": "Login"}],
        },
        "discovered_elements": [
            {"page_url": "https://test.app/login", "role": "button", "name": "Sign In", "locator": "button#signin"}
        ],
    }
    input_data = {
        "project_id": project_id,
        "input_payload": {
            "user_stories": ["As a user I want to sign in to my account"],
            "acceptance_criteria": ["Sign in button is clickable"],
        },
        "crawl_knowledge": crawl_knowledge,
    }
    exec_ctx = ExecutionContext(request_id="req-1", workflow_id="wf-1", metadata={"mock_mode": True})

    structured_ctx = await agent.run(input_data, exec_ctx)
    assert isinstance(structured_ctx, StructuredContext)
    assert structured_ctx.application_knowledge is not None
    assert structured_ctx.application_knowledge["application_url"] == "https://test.app"
    assert len(structured_ctx.application_knowledge["pages"]) >= 1


@pytest.mark.asyncio
async def test_scenario_unsupported_evidence_reasons():
    """Verify Scenario schema tracks unsupported_evidence_reasons without breaking valid fields."""
    project_id = uuid.uuid4()
    scenario = Scenario(
        project_id=project_id,
        title="Valid Appointment Renewal",
        description="Verify appointment renewal schedule",
        scenario_type="positive",
        expected_business_outcome="Renewal is saved",
        unsupported_evidence_reasons=["UI button 'Quick Reschedule' was not found in crawl knowledge"],
    )
    assert scenario.unsupported_evidence_reasons == ["UI button 'Quick Reschedule' was not found in crawl knowledge"]
    assert scenario.title == "Valid Appointment Renewal"


@pytest.mark.asyncio
async def test_testcase_ui_mapping_and_unsupported_evidence_status():
    """Verify TestCase and TestStep support evidence_status and ui_mapping."""
    project_id = uuid.uuid4()
    scenario_id = uuid.uuid4()

    step1 = TestStep(
        step_number=1,
        action="Navigate to Appointments overview page",
        expected_result="Appointments list is displayed",
        evidence_status="verified",
        target_page="https://caregiver.app.internal/appointments",
    )
    step2 = TestStep(
        step_number=2,
        action="Click 'Auto Renew' button",
        expected_result="Schedule is updated",
        evidence_status="verified",
        target_element="Auto Renew",
        target_locator="button:has-text('Auto Renew')",
    )
    test_case = TestCase(
        project_id=project_id,
        scenario_id=scenario_id,
        title="Caregiver appointment auto-renew",
        description="Ensure auto renew works as expected",
        steps=[step1, step2],
        evidence_status="verified",
        ui_mapping=[
            {"step_number": 2, "target": "Auto Renew", "locator": "button:has-text('Auto Renew')"}
        ],
    )
    assert test_case.evidence_status == "verified"
    assert len(test_case.steps) == 2
    assert test_case.steps[1].target_locator == "button:has-text('Auto Renew')"


@pytest.mark.asyncio
async def test_project_supports_multiple_requirement_generations():
    """Verify One Project supports multiple requirement generations and get_generations returns them."""
    session = AsyncMock()
    service = ProjectService(session)
    project_id = uuid.uuid4()

    mock_project = Project(
        id=project_id,
        name="Multi-Gen Health Care Portal",
        application_url="https://health.app.org",
        is_active=True,
    )
    service.get = AsyncMock(return_value=mock_project)

    # Mock workflow_service returning two independent generations
    wf1_id = uuid.uuid4()
    wf2_id = uuid.uuid4()
    mock_workflows = [
        {
            "workflow_id": wf2_id,
            "project_id": project_id,
            "status": "completed",
            "current_stage": "completed",
            "started_at": "2026-09-09T10:00:00Z",
            "completed_at": "2026-09-09T10:05:00Z",
            "input_payload": {
                "user_stories": [{"id": "US-2", "text": "Generation 2 Story"}],
                "acceptance_criteria": [{"id": "AC-2", "text": "Gen 2 AC"}],
            },
            "scenarios": [{"title": "Gen 2 Scenario"}],
            "test_cases": [{"title": "Gen 2 Test Case"}],
        },
        {
            "workflow_id": wf1_id,
            "project_id": project_id,
            "status": "completed",
            "current_stage": "completed",
            "started_at": "2026-09-09T09:00:00Z",
            "completed_at": "2026-09-09T09:05:00Z",
            "input_payload": {
                "user_stories": [{"id": "US-1", "text": "Generation 1 Story"}],
                "acceptance_criteria": [{"id": "AC-1", "text": "Gen 1 AC"}],
            },
            "scenarios": [{"title": "Gen 1 Scenario"}],
            "test_cases": [{"title": "Gen 1 Test Case"}],
        },
    ]

    with patch("app.services.workflow_service.workflow_service.get_workflows_for_project", return_value=mock_workflows):
        generations = await service.get_generations(project_id)

        assert len(generations) == 2
        # Generation 2 (newest)
        assert generations[0]["workflow_id"] == str(wf2_id)
        assert generations[0]["user_story_count"] == 1
        assert generations[0]["test_case_count"] == 1
        assert generations[0]["user_stories"][0]["text"] == "Generation 2 Story"

        # Generation 1 (prior generation preserved intact)
        assert generations[1]["workflow_id"] == str(wf1_id)
        assert generations[1]["user_story_count"] == 1
        assert generations[1]["test_case_count"] == 1
        assert generations[1]["user_stories"][0]["text"] == "Generation 1 Story"


@pytest.mark.asyncio
async def test_re_crawl_updates_knowledge_without_altering_prior_generations():
    """Verify re-crawling saves new crawl knowledge on Project without touching existing generations."""
    session = AsyncMock()
    service = ProjectService(session)
    project_id = uuid.uuid4()

    initial_crawl = {"crawl_id": "crawl-v1", "pages_crawled": 2}
    updated_crawl = {"crawl_id": "crawl-v2", "pages_crawled": 5}

    project = Project(
        id=project_id,
        name="My Project",
        application_url="https://app.test",
        is_active=True,
        latest_crawl_id="crawl-v1",
        crawl_knowledge=initial_crawl,
    )
    service.get = AsyncMock(return_value=project)

    # Perform re-crawl save
    await service.save_crawl_knowledge(
        entity_id=project_id,
        crawl_knowledge=updated_crawl,
        latest_crawl_id="crawl-v2",
    )

    assert project.latest_crawl_id == "crawl-v2"
    assert project.crawl_knowledge["pages_crawled"] == 5
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_requirement_targeting_deep_page_includes_prerequisite_navigation_pages():
    """Verify requirement targeting deep page includes prerequisite root/login/intermediate pages in order."""
    user_stories = [
        {"id": "US-CART", "text": "As a shopper I want to view my cart and proceed to checkout"}
    ]
    acceptance_criteria = [
        {"id": "AC-CART", "text": "Verify Checkout button on cart page is clickable"}
    ]
    crawl_knowledge = {
        "crawl_id": "crawl-deep-path",
        "application_url": "https://www.saucedemo.com/",
        "page_title": "Swag Labs Login",
        "application_map": {
            "pages": [
                {"url": "https://www.saucedemo.com/", "title": "Swag Labs Login"},
                {"url": "https://www.saucedemo.com/inventory.html", "title": "Swag Labs Inventory"},
                {"url": "https://www.saucedemo.com/cart.html", "title": "Your Cart"},
            ],
            "relationships": [
                {"from": "https://www.saucedemo.com/", "to": "https://www.saucedemo.com/inventory.html", "action": "click login"},
                {"from": "https://www.saucedemo.com/inventory.html", "to": "https://www.saucedemo.com/cart.html", "action": "click cart"},
            ],
        },
        "discovered_elements": [
            {"page_url": "https://www.saucedemo.com/", "role": "button", "name": "Login", "locator": "input#login-button"},
            {"page_url": "https://www.saucedemo.com/inventory.html", "role": "button", "name": "Add to cart", "locator": "button#add-to-cart"},
            {"page_url": "https://www.saucedemo.com/cart.html", "role": "button", "name": "Checkout", "locator": "button#checkout", "test_id": "checkout"},
        ],
    }

    result = extract_relevant_application_knowledge(user_stories, acceptance_criteria, crawl_knowledge)

    assert result is not None
    page_urls = [p["url"] for p in result["pages"]]

    # Root page '/' must be included as prerequisite
    assert "https://www.saucedemo.com/" in page_urls
    # Intermediate page '/inventory.html' must be included as prerequisite
    assert "https://www.saucedemo.com/inventory.html" in page_urls
    # Target page '/cart.html' must be included
    assert "https://www.saucedemo.com/cart.html" in page_urls

    # Preserved sequence: Root first, intermediate second, target third
    assert page_urls.index("https://www.saucedemo.com/") < page_urls.index("https://www.saucedemo.com/inventory.html")
    assert page_urls.index("https://www.saucedemo.com/inventory.html") < page_urls.index("https://www.saucedemo.com/cart.html")

    # Navigation flow captures the step-by-step path
    flow_pairs = [(f["from"], f["to"]) for f in result["navigation_flows"]]
    assert ("https://www.saucedemo.com/", "https://www.saucedemo.com/inventory.html") in flow_pairs
    assert ("https://www.saucedemo.com/inventory.html", "https://www.saucedemo.com/cart.html") in flow_pairs


@pytest.mark.asyncio
async def test_navigation_path_follows_actual_discovered_relationships():
    """Verify only pages along the discovered relationship path are included, ignoring unrelated branches."""
    user_stories = [{"id": "US-RPT", "text": "View monthly analytics reports"}]
    acceptance_criteria = [{"id": "AC-RPT", "text": "Download report data table"}]

    crawl_knowledge = {
        "crawl_id": "crawl-branch",
        "application_url": "https://portal.test/home",
        "page_title": "Portal Home",
        "application_map": {
            "pages": [
                {"url": "https://portal.test/home", "title": "Portal Home"},
                {"url": "https://portal.test/analytics", "title": "Analytics Dashboard"},
                {"url": "https://portal.test/reports", "title": "Monthly Reports"},
                {"url": "https://portal.test/unrelated-billing", "title": "Billing Settings"},
            ],
            "relationships": [
                {"from": "https://portal.test/home", "to": "https://portal.test/analytics", "action": "nav analytics"},
                {"from": "https://portal.test/analytics", "to": "https://portal.test/reports", "action": "nav reports"},
                {"from": "https://portal.test/home", "to": "https://portal.test/unrelated-billing", "action": "nav billing"},
            ],
        },
        "discovered_elements": [
            {"page_url": "https://portal.test/reports", "name": "Download CSV", "locator": "button#dl-csv"},
            {"page_url": "https://portal.test/unrelated-billing", "name": "Payment Method", "locator": "input#card"},
        ],
    }

    result = extract_relevant_application_knowledge(user_stories, acceptance_criteria, crawl_knowledge)
    included_urls = [p["url"] for p in result["pages"]]

    assert "https://portal.test/home" in included_urls
    assert "https://portal.test/analytics" in included_urls
    assert "https://portal.test/reports" in included_urls
    # Unrelated billing branch must not be included
    assert "https://portal.test/unrelated-billing" not in included_urls


@pytest.mark.asyncio
async def test_deterministic_step_mapping_populates_verified_evidence():
    """Verify map_test_case_steps_to_crawl_evidence deterministically populates target_page, element, locator."""
    crawl_knowledge = {
        "application_url": "https://www.saucedemo.com/",
        "pages": [
            {
                "url": "https://www.saucedemo.com/",
                "elements": [
                    {"name": "user-name", "tag": "input", "test_id": "username"},
                    {"name": "Login", "tag": "button", "locator": "[data-testid='login-button']"},
                ],
            },
            {
                "url": "https://www.saucedemo.com/inventory.html",
                "elements": [
                    {"name": "Add to cart", "tag": "button", "locator": "[data-testid='add-to-cart-sauce-labs-backpack']"},
                ],
            },
        ],
    }

    test_case = {
        "test_case_id": "TC-E2E-01",
        "title": "Add backpack to cart",
        "steps": [
            {"step_number": 1, "action": "Navigate to base application", "expected_result": "Application opened"},
            {"step_number": 2, "action": "Enter username 'standard_user'", "expected_result": "Username entered"},
            {"step_number": 3, "action": "Click 'Login' button", "expected_result": "Logged in"},
            {"step_number": 4, "action": "Click 'Add to cart' button for backpack", "expected_result": "Product added to cart"},
        ],
    }

    mapped_cases = map_test_case_steps_to_crawl_evidence([test_case], crawl_knowledge)
    tc = mapped_cases[0]

    assert tc["evidence_status"] == "verified"
    steps = tc["steps"]

    # Step 1: navigation
    assert steps[0]["target_page"] == "https://www.saucedemo.com/"
    assert steps[0]["evidence_status"] == "verified"
    assert steps[0]["target_locator"] == 'page.goto("https://www.saucedemo.com/")'

    # Step 2: username field
    assert steps[1]["target_page"] == "https://www.saucedemo.com/"
    assert steps[1]["target_element"] == "user-name"
    assert steps[1]["target_locator"] == '[data-testid="username"]'
    assert steps[1]["evidence_status"] == "verified"

    # Step 3: login button
    assert steps[2]["target_page"] == "https://www.saucedemo.com/"
    assert steps[2]["target_element"] == "Login"
    assert steps[2]["target_locator"] == "[data-testid='login-button']"
    assert steps[2]["evidence_status"] == "verified"

    # Step 4: Add to cart on inventory page
    assert steps[3]["target_page"] == "https://www.saucedemo.com/inventory.html"
    assert steps[3]["target_element"] == "Add to cart"
    assert steps[3]["target_locator"] == "[data-testid='add-to-cart-sauce-labs-backpack']"
    assert steps[3]["evidence_status"] == "verified"

    # Verify ui_mapping list on test case
    assert len(tc["ui_mapping"]) == 4
    assert tc["ui_mapping"][3]["target_locator"] == "[data-testid='add-to-cart-sauce-labs-backpack']"


@pytest.mark.asyncio
async def test_unsupported_steps_marked_and_no_invented_locators():
    """Verify unsupported step receives unsupported_missing_evidence and does not invent selectors."""
    crawl_knowledge = {
        "application_url": "https://www.saucedemo.com/",
        "pages": [
            {
                "url": "https://www.saucedemo.com/",
                "elements": [
                    {"name": "Login", "tag": "button", "locator": "#login-button"},
                ],
            }
        ],
    }

    test_case = {
        "test_case_id": "TC-UNSUPPORTED",
        "title": "Biometric fingerprint login",
        "steps": [
            {"step_number": 1, "action": "Click nonexistent holographic fingerprint scanner", "expected_result": "Fingerprint accepted"},
        ],
    }

    mapped_cases = map_test_case_steps_to_crawl_evidence([test_case], crawl_knowledge)
    tc = mapped_cases[0]

    assert tc["evidence_status"] == "unsupported_missing_evidence"
    step = tc["steps"][0]
    assert step["evidence_status"] == "unsupported_missing_evidence"
    assert step["target_locator"] is None
    assert step["target_element"] is None
    assert len(tc["unsupported_evidence_reasons"]) >= 1
    assert "No discovered element in crawl evidence" in tc["unsupported_evidence_reasons"][0]

