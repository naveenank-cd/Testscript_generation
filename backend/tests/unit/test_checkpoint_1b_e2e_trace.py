"""
End-to-End Data Flow Verification Test for Checkpoint 1B:
REAL CRAWL
→ SAVED APPLICATION KNOWLEDGE
→ USER STORY + AC
→ SCENARIO
→ TEST CASE
→ UI STEP MAPPING
→ VERIFIED LOCATOR
→ PLAYWRIGHT / MODULAR POM SCRIPT
"""

import pytest
from app.services.application_knowledge_service import (
    extract_relevant_application_knowledge,
    map_test_case_steps_to_crawl_evidence,
)
from app.services.project_structure_generator import ProjectStructureGenerator
from app.services.automation_service import _python_source


@pytest.mark.asyncio
async def test_complete_e2e_saucedemo_trace():
    print("\n--- 1. REAL DISCOVERED APPLICATION CRAWL KNOWLEDGE ---")
    crawl_knowledge = {
        "crawl_id": "saucedemo-crawl-real-001",
        "application_url": "https://www.saucedemo.com/",
        "page_title": "Swag Labs",
        "application_map": {
            "pages": [
                {"url": "https://www.saucedemo.com/", "title": "Swag Labs Login"},
                {"url": "https://www.saucedemo.com/inventory.html", "title": "Swag Labs Inventory"},
                {"url": "https://www.saucedemo.com/cart.html", "title": "Swag Labs Cart"},
            ],
            "relationships": [
                {"from": "https://www.saucedemo.com/", "to": "https://www.saucedemo.com/inventory.html", "action": "submit login"},
                {"from": "https://www.saucedemo.com/inventory.html", "to": "https://www.saucedemo.com/cart.html", "action": "shopping cart link"},
            ],
        },
        "discovered_elements": [
            # Login Page
            {"page_url": "https://www.saucedemo.com/", "name": "user-name", "tag": "input", "test_id": "username"},
            {"page_url": "https://www.saucedemo.com/", "name": "password", "tag": "input", "test_id": "password"},
            {"page_url": "https://www.saucedemo.com/", "name": "Login", "tag": "button", "locator": "[data-testid='login-button']", "test_id": "login-button"},
            # Inventory Page
            {"page_url": "https://www.saucedemo.com/inventory.html", "name": "Add to cart", "tag": "button", "locator": "[data-testid='add-to-cart-sauce-labs-backpack']", "test_id": "add-to-cart-sauce-labs-backpack"},
            {"page_url": "https://www.saucedemo.com/inventory.html", "name": "Shopping Cart", "tag": "a", "locator": "#shopping_cart_container"},
            # Cart Page
            {"page_url": "https://www.saucedemo.com/cart.html", "name": "Checkout", "tag": "button", "locator": "[data-testid='checkout']", "test_id": "checkout"},
        ],
    }

    print("\n--- 2. USER STORY + ACCEPTANCE CRITERIA ---")
    user_stories = [
        {
            "id": "US-PURCHASE",
            "text": "As a standard user I want to purchase the Sauce Labs Backpack and proceed to checkout",
        }
    ]
    acceptance_criteria = [
        {"id": "AC-1", "text": "Authenticate on login page"},
        {"id": "AC-2", "text": "Add backpack to cart from inventory"},
        {"id": "AC-3", "text": "Verify Checkout button on cart page is clickable"},
    ]

    print("\n--- 3. PATH-AWARE APPLICATION KNOWLEDGE EXTRACTION ---")
    app_knowledge = extract_relevant_application_knowledge(
        user_stories, acceptance_criteria, crawl_knowledge
    )
    assert app_knowledge is not None

    extracted_urls = [p["url"] for p in app_knowledge["pages"]]
    print(f"Extracted Pages (in navigation path order): {extracted_urls}")

    # Preserved Path: / -> /inventory.html -> /cart.html
    assert extracted_urls == [
        "https://www.saucedemo.com/",
        "https://www.saucedemo.com/inventory.html",
        "https://www.saucedemo.com/cart.html",
    ]

    # Preserved navigation flows
    flows = app_knowledge["navigation_flows"]
    assert len(flows) == 2
    assert flows[0]["from"] == "https://www.saucedemo.com/"
    assert flows[0]["to"] == "https://www.saucedemo.com/inventory.html"
    assert flows[1]["from"] == "https://www.saucedemo.com/inventory.html"
    assert flows[1]["to"] == "https://www.saucedemo.com/cart.html"

    print("\n--- 4. SCENARIO AND TEST CASE GENERATION ---")
    scenario = {
        "scenario_id": "SC-PURCHASE-001",
        "title": "End to end backpack checkout flow",
    }
    test_case = {
        "test_case_id": "TC-SAUCE-001",
        "scenario_id": "SC-PURCHASE-001",
        "title": "Purchase Sauce Labs Backpack Checkout",
        "steps": [
            {"step_number": 1, "action": "Navigate to base application", "expected_result": "Login page is displayed"},
            {"step_number": 2, "action": "Enter username 'standard_user'", "expected_result": "Username entered"},
            {"step_number": 3, "action": "Enter password 'secret_sauce'", "expected_result": "Password entered"},
            {"step_number": 4, "action": "Click 'Login' button", "expected_result": "Navigated to inventory page"},
            {"step_number": 5, "action": "Click 'Add to cart' button for backpack", "expected_result": "Item added to cart"},
            {"step_number": 6, "action": "Click 'Checkout' button on cart page", "expected_result": "Checkout page displayed"},
        ],
    }

    print("\n--- 5. DETERMINISTIC UI STEP -> CRAWL EVIDENCE MAPPING ---")
    mapped_cases = map_test_case_steps_to_crawl_evidence([test_case], app_knowledge)
    tc = mapped_cases[0]

    assert tc["evidence_status"] == "verified"
    steps = tc["steps"]

    # Step 1: Base navigation
    assert steps[0]["target_page"] == "https://www.saucedemo.com/"
    assert steps[0]["target_locator"] == 'page.goto("https://www.saucedemo.com/")'
    assert steps[0]["evidence_status"] == "verified"

    # Step 2: Username
    assert steps[1]["target_page"] == "https://www.saucedemo.com/"
    assert steps[1]["target_element"] == "user-name"
    assert steps[1]["target_locator"] == '[data-testid="username"]'
    assert steps[1]["evidence_status"] == "verified"

    # Step 3: Password
    assert steps[2]["target_page"] == "https://www.saucedemo.com/"
    assert steps[2]["target_element"] == "password"
    assert steps[2]["target_locator"] == '[data-testid="password"]'
    assert steps[2]["evidence_status"] == "verified"

    # Step 4: Login button
    assert steps[3]["target_page"] == "https://www.saucedemo.com/"
    assert steps[3]["target_element"] == "Login"
    assert steps[3]["target_locator"] == "[data-testid='login-button']"
    assert steps[3]["evidence_status"] == "verified"

    # Step 5: Add to cart
    assert steps[4]["target_page"] == "https://www.saucedemo.com/inventory.html"
    assert steps[4]["target_element"] == "Add to cart"
    assert steps[4]["target_locator"] == "[data-testid='add-to-cart-sauce-labs-backpack']"
    assert steps[4]["evidence_status"] == "verified"

    # Step 6: Checkout
    assert steps[5]["target_page"] == "https://www.saucedemo.com/cart.html"
    assert steps[5]["target_element"] == "Checkout"
    assert steps[5]["target_locator"] == "[data-testid='checkout']"
    assert steps[5]["evidence_status"] == "verified"

    # Verify ui_mapping breakdown
    assert len(tc["ui_mapping"]) == 6
    print(f"Verified UI Mapping Breakdown: {len(tc['ui_mapping'])} steps mapped with 0 missing locators.")

    print("\n--- 6. SCRIPT GENERATION CONSUMPTION ---")
    script_source = _python_source(tc, "https://www.saucedemo.com/", crawl_knowledge["discovered_elements"])
    assert "def stable_locator(self, instruction: str, step: dict | None = None):" in script_source
    assert "app.perform(step[\"action\"], step=step)" in script_source
    assert "[data-testid='login-button']" in script_source
    assert "[data-testid='add-to-cart-sauce-labs-backpack']" in script_source
    assert "[data-testid='checkout']" in script_source

    print("\n--- 7. MODULAR POM PROJECT GENERATION ---")
    gen = ProjectStructureGenerator(app_name="saucedemo_pom")
    modular_proj = gen.generate_project(
        base_url="https://www.saucedemo.com/",
        discovered_elements=crawl_knowledge["discovered_elements"],
        page_inventory=crawl_knowledge["application_map"]["pages"],
        test_cases=[tc],
        scenarios=[scenario],
        credentials={"identifier": "standard_user", "password": "secret_sauce"},
    )

    file_paths = [f.relative_path for f in modular_proj.files]

    # Verify Page Objects created for all 3 pages
    assert any("pages/home_page.py" in p for p in file_paths)
    assert any("pages/inventory_page.py" in p for p in file_paths)
    assert any("pages/cart_page.py" in p for p in file_paths)

    # Verify Test Case placement:
    # Deepest verified action is on Cart Page (https://www.saucedemo.com/cart.html -> module 'cart')
    # Must be placed in modules/cart/tests/test_tc_sauce_001.py, NOT arbitrarily in modules/core/
    assert "modules/cart/tests/test_tc_sauce_001.py" in file_paths

    test_file_obj = next(f for f in modular_proj.files if "test_tc_sauce_001.py" in f.relative_path)
    test_code = test_file_obj.content

    # Verify POM test code uses the verified locators and cross-page POM classes
    assert 'data-testid="username"' in test_code
    assert 'data-testid="password"' in test_code
    assert "data-testid='login-button'" in test_code or 'data-testid="login-button"' in test_code
    assert "data-testid='add-to-cart-sauce-labs-backpack'" in test_code or 'data-testid="add-to-cart-sauce-labs-backpack"' in test_code
    assert "data-testid='checkout'" in test_code or 'data-testid="checkout"' in test_code
    assert "cart_page" in test_code
    assert "inventory_page" in test_code
    assert "home_page" in test_code

    print("=" * 75)
    print("E2E TRACE SUCCESSFUL: REAL CRAWL -> SCRIPT & MODULAR POM FULLY VERIFIED")
    print("=" * 75)
