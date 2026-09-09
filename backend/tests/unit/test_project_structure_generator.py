"""
Unit Tests for Modular Page Object Model (POM) Project Structure Generator.
"""

import pytest
from app.services.project_structure_generator import (
    ProjectStructureGenerator,
    sanitize_identifier,
    sanitize_class_name,
    determine_module_name,
    determine_page_name,
)


def test_sanitize_and_naming_helpers():
    assert sanitize_identifier("Sauce Labs Backpack") == "sauce_labs_backpack"
    assert sanitize_identifier("123-invalid-start") == "item_123_invalid_start"
    assert sanitize_identifier("") == "item"
    assert sanitize_class_name("login_page") == "LoginPage"
    assert sanitize_class_name("inventory") == "Inventory"
    assert determine_module_name("https://example.com/checkout/step-one.html") == "checkout"
    assert determine_page_name("https://example.com/inventory.html") == "inventory"
    assert determine_page_name("https://example.com/") == "home"


def test_modular_pom_project_generation():
    generator = ProjectStructureGenerator(app_name="swag_labs")

    discovered_elements = [
        # Login Page Elements
        {
            "tag": "input",
            "name": "user-name",
            "label": "Username",
            "input_type": "text",
            "page_url": "https://www.saucedemo.com/",
            "element_id": "user-name",
            "test_id": "username",
        },
        {
            "tag": "input",
            "name": "password",
            "label": "Password",
            "input_type": "password",
            "page_url": "https://www.saucedemo.com/",
            "element_id": "password",
            "test_id": "password",
        },
        {
            "tag": "button",
            "name": "Login",
            "role": "button",
            "page_url": "https://www.saucedemo.com/",
            "element_id": "login-button",
            "test_id": "login-button",
        },
        # Inventory Page Elements
        {
            "tag": "button",
            "name": "Add to cart",
            "role": "button",
            "page_url": "https://www.saucedemo.com/inventory.html",
            "element_id": "add-to-cart-sauce-labs-backpack",
            "test_id": "add-to-cart-sauce-labs-backpack",
        },
        {
            "tag": "a",
            "name": "Shopping Cart",
            "page_url": "https://www.saucedemo.com/inventory.html",
            "element_id": "shopping_cart_container",
        },
    ]

    page_inventory = [
        {"url": "https://www.saucedemo.com/", "title": "Swag Labs Login"},
        {"url": "https://www.saucedemo.com/inventory.html", "title": "Swag Labs Inventory"},
    ]

    test_cases = [
        {
            "test_case_id": "TC_001",
            "scenario_id": "SC_001",
            "title": "Successful login and add product to cart",
            "steps": [
                {"step_number": 1, "action": "Enter username and password on login page", "expected_result": "Credentials filled"},
                {"step_number": 2, "action": "Click login button", "expected_result": "Navigated to inventory"},
                {"step_number": 3, "action": "Click Add to cart for Sauce Labs Backpack", "expected_result": "Item added to cart"},
            ],
        },
    ]

    scenarios = [
        {"scenario_id": "SC_001", "title": "End to end purchase flow"},
    ]

    project = generator.generate_project(
        base_url="https://www.saucedemo.com/",
        discovered_elements=discovered_elements,
        page_inventory=page_inventory,
        test_cases=test_cases,
        scenarios=scenarios,
        credentials={"identifier": "standard_user", "password": "secret_sauce"},
    )

    assert project.project_name == "swag_labs"
    assert len(project.files) > 0

    file_paths = [f.relative_path for f in project.files]

    # Shared framework files
    assert "shared/config/settings.py" in file_paths
    assert "shared/fixtures/conftest.py" in file_paths
    assert "shared/utils/helpers.py" in file_paths
    assert "shared/test_data/data_loader.py" in file_paths
    assert "shared/test_data/test_data.json" in file_paths
    assert "shared/assets/.gitkeep" in file_paths
    assert "screenshots/.gitkeep" in file_paths
    assert "traces/.gitkeep" in file_paths
    assert "reports/.gitkeep" in file_paths
    assert "requirements.txt" in file_paths
    assert ".env.example" in file_paths
    assert "pytest.ini" in file_paths
    assert "pyproject.toml" in file_paths
    assert "README.md" in file_paths

    # Page Objects
    assert any("pages" in p and "page.py" in p for p in file_paths)

    # Test Suites
    assert any("tests" in p and "test_" in p for p in file_paths)

    # Verify conftest contains Playwright fixtures
    conftest_file = next(f for f in project.files if f.relative_path == "shared/fixtures/conftest.py")
    assert "sync_playwright" in conftest_file.content
    assert "def browser" in conftest_file.content
    assert "def page" in conftest_file.content

    # Verify Page Object has resilient locators and methods
    page_obj_file = next(f for f in project.files if "page.py" in f.relative_path and "modules" in f.relative_path)
    assert "class " in page_obj_file.content
    assert "def navigate" in page_obj_file.content
    assert "def assert_loaded" in page_obj_file.content


def test_cross_page_pom_test_generation():
    generator = ProjectStructureGenerator(app_name="e_commerce")

    discovered_elements = [
        {"tag": "input", "name": "user-name", "element_id": "user-name", "page_url": "https://example.com/login"},
        {"tag": "button", "name": "Login", "element_id": "login-btn", "page_url": "https://example.com/login"},
        {"tag": "button", "name": "Add to cart", "element_id": "add-btn", "page_url": "https://example.com/catalog"},
    ]

    test_cases = [
        {
            "test_case_id": "TC_E2E_01",
            "scenario_id": "SC_E2E_01",
            "title": "Login and add to cart flow",
            "steps": [
                {"step_number": 1, "action": "Enter username credentials", "expected_result": "Username entered"},
                {"step_number": 2, "action": "Add to cart product", "expected_result": "Product added"},
            ],
        }
    ]

    project = generator.generate_project(
        base_url="https://example.com/login",
        discovered_elements=discovered_elements,
        page_inventory=[
            {"url": "https://example.com/login", "title": "Login Page"},
            {"url": "https://example.com/catalog", "title": "Catalog Page"},
        ],
        test_cases=test_cases,
    )

    test_file = next(f for f in project.files if "test_tc_e2e_01.py" in f.relative_path)
    assert "@pytest.mark.regression" in test_file.content
    assert "def test_login_and_add_to_cart_flow" in test_file.content


def test_pom_never_assigned_to_first_page_arbitrarily():
    """Verify test cases without verified target pages are never assigned to pages_meta[0]."""
    generator = ProjectStructureGenerator(app_name="crm_app")

    discovered_elements = [
        {"tag": "input", "name": "email", "element_id": "email", "page_url": "https://crm.test/login"},
        {"tag": "button", "name": "Submit", "element_id": "submit-lead", "page_url": "https://crm.test/leads"},
    ]

    test_cases = [
        {
            "test_case_id": "TC_UNSUPPORTED_01",
            "scenario_id": "SC_001",
            "title": "Quantum AI Lead Routing",
            "evidence_status": "unsupported_missing_evidence",
            "unsupported_evidence_reasons": ["No crawl-verified controls exist for Quantum routing"],
            "steps": [
                {"step_number": 1, "action": "Trigger quantum routing algorithm", "expected_result": "Algorithm completes", "evidence_status": "unsupported_missing_evidence"},
            ],
        }
    ]

    project = generator.generate_project(
        base_url="https://crm.test/login",
        discovered_elements=discovered_elements,
        page_inventory=[
            {"url": "https://crm.test/login", "title": "Login"},
            {"url": "https://crm.test/leads", "title": "Leads"},
        ],
        test_cases=test_cases,
    )

    # Must NOT be assigned to modules/login/tests/ (pages_meta[0])
    test_paths = [f.relative_path for f in project.files if "test_tc_unsupported_01.py" in f.relative_path]
    assert len(test_paths) == 1
    assert "modules/unsupported/tests/test_tc_unsupported_01.py" in test_paths
    assert "modules/login/tests/test_tc_unsupported_01.py" not in test_paths

    unsupported_file = next(f for f in project.files if "test_tc_unsupported_01.py" in f.relative_path)
    assert "@pytest.mark.skip" in unsupported_file.content
    assert "UNSUPPORTED / MISSING EVIDENCE" in unsupported_file.content


def test_pom_module_selected_using_verified_target_page():
    """Verify test case is placed in correct module based on step target_page, even when title lacks keywords."""
    generator = ProjectStructureGenerator(app_name="store_app")

    discovered_elements = [
        {"tag": "input", "name": "user", "element_id": "user", "page_url": "https://store.test/login"},
        {"tag": "button", "name": "Pay", "element_id": "btn-pay", "page_url": "https://store.test/checkout"},
    ]

    test_cases = [
        {
            "test_case_id": "TC_PAY_01",
            "scenario_id": "SC_PAY",
            "title": "Execute final transaction",  # Does NOT contain the word 'checkout' or 'login'
            "steps": [
                {
                    "step_number": 1,
                    "action": "Click 'Pay' button",
                    "expected_result": "Payment confirmed",
                    "target_page": "https://store.test/checkout",
                    "target_element": "Pay",
                    "target_locator": "#btn-pay",
                    "evidence_status": "verified",
                }
            ],
        }
    ]

    project = generator.generate_project(
        base_url="https://store.test/login",
        discovered_elements=discovered_elements,
        page_inventory=[
            {"url": "https://store.test/login", "title": "Login Page"},
            {"url": "https://store.test/checkout", "title": "Checkout Page"},
        ],
        test_cases=test_cases,
    )

    test_paths = [f.relative_path for f in project.files if "test_tc_pay_01.py" in f.relative_path]
    assert len(test_paths) == 1
    # Must be placed under modules/checkout/tests/ because step target_page is /checkout
    assert "modules/checkout/tests/test_tc_pay_01.py" in test_paths
    assert "modules/login/tests/test_tc_pay_01.py" not in test_paths

    test_file = next(f for f in project.files if "test_tc_pay_01.py" in f.relative_path)
    assert "#btn-pay" in test_file.content
    assert "checkout_page" in test_file.content


def test_script_generation_consumes_verified_mapping():
    """Verify _python_source generates code that consumes verified step mapping."""
    from app.services.automation_service import _python_source

    test_case = {
        "test_case_id": "TC_MAP_99",
        "title": "Add backpack using verified locator",
        "steps": [
            {
                "step_number": 1,
                "action": "Click 'Add to cart' button",
                "expected_result": "Backpack in cart",
                "target_page": "https://www.saucedemo.com/inventory.html",
                "target_element": "Add to cart",
                "target_locator": "[data-testid='add-to-cart-sauce-labs-backpack']",
                "evidence_status": "verified",
            }
        ],
    }

    code = _python_source(test_case, "https://www.saucedemo.com/", discovered_elements=[])
    assert "def stable_locator(self, instruction: str, step: dict | None = None):" in code
    assert "app.perform(step[\"action\"], step=step)" in code
    assert "[data-testid='add-to-cart-sauce-labs-backpack']" in code

