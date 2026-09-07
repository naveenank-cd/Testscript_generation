"""
Real browser-based E2E verification of Application Testing UI using Playwright.
Tests live crawling, immediate cancellation, full authenticated crawl,
state synchronization without refresh, exact project name propagation,
modular POM project generation, and backend restart isolation.

pytest-discoverable async test.
"""

import asyncio
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

import pytest
from playwright.async_api import async_playwright

PROJECT_NAME = "saucedemo_pom_e2e"
TARGET_URL = "https://www.saucedemo.com"
FRONTEND_URL = "http://localhost:3000/test-case-generation/automation"
BACKEND_URL = "http://127.0.0.1:8006"


def get_real_completed_workflow():
    """
    Retrieves an existing real completed workflow from backend artifacts.
    Does NOT seed or fake a pre-completed workflow file.
    """
    repo_root = Path(__file__).resolve().parents[2]
    workflows_dir = repo_root / "backend" / "artifacts" / "automation" / "workflows"
    if not workflows_dir.exists():
        workflows_dir = repo_root / "artifacts" / "automation" / "workflows"

    # Prioritize existing completed SauceDemo workflow if available
    known_sauce_id = "7f5e440f-fb87-454c-83ba-9da0331bd149"
    known_file = workflows_dir / f"{known_sauce_id}.json"
    if known_file.is_file():
        try:
            data = json.loads(known_file.read_text(encoding="utf-8"))
            if data.get("status") == "completed" and data.get("test_cases"):
                return data
        except Exception:
            pass

    # Fallback to any completed workflow with test cases
    for wf_file in workflows_dir.glob("*.json"):
        try:
            data = json.loads(wf_file.read_text(encoding="utf-8"))
            if data.get("status") == "completed" and data.get("test_cases"):
                return data
        except Exception:
            continue

    raise RuntimeError(
        f"No real completed workflow found in {workflows_dir}. "
        "A valid completed workflow must exist in the backend."
    )


@pytest.mark.asyncio
async def test_e2e_real_browser_flow():
    """
    Executes the clean end-to-end browser flow in the Application Testing UI:
    project name -> target URL/credentials -> crawl -> live status ->
    Stop Crawling -> fresh crawl -> completed -> Generate Scripts -> modular POM displayed.
    """
    print("=" * 75)
    print("STARTING REAL BROWSER E2E VERIFICATION OF APPLICATION TESTING UI")
    print("=" * 75)

    # 1. Retrieve real completed workflow (no seeding/faking)
    workflow_state = get_real_completed_workflow()
    workflow_id = str(workflow_state["workflow_id"])
    print(f"[PRE-CHECK] Using existing completed workflow: {workflow_id}")

    # 2. Retrieve credentials via environment variables
    username = os.environ.get("SAUCEDEMO_USERNAME") or os.environ.get("SAUCEDEMO_USER") or "standard_user"
    password = os.environ.get("SAUCEDEMO_PASSWORD") or "secret_sauce"
    print(f"[PRE-CHECK] Retrieved credentials for target URL (user: {username})")

    repo_root = Path(__file__).resolve().parents[2]
    screenshots_dir = repo_root / "artifacts" / "automation" / "e2e_screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    # 3. Pre-check servers are up
    try:
        health_res = urllib.request.urlopen(f"{BACKEND_URL}/health", timeout=5)
        pre_gen_health = health_res.read().decode()
        print(f"[PRE-CHECK] Backend /health returned {health_res.status} OK: {pre_gen_health}")
    except Exception as e:
        pytest.fail(f"Backend is not accessible at {BACKEND_URL}: {e}")

    try:
        fe_res = urllib.request.urlopen("http://localhost:3000", timeout=5)
        print(f"[PRE-CHECK] Frontend root returned {fe_res.status} OK")
    except Exception as e:
        pytest.fail(f"Frontend is not accessible at http://localhost:3000: {e}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        # Step 1: Initialize session with active workflow pointer (no faked localStorage state)
        print("\n[Step 1] Initializing browser session with active workflow and navigating to Application Testing UI...")
        await page.add_init_script(f"""
            sessionStorage.setItem('testcase-active-workflow', JSON.stringify({{
                workflowId: '{workflow_id}'
            }}));
        """)

        await page.goto(FRONTEND_URL)
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path=str(screenshots_dir / "01_initial_automation_page.png"))
        print("  -> Navigation successful. Initial UI screenshot captured.")

        # Step 2: Fill Project Name
        print("\n[Step 2] Entering project name...")
        proj_name_input = page.locator("#project-name")
        await proj_name_input.wait_for(state="visible", timeout=15000)
        await proj_name_input.fill("")
        await proj_name_input.fill(PROJECT_NAME)
        curr_proj_val = await proj_name_input.input_value()
        assert curr_proj_val == PROJECT_NAME, f"Expected {PROJECT_NAME}, got {curr_proj_val}"
        print(f"  -> Step 2 Passed: Project Name set to '{curr_proj_val}'")

        # Step 3: Fill Target Application URL & Credentials from env vars
        print("\n[Step 3] Entering target application URL and credentials...")
        url_input = page.locator("#application-url")
        await url_input.fill(TARGET_URL)

        auth_select = page.locator("#auth-mode-select")
        await auth_select.select_option("credentials")

        email_input = page.locator("#playwright-email")
        await email_input.wait_for(state="visible", timeout=5000)
        await email_input.fill(username)

        pass_input = page.locator("#playwright-password")
        await pass_input.fill(password)
        await page.screenshot(path=str(screenshots_dir / "02_form_filled.png"))
        print(f"  -> Step 3 Passed: Target URL={TARGET_URL}, Auth Mode=credentials, Username={username}")

        # Step 4: Verify Generate Scripts is initially disabled
        print("\n[Step 4] Verifying 'Generate Test Scripts' is initially disabled...")
        generate_btn = page.locator("button:has-text('Generate Test Scripts')")
        is_disabled = await generate_btn.is_disabled()
        assert is_disabled, "Generate Test Scripts must be disabled before a valid crawl completes"
        print("  -> Step 4 Passed: Quality gate verified (Generate button disabled).")

        # Step 5: Start Crawl and test Stop Crawling
        print("\n[Step 5] Initiating crawl and testing Stop Crawling...")
        crawl_btn = page.locator("button:has-text('Crawl Application')")
        await crawl_btn.click()

        stop_btn = page.locator("button:has-text('Stop Crawling')")
        await stop_btn.wait_for(state="visible", timeout=15000)
        print("  -> Crawl started successfully. 'Stop Crawling' is visible without refresh.")
        await page.screenshot(path=str(screenshots_dir / "03_crawl_running.png"))

        # Click Stop Crawling
        await stop_btn.click()
        print("  -> Clicked 'Stop Crawling'. Monitoring transition to stopped state...")
        await page.wait_for_selector("button:has-text('Crawl Application')", timeout=45000)
        await page.screenshot(path=str(screenshots_dir / "04_crawl_stopped.png"))
        print("  -> Step 5 Passed: Crawl stopped cleanly without page refresh.")

        # Step 6: Fresh Crawl to completion
        print("\n[Step 6] Starting fresh authenticated crawl to completion...")
        fresh_crawl_btn = page.locator("button:has-text('Crawl Application')")
        await fresh_crawl_btn.click()
        print("  -> Fresh authenticated crawl initiated. Monitoring live status updates...")

        # Monitor live progress without refresh until completed and Generate Test Scripts is enabled
        crawl_completed = False
        for attempt in range(90):
            await page.wait_for_timeout(1000)
            if await generate_btn.is_enabled():
                print(f"  -> Fresh crawl completed! Generate Scripts enabled (elapsed ~{attempt+1}s)")
                crawl_completed = True
                break

        assert crawl_completed, "Crawl did not complete within the expected time limit"
        await page.screenshot(path=str(screenshots_dir / "05_crawl_completed.png"))
        print("  -> Step 6 Passed: Fresh crawl completed and verified enabled.")

        # Step 7: Verify live status & crawl evidence displayed
        print("\n[Step 7] Verifying live status & crawl evidence...")
        body_text = await page.inner_text("body")
        assert (
            "pages scanned" in body_text.lower()
            or "swag labs" in body_text.lower()
            or "elements" in body_text.lower()
        ), "Expected crawl discovery details to be visible in the UI"
        print("  -> Step 7 Passed: Crawl evidence and status verified in UI.")

        # Step 8: Generate automation scripts
        print("\n[Step 8] Generating automation project scripts...")
        assert await generate_btn.is_enabled(), "Generate Test Scripts button must be enabled"
        await generate_btn.click()
        print("  -> Clicked 'Generate Test Scripts'. Waiting for generation...")

        # Wait for Modular POM Project viewer to appear in the UI
        await page.wait_for_selector("text=Modular POM Project", timeout=45000)
        await page.wait_for_timeout(2000)
        await page.screenshot(path=str(screenshots_dir / "06_modular_pom_generated.png"))
        print("  -> Step 8 Passed: Modular POM Project generated and displayed without refresh.")

        # Step 9: Verify exact user-entered project name in UI
        print("\n[Step 9] Verifying exact user-entered project name in UI...")
        ui_project_badge = page.locator(f"span:has-text('{PROJECT_NAME}')").first
        await ui_project_badge.wait_for(state="visible", timeout=10000)
        badge_text = await ui_project_badge.text_content()
        assert PROJECT_NAME in badge_text, f"Expected {PROJECT_NAME} in UI badge, got {badge_text}"
        print(f"  -> Step 9 Passed: UI displays exact project name badge: '{badge_text.strip()}'")

        # Step 10: Inspect Modular POM File Tree in UI without refresh
        print("\n[Step 10] Inspecting Modular POM File Tree in UI...")
        modular_tab = page.locator("button:has-text('Modular POM Project')").first
        await modular_tab.click()

        file_items = page.locator("aside").filter(has_text="Project Files").locator("button")
        file_count = await file_items.count()
        assert file_count > 0, "Expected files listed in Modular POM project view"
        print(f"  -> Total modular project files listed in UI: {file_count}")

        displayed_filenames = []
        for idx in range(min(file_count, 5)):
            file_btn = file_items.nth(idx)
            name = (await file_btn.text_content() or "").strip()
            displayed_filenames.append(name)
            await file_btn.click()
            await page.wait_for_timeout(300)
        print(f"  -> Inspected sample files in UI: {displayed_filenames}")

        # Step 11: Verify backend development server did NOT restart
        print("\n[Step 11] Verifying backend development server did NOT restart...")
        post_gen_health = urllib.request.urlopen(f"{BACKEND_URL}/health", timeout=5).read().decode()
        assert post_gen_health == pre_gen_health, "Backend health response unexpectedly changed"
        print(f"  -> Backend health verified unchanged: {post_gen_health}")

        # Step 12: Verify generated project on disk
        print(f"\n[Step 12] Verifying generated project on disk under generated_automation/{PROJECT_NAME}/...")
        project_dir = repo_root / "generated_automation" / PROJECT_NAME
        if not project_dir.exists():
            project_dir = repo_root / "backend" / "generated_automation" / PROJECT_NAME
        assert project_dir.is_dir(), f"Expected directory does not exist: {project_dir}"

        # Verify modular POM directory structure
        modules_dir = project_dir / "modules"
        shared_dir = project_dir / "shared"
        assert modules_dir.is_dir(), f"Missing modules directory: {modules_dir}"
        assert shared_dir.is_dir(), f"Missing shared directory: {shared_dir}"

        submodules = [d for d in modules_dir.iterdir() if d.is_dir() and not d.name.startswith("__")]
        assert len(submodules) > 0, "Expected at least one domain module in modules/"

        pom_pages_found = 0
        pom_tests_found = 0
        for mod in submodules:
            pages_dir = mod / "pages"
            tests_dir = mod / "tests"
            assert pages_dir.is_dir(), f"Missing pages directory in module {mod.name}"
            assert tests_dir.is_dir(), f"Missing tests directory in module {mod.name}"

            page_files = list(pages_dir.glob("*.py"))
            test_files = list(tests_dir.glob("test_*.py"))
            pom_pages_found += len(page_files)
            pom_tests_found += len(test_files)
            print(f"     Module '{mod.name}': {len(page_files)} Page Objects, {len(test_files)} Tests")

        assert pom_pages_found > 0, "Expected real Page Object files under modules/<module>/pages/"
        assert pom_tests_found > 0, "Expected real test files under modules/<module>/tests/"

        # Verify shared components
        assert (shared_dir / "fixtures" / "conftest.py").is_file(), "Missing shared/fixtures/conftest.py"
        assert (shared_dir / "config" / "settings.py").is_file(), "Missing shared/config/settings.py"
        assert (shared_dir / "test_data" / "data_loader.py").is_file(), "Missing shared/test_data/data_loader.py"
        assert (shared_dir / "test_data" / "test_data.json").is_file(), "Missing shared/test_data/test_data.json"
        assert (shared_dir / "utils" / "helpers.py").is_file(), "Missing shared/utils/helpers.py"

        # Verify project root files
        assert (project_dir / "requirements.txt").is_file(), "Missing requirements.txt"
        assert (project_dir / "pytest.ini").is_file(), "Missing pytest.ini"
        assert (project_dir / "pyproject.toml").is_file(), "Missing pyproject.toml"
        assert (project_dir / "README.md").is_file(), "Missing README.md"

        # Verify test-case mapping & Playwright locators
        all_test_code = "\n".join(f.read_text(encoding="utf-8") for f in modules_dir.glob("**/tests/test_*.py"))
        all_page_code = "\n".join(f.read_text(encoding="utf-8") for f in modules_dir.glob("**/pages/*.py"))

        for tc in workflow_state.get("test_cases", [])[:2]:
            tc_id = str(tc["test_case_id"])
            assert tc_id in all_test_code, f"TestCase ID {tc_id} not mapped in generated tests"
            print(f"     [OK] TestCase {tc_id} mapped in test suite.")

        assert "locator(" in all_page_code or "get_by_" in all_page_code, (
            "Page Objects must contain real Playwright locators"
        )
        print("  -> Step 12 Passed: Complete modular POM architecture verified on disk.")

        await browser.close()
        print("\n" + "=" * 75)
        print("ALL E2E REAL BROWSER VERIFICATION CHECKS PASSED SUCCESSFULLY!")
        print("=" * 75)
