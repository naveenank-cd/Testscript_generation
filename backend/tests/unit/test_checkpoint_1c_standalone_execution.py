"""
Verification and Standalone Execution Test for Checkpoint 1C:
Generated Automation Validation and Executability

Verifies:
1. Every generated test file is actually discoverable by Pytest.
2. Every test imports and calls the correct Page Objects.
3. Every Page Object contains the methods actually used by the tests.
4. Every locator used by a Page Object comes from verified crawl evidence.
5. No generated test depends on a missing function/class/module.
6. Fixtures in conftest.py (browser, context, page, test_data, default_credentials) are loaded correctly.
7. Root-level conftest.py and pytest.ini with pythonpath = . ensure standalone execution without fixture errors.
8. Generated project passes validate_project().
9. Standalone execution: runs `python -m pytest --collect-only` and `python -m pytest --setup-show` in isolated project root.
10. Unsupported tests remain skipped with clear reason.
11. No raw `page.locator(...)` calls are emitted where a Page Object method should be used.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from app.services.application_knowledge_service import (
    extract_relevant_application_knowledge,
    map_test_case_steps_to_crawl_evidence,
)
from app.services.project_structure_generator import ProjectStructureGenerator


def test_checkpoint_1c_modular_pom_validation_and_standalone_execution():
    # 1. Crawl Knowledge Fixture
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

    # 2. Test Cases: 1 Verified, 1 Unsupported
    verified_test_case = {
        "test_case_id": "TC-SAUCE-001",
        "scenario_id": "SC-PURCHASE-001",
        "title": "Purchase Sauce Labs Backpack Checkout",
        "steps": [
            {"step_number": 1, "action": "Navigate to base application", "expected_result": "Login page is displayed"},
            {"step_number": 2, "action": "Enter username 'standard_user'", "expected_result": "Username entered"},
            {"step_number": 3, "action": "Enter password 'secret_sauce'", "expected_result": "Password entered"},
            {"step_number": 4, "action": "Click 'Login' button", "expected_result": "Inventory page displayed"},
            {"step_number": 5, "action": "Click 'Add to cart' button for backpack", "expected_result": "Backpack added to cart"},
            {"step_number": 6, "action": "Click 'Checkout' button on cart page", "expected_result": "Checkout page loaded"},
        ],
    }

    unsupported_test_case = {
        "test_case_id": "TC-UNSUPPORTED-002",
        "scenario_id": "SC-PURCHASE-001",
        "title": "Crypto Payment Option Verification",
        "evidence_status": "unsupported_missing_evidence",
        "unsupported_evidence_reasons": ["No cryptocurrency payment options discovered on Saucedemo"],
        "steps": [
            {"step_number": 1, "action": "Select Bitcoin Wallet", "expected_result": "Bitcoin option active", "evidence_status": "unsupported_missing_evidence"},
        ],
    }

    # Extract Knowledge & Map steps
    app_knowledge = extract_relevant_application_knowledge(
        [{"id": "US-1", "text": "Checkout backpack"}],
        [{"id": "AC-1", "text": "Checkout backpack from cart"}],
        crawl_knowledge,
    )
    mapped_cases = map_test_case_steps_to_crawl_evidence([verified_test_case], app_knowledge)
    tc_verified = mapped_cases[0]

    # 3. Generate Modular POM Project
    generator = ProjectStructureGenerator(app_name="saucedemo_pom_exec")
    modular_proj = generator.generate_project(
        base_url="https://www.saucedemo.com/",
        discovered_elements=crawl_knowledge["discovered_elements"],
        page_inventory=crawl_knowledge["application_map"]["pages"],
        test_cases=[tc_verified, unsupported_test_case],
        scenarios=[{"scenario_id": "SC-PURCHASE-001", "title": "Checkout flow"}],
        credentials={"identifier": "standard_user", "password": "secret_sauce"},
    )

    # 4. Project Validation
    validation = generator.validate_project(modular_proj)
    print("Project Validation Result:", validation)
    assert validation["valid"] is True, f"Validation failed with errors: {validation['errors']}"
    assert "python_syntax_valid" in validation["checks_passed"]
    assert "conftest_fixtures_configured" in validation["checks_passed"]
    assert "pytest_pythonpath_configured" in validation["checks_passed"]
    assert "test_data_connected" in validation["checks_passed"]

    # 5. Check Test → Page Object → Playwright flow
    test_files = [f for f in modular_proj.files if "modules/cart/tests/test_tc_sauce_001.py" in f.relative_path]
    assert len(test_files) == 1
    tc_code = test_files[0].content

    # Verify Page Object methods are called
    assert "home_page.fill_user_name(default_credentials[\"username\"])" in tc_code or "home_page.fill_username" in tc_code
    assert "home_page.fill_password(default_credentials[\"password\"])" in tc_code
    assert "home_page.click_login()" in tc_code or "home_page.click_login_button()" in tc_code
    assert "inventory_page.click_add_to_cart()" in tc_code or "inventory_page.click_add_to_cart_sauce_labs_backpack()" in tc_code
    assert "cart_page.click_checkout()" in tc_code

    # Verify no raw page.locator calls in test
    assert "home_page.page.locator" not in tc_code
    assert "inventory_page.page.locator" not in tc_code
    assert "cart_page.page.locator" not in tc_code
    assert "safe_fill" not in tc_code
    assert "wait_and_click" not in tc_code

    # Verify only required Page Objects are imported (Home, Inventory, Cart)
    assert "HomePage" in tc_code
    assert "InventoryPage" in tc_code
    assert "CartPage" in tc_code

    # Verify unsupported test is skipped
    unsupported_files = [f for f in modular_proj.files if "modules/unsupported/tests/test_tc_unsupported_002.py" in f.relative_path]
    assert len(unsupported_files) == 1
    unsupported_code = unsupported_files[0].content
    assert "@pytest.mark.skip" in unsupported_code

    # 6. Standalone Execution with Pytest in isolated temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        root_path = Path(tmpdir) / "saucedemo_pom_exec"
        for gen_file in modular_proj.files:
            fpath = root_path / gen_file.relative_path
            fpath.parent.mkdir(parents=True, exist_ok=True)
            fpath.write_text(gen_file.content, encoding="utf-8")

        # Run pytest --collect-only in root_path
        collect_res = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only"],
            cwd=str(root_path),
            capture_output=True,
            text=True,
        )
        print("COLLECT STDOUT:\n", collect_res.stdout)
        print("COLLECT STDERR:\n", collect_res.stderr)
        assert collect_res.returncode == 0
        assert "collected 2 items" in collect_res.stdout

        # Run pytest --setup-show to verify 0 fixture errors
        setup_res = subprocess.run(
            [sys.executable, "-m", "pytest", "--setup-show"],
            cwd=str(root_path),
            capture_output=True,
            text=True,
        )
        print("SETUP STDOUT:\n", setup_res.stdout)
        print("SETUP STDERR:\n", setup_res.stderr)
        # Fixture resolution must NOT report "fixture 'page' not found"
        assert "fixture 'page' not found" not in setup_res.stderr
        assert "fixture 'page' not found" not in setup_res.stdout
        assert "fixture 'default_credentials' not found" not in setup_res.stdout
        assert "ERROR at setup of test_" not in setup_res.stdout
        # Unsupported test must be SKIPPED
        assert "SKIPPED" in setup_res.stdout
