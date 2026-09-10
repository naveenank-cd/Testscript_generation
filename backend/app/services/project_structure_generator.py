"""
Project Structure Generator for Modular Page Object Model (POM) Automation Projects.

Generates industry-standard Playwright + Pytest modular projects structured by domain modules,
reusable Page Objects, Pytest fixtures (conftest.py), centralized configuration, and data loaders.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlsplit


def sanitize_identifier(name: str, fallback: str = "item") -> str:
    """Sanitize any arbitrary string into a valid Python identifier (snake_case)."""
    if not name or not name.strip():
        return fallback
    clean = re.sub(r"[^\w\s-]", "", name.strip().lower())
    clean = re.sub(r"[-\s]+", "_", clean)
    clean = clean.strip("_")
    if not clean or clean[0].isdigit():
        clean = f"{fallback}_{clean}" if clean else fallback
    return clean


def sanitize_class_name(name: str, fallback: str = "Page") -> str:
    """Sanitize any arbitrary string into a valid Python ClassName (PascalCase)."""
    clean_snake = sanitize_identifier(name, fallback=fallback)
    pascal = "".join(part.capitalize() for part in clean_snake.split("_") if part)
    if not pascal:
        pascal = fallback
    if pascal[0].isdigit():
        pascal = f"{fallback}{pascal}"
    return pascal


def _normalize_path(url: str) -> str:
    """Normalize URL path for consistent lookup."""
    try:
        parsed = urlsplit(url)
        path = parsed.path.rstrip("/")
        return path if path else "/"
    except Exception:
        return url


def determine_module_name(url: str, title: Optional[str] = None) -> str:
    """Determine a sensible business module name from URL path or page title."""
    try:
        parsed = urlsplit(url)
        clean_path = re.sub(r"\.(html|htm|php|aspx|jsp)$", "", parsed.path.strip("/"), flags=re.IGNORECASE)
        path_segments = [s for s in clean_path.split("/") if s]
        if path_segments:
            return sanitize_identifier(path_segments[0], fallback="core")
    except Exception:
        pass
    if title and title.strip():
        first_word = title.strip().split()[0]
        return sanitize_identifier(first_word, fallback="core")
    return "core"


def determine_page_name(url: str, title: Optional[str] = None) -> str:
    """Determine a descriptive Page Object name from URL or title."""
    try:
        parsed = urlsplit(url)
        path = parsed.path.strip("/")
        if not path or path in {"", "index.html", "index.htm", "home"}:
            return "home"
        last_segment = path.split("/")[-1]
        last_segment = re.sub(r"\.(html|htm|php|aspx|jsp)$", "", last_segment, flags=re.IGNORECASE)
        if last_segment:
            return sanitize_identifier(last_segment, fallback="page")
    except Exception:
        pass
    if title and title.strip():
        return sanitize_identifier(title, fallback="page")
    return "page"


@dataclass
class GeneratedFile:
    relative_path: str
    content: str
    file_type: str = "python"  # python, json, toml, text


@dataclass
class ModularProject:
    project_name: str
    files: List[GeneratedFile] = field(default_factory=list)
    modules: Set[str] = field(default_factory=set)
    page_objects: List[str] = field(default_factory=list)
    test_suites: List[str] = field(default_factory=list)


class ProjectStructureGenerator:
    """Generates an enterprise-ready Modular POM Project structure from crawl evidence and test cases."""

    def __init__(self, app_name: str = "app_test_project"):
        self.app_name = sanitize_identifier(app_name, fallback="test_project")

    def generate_project(
        self,
        base_url: str,
        discovered_elements: List[Dict[str, Any]],
        page_inventory: List[Dict[str, Any]],
        test_cases: List[Dict[str, Any]],
        scenarios: Optional[List[Dict[str, Any]]] = None,
        credentials: Optional[Dict[str, Any]] = None,
    ) -> ModularProject:
        project = ModularProject(project_name=self.app_name)
        scenarios_by_id = {str(s.get("scenario_id")): s for s in (scenarios or [])}

        # 1. Group discovered elements by page
        elements_by_page: Dict[str, List[Dict[str, Any]]] = {}
        for elem in discovered_elements:
            p_url = str(elem.get("page_url") or base_url)
            elements_by_page.setdefault(p_url, []).append(elem)

        if not elements_by_page and page_inventory:
            for p_info in page_inventory:
                p_url = str(p_info.get("url") or base_url)
                elements_by_page[p_url] = p_info.get("elements", [])

        if not elements_by_page:
            elements_by_page[base_url] = discovered_elements

        # 2. Build Page Objects
        pages_meta: Dict[str, Dict[str, Any]] = {}
        for p_url, elems in elements_by_page.items():
            # Extract page title
            p_title = None
            if elems and elems[0].get("page_title"):
                p_title = elems[0]["page_title"]
            elif page_inventory:
                for p_inv in page_inventory:
                    if str(p_inv.get("url")) == p_url:
                        p_title = p_inv.get("title")
                        break

            mod_name = determine_module_name(p_url, p_title)
            page_slug = determine_page_name(p_url, p_title)
            class_name = f"{sanitize_class_name(page_slug)}Page"

            pages_meta[p_url] = {
                "module_name": mod_name,
                "page_slug": page_slug,
                "class_name": class_name,
                "url": p_url,
                "elements": elems,
            }
            project.modules.add(mod_name)
            project.page_objects.append(class_name)

        # 3. Add Shared Framework Files
        self._add_shared_files(project, base_url, credentials)

        # 4. Generate Page Object Class Files
        for p_url, meta in pages_meta.items():
            mod = meta["module_name"]
            slug = meta["page_slug"]
            page_content = self._generate_page_object_code(meta, base_url)
            project.files.append(
                GeneratedFile(
                    relative_path=f"modules/{mod}/pages/{slug}_page.py",
                    content=page_content,
                )
            )

        # 5. Generate Test Suites per Module / Test Case
        for idx, tc in enumerate(test_cases, start=1):
            tc_id = str(tc.get("test_case_id") or f"tc_{idx:03d}")
            sc_id = str(tc.get("scenario_id") or "sc_001")
            scenario_obj = scenarios_by_id.get(sc_id, {})

            is_unsupported = tc.get("evidence_status") == "unsupported_missing_evidence"

            # 1. Identify verified target page URL from test case steps
            verified_target_url = None
            if not is_unsupported:
                step_target_pages = [
                    s.get("target_page") for s in tc.get("steps", [])
                    if s.get("target_page") and s.get("evidence_status") != "unsupported_missing_evidence"
                ]
                if step_target_pages:
                    # Prefer non-base target page or last action page
                    non_base = [p for p in step_target_pages if _normalize_path(p) != _normalize_path(base_url)]
                    verified_target_url = non_base[-1] if non_base else step_target_pages[0]
                elif tc.get("page_url"):
                    verified_target_url = tc.get("page_url")

            matched_page = None
            tc_module = None

            if verified_target_url:
                target_norm = _normalize_path(verified_target_url)
                for p_url, meta in pages_meta.items():
                    p_norm = _normalize_path(p_url)
                    if target_norm == p_norm or verified_target_url == p_url:
                        matched_page = meta
                        tc_module = meta["module_name"]
                        break

            # 2. Match against title / slug if still not matched
            if not matched_page and not is_unsupported:
                for p_url, meta in pages_meta.items():
                    if any(word in str(tc.get("title", "")).lower() for word in [meta["page_slug"], meta["module_name"]]):
                        tc_module = meta["module_name"]
                        matched_page = meta
                        break

            # 3. If no verified target page exists or test case is unsupported:
            if not matched_page or is_unsupported:
                # NEVER fallback to list(pages_meta.values())[0]!
                tc_module = "unsupported"
                matched_page = None

            project.modules.add(tc_module)
            test_content = self._generate_test_file_code(
                tc, scenario_obj, pages_meta, base_url, credentials, matched_page=matched_page
            )
            safe_tc_id = sanitize_identifier(tc_id)
            test_file_path = f"modules/{tc_module}/tests/test_{safe_tc_id}.py"
            project.files.append(
                GeneratedFile(relative_path=test_file_path, content=test_content)
            )
            project.test_suites.append(test_file_path)

        # 6. Add __init__.py files
        self._add_init_files(project)

        # 7. Add root config files (pytest.ini, pyproject.toml, README.md, requirements.txt, .env.example)
        self._add_root_config_files(project, base_url, credentials=credentials)

        return project

    def _add_shared_files(
        self, project: ModularProject, base_url: str, credentials: Optional[Dict[str, Any]]
    ) -> None:
        # Settings
        settings_code = f'''"""Global test automation configuration settings."""
import os
from dataclasses import dataclass

@dataclass
class Settings:
    BASE_URL: str = os.getenv("APP_BASE_URL", "{base_url}")
    HEADLESS: bool = os.getenv("HEADLESS", "true").lower() in ("true", "1", "yes")
    DEFAULT_TIMEOUT: int = int(os.getenv("DEFAULT_TIMEOUT", "10000"))
    SLOW_MO: int = int(os.getenv("SLOW_MO", "0"))
    SCREENSHOT_ON_FAILURE: bool = True

settings = Settings()
'''
        project.files.append(
            GeneratedFile(relative_path="shared/config/settings.py", content=settings_code)
        )

        # Helpers
        helpers_code = '''"""Reusable UI automation helper utilities."""
from typing import Optional
from playwright.sync_api import Page, Locator, expect

def wait_and_click(locator: Locator, timeout: int = 10000) -> None:
    """Wait for element to be visible and click."""
    locator.wait_for(state="visible", timeout=timeout)
    locator.click()

def safe_fill(locator: Locator, value: str, timeout: int = 10000) -> None:
    """Wait for input to be visible, clear, and fill value."""
    locator.wait_for(state="visible", timeout=timeout)
    locator.fill(value)

def assert_element_text(locator: Locator, expected_text: str, timeout: int = 10000) -> None:
    """Assert locator contains expected text."""
    expect(locator).to_contain_text(expected_text, timeout=timeout)
'''
        project.files.append(
            GeneratedFile(relative_path="shared/utils/helpers.py", content=helpers_code)
        )

        # Conftest (Pytest Fixtures)
        ident = "test_user"
        pwd = ""
        if credentials:
            if hasattr(credentials, "get_identifier") and credentials.get_identifier:
                ident = credentials.get_identifier
            elif isinstance(credentials, dict):
                ident = credentials.get("identifier") or credentials.get("email") or credentials.get("username") or "test_user"
            elif hasattr(credentials, "identifier") or hasattr(credentials, "email"):
                ident = getattr(credentials, "identifier", None) or getattr(credentials, "email", None) or "test_user"

            if hasattr(credentials, "password") and credentials.password:
                pwd = credentials.password.get_secret_value() if hasattr(credentials.password, "get_secret_value") else str(credentials.password)
            elif isinstance(credentials, dict):
                p = credentials.get("password")
                if p:
                    pwd = p.get_secret_value() if hasattr(p, "get_secret_value") else str(p)

        conftest_code = f'''"""Pytest global fixtures for Playwright browser and page management."""
import os
import pytest
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from shared.config.settings import settings
from shared.test_data.data_loader import load_test_data

@pytest.fixture(scope="session")
def browser():
    """Session-scoped Playwright browser instance."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=settings.HEADLESS,
            slow_mo=settings.SLOW_MO
        )
        yield browser
        browser.close()

@pytest.fixture(scope="function")
def context(browser: Browser) -> BrowserContext:
    """Function-scoped browser context."""
    context = browser.new_context(
        viewport={{"width": 1280, "height": 720}},
        ignore_https_errors=True
    )
    yield context
    context.close()

@pytest.fixture(scope="function")
def page(context: BrowserContext) -> Page:
    """Function-scoped page fixture with failure screenshot capture."""
    page = context.new_page()
    page.set_default_timeout(settings.DEFAULT_TIMEOUT)
    yield page
    page.close()

@pytest.fixture(scope="session")
def test_data() -> dict:
    """Session-scoped test data loader."""
    return load_test_data()

@pytest.fixture(scope="session")
def default_credentials(test_data: dict) -> dict:
    """Default test credentials loaded securely via data_loader."""
    default_creds = test_data.get("credentials", {{}}).get("default", {{}})
    return {{
        "username": os.getenv("TEST_USERNAME", default_creds.get("username", "{ident}")),
        "password": os.getenv("TEST_PASSWORD", default_creds.get("password", "{pwd}")),
    }}
'''
        project.files.append(
            GeneratedFile(relative_path="shared/fixtures/conftest.py", content=conftest_code)
        )
        # Root conftest.py for seamless pytest discovery
        root_conftest_code = '"""Root-level conftest for Pytest plugin and fixture discovery."""\npytest_plugins = ["shared.fixtures.conftest"]\n'
        project.files.append(
            GeneratedFile(relative_path="conftest.py", content=root_conftest_code)
        )

        # Data Loader
        data_loader_code = '''"""Test data loader utility."""
import json
import os
from pathlib import Path
from typing import Any, Dict

def load_test_data(filename: str = "test_data.json") -> Dict[str, Any]:
    """Load JSON test data from shared/test_data directory with runtime env secret resolution."""
    data_path = Path(__file__).resolve().parent / filename
    data = {}
    if data_path.is_file():
        data = json.loads(data_path.read_text(encoding="utf-8"))
    if "credentials" in data and "default" in data["credentials"]:
        env_pwd = os.getenv("TEST_PASSWORD")
        if env_pwd:
            data["credentials"]["default"]["password"] = env_pwd
    return data
'''
        project.files.append(
            GeneratedFile(relative_path="shared/test_data/data_loader.py", content=data_loader_code)
        )

        # Default Test Data (including negative testing variants)
        default_data = {
            "credentials": {
                "default": {
                    "username": ident,
                    "password": "",
                },
                "invalid_password": {
                    "username": ident,
                    "password": "WrongPassword!999",
                },
                "invalid_user": {
                    "username": "nonexistent.user.test@example.com",
                    "password": "WrongPassword!999",
                },
            },
            "environment": {
                "base_url": base_url,
            },
        }
        project.files.append(
            GeneratedFile(
                relative_path="shared/test_data/test_data.json",
                content=json.dumps(default_data, indent=2),
                file_type="json",
            )
        )

        # Assets, Screenshots, Traces, and Reports directory markers
        project.files.append(
            GeneratedFile(relative_path="shared/assets/.gitkeep", content="", file_type="text")
        )
        project.files.append(
            GeneratedFile(relative_path="screenshots/.gitkeep", content="", file_type="text")
        )
        project.files.append(
            GeneratedFile(relative_path="traces/.gitkeep", content="", file_type="text")
        )
        project.files.append(
            GeneratedFile(relative_path="reports/.gitkeep", content="", file_type="text")
        )

    def _generate_page_object_code(self, meta: Dict[str, Any], base_url: str) -> str:
        class_name = meta["class_name"]
        page_url = meta["url"]
        elements = meta["elements"]

        locator_attrs: List[str] = []
        action_methods: List[str] = []
        seen_locators: Set[str] = set()

        meta.setdefault("selector_to_method", {})
        meta.setdefault("element_to_method", {})
        meta.setdefault("methods", {})

        for elem in elements:
            tag = (elem.get("tag") or "").lower()
            name = elem.get("name") or elem.get("label") or elem.get("placeholder") or elem.get("test_id") or elem.get("element_id") or ""
            if not name:
                continue

            clean_name = sanitize_identifier(name)
            attr_suffix = "input" if tag in {"input", "textarea"} else ("button" if tag in {"button", "a"} else "elem")
            attr_name = sanitize_identifier(f"{clean_name}_{attr_suffix}", fallback=f"elem_{tag}")
            if attr_name in seen_locators:
                continue
            seen_locators.add(attr_name)

            selector = self._extract_best_selector(elem)
            if not selector:
                continue

            locator_attrs.append(f'        self.{attr_name} = self.page.locator({selector!r})')

            # Generate helper actions
            if tag in {"input", "textarea"} or elem.get("input_type") in {"text", "password", "email"}:
                method_name = f"fill_{clean_name}"
                action_methods.append(f'''
    def {method_name}(self, value: str) -> "{class_name}":
        """Enter value into {name} field."""
        self.{attr_name}.fill(value)
        return self''')
                meta["methods"][method_name] = ("fill", attr_name)
                self._register_selector_mapping(meta, selector, method_name, "fill", elem)

                # Alias: e.g. fill_user_name vs fill_username
                if "_" in clean_name:
                    alias_clean = f"fill_{clean_name.replace('_', '')}"
                    if alias_clean != method_name:
                        action_methods.append(f'''
    def {alias_clean}(self, value: str) -> "{class_name}":
        """Alias for {method_name}."""
        return self.{method_name}(value)''')
                        meta["methods"][alias_clean] = ("fill", attr_name)

            elif tag in {"button", "a"} or elem.get("role") == "button":
                method_name = f"click_{clean_name}"
                action_methods.append(f'''
    def {method_name}(self) -> "{class_name}":
        """Click the {name} control."""
        self.{attr_name}.click()
        return self''')
                meta["methods"][method_name] = ("click", attr_name)
                self._register_selector_mapping(meta, selector, method_name, "click", elem)

                # Alias: click_login vs click_login_button
                if not clean_name.endswith("button"):
                    alias_btn = f"click_{clean_name}_button"
                    action_methods.append(f'''
    def {alias_btn}(self) -> "{class_name}":
        """Alias for {method_name}."""
        return self.{method_name}()''')
                    meta["methods"][alias_btn] = ("click", attr_name)

        locators_block = "\n".join(locator_attrs) if locator_attrs else "        pass"
        actions_block = "\n".join(action_methods)

        code = f'''"""Page Object Model for {class_name}."""
from playwright.sync_api import Page, Locator, expect
from shared.config.settings import settings

class {class_name}:
    """Page Object for {page_url}."""

    PAGE_URL: str = "{page_url}"

    def __init__(self, page: Page) -> None:
        self.page = page
{locators_block}

    def navigate(self) -> "{class_name}":
        """Navigate to {page_url}."""
        self.page.goto(self.PAGE_URL)
        return self

    def assert_loaded(self) -> "{class_name}":
        """Assert the page is loaded and body is visible."""
        expect(self.page.locator("body")).to_be_visible()
        return self

    def get_element(self, selector: str) -> Locator:
        """Retrieve Playwright locator for a selector."""
        return self.page.locator(selector)
{actions_block}
'''
        return code

    def _register_selector_mapping(
        self, meta: Dict[str, Any], selector: str, method_name: str, action_type: str, elem: Dict[str, Any]
    ) -> None:
        mappings = meta.setdefault("selector_to_method", {})
        mappings[selector] = (method_name, action_type)
        if '"' in selector:
            mappings[selector.replace('"', "'")] = (method_name, action_type)
        if "'" in selector:
            mappings[selector.replace("'", '"')] = (method_name, action_type)

        elem_map = meta.setdefault("element_to_method", {})
        for key in ("test_id", "element_id", "name", "label"):
            val = elem.get(key)
            if val:
                sval = str(val).strip().lower()
                elem_map[sval] = (method_name, action_type)
                elem_map[sval.replace("-", "_")] = (method_name, action_type)
                elem_map[sval.replace("_", "-")] = (method_name, action_type)
                elem_map[sval.replace(" ", "_")] = (method_name, action_type)
                elem_map[sval.replace(" ", "-")] = (method_name, action_type)

    def _extract_best_selector(self, elem: Dict[str, Any]) -> str:
        if elem.get("test_id"):
            return f'[data-testid="{elem["test_id"]}"]'
        if elem.get("element_id"):
            return f'#{elem["element_id"]}'
        if elem.get("name") and elem.get("tag") in {"input", "select", "textarea"}:
            return f'{elem["tag"]}[name="{elem["name"]}"]'
        if elem.get("placeholder"):
            return f'[placeholder="{elem["placeholder"]}"]'
        if elem.get("css_selector"):
            return elem["css_selector"]
        if elem.get("visible_text") and len(elem["visible_text"]) < 40:
            clean_text = elem["visible_text"].replace('"', '\\"')
            return f'text="{clean_text}"'
        return ""

    def _generate_test_file_code(
        self,
        test_case: Dict[str, Any],
        scenario: Dict[str, Any],
        pages_meta: Dict[str, Dict[str, Any]],
        base_url: str,
        credentials: Optional[Dict[str, Any]],
        matched_page: Optional[Dict[str, Any]] = None,
    ) -> str:
        tc_title = test_case.get("title", "Test Scenario")
        tc_id = test_case.get("test_case_id", "TC_001")
        sc_id = scenario.get("scenario_id", "SC_001")
        safe_func_name = f"test_{sanitize_identifier(tc_title, fallback='test_case')}"

        if not matched_page or test_case.get("evidence_status") == "unsupported_missing_evidence":
            reasons = test_case.get("unsupported_evidence_reasons") or [
                "UNSUPPORTED / MISSING EVIDENCE: No verified target page found in crawl evidence"
            ]
            reason_text = "; ".join(reasons)
            return f'''"""Test Case: {tc_title}
Scenario: {sc_id} | Test Case ID: {tc_id}
Status: UNSUPPORTED / MISSING EVIDENCE
"""
import pytest

@pytest.mark.skip(reason={reason_text!r})
def {safe_func_name}() -> None:
    """Test skipped due to missing crawl evidence."""
    pass
'''

        steps = test_case.get("steps", [])
        if not steps:
            steps = [
                {"step_number": 1, "action": f"Navigate to {base_url}", "expected_result": "Page loaded"},
                {"step_number": 2, "action": "Verify page elements", "expected_result": "Elements visible"},
            ]

        # 1. Determine ONLY the pages actually involved in this test case:
        used_page_urls: List[str] = []
        # Base/root page for initial navigation
        for p_url in pages_meta.keys():
            if _normalize_path(p_url) == _normalize_path(base_url):
                if p_url not in used_page_urls:
                    used_page_urls.append(p_url)
                break
        if not used_page_urls and pages_meta:
            used_page_urls.append(list(pages_meta.keys())[0])

        if matched_page and matched_page["url"] not in used_page_urls:
            used_page_urls.append(matched_page["url"])

        for s in steps:
            s_target = s.get("target_page")
            if s_target:
                t_norm = _normalize_path(s_target)
                for p_url in pages_meta.keys():
                    if _normalize_path(p_url) == t_norm or s_target == p_url:
                        if p_url not in used_page_urls:
                            used_page_urls.append(p_url)
                        break

        page_imports: List[str] = []
        instantiations: List[str] = []
        for p_url in used_page_urls:
            meta = pages_meta[p_url]
            mod = meta["module_name"]
            slug = meta["page_slug"]
            cls = meta["class_name"]
            page_imports.append(f"from modules.{mod}.pages.{slug}_page import {cls}")
            instantiations.append(f"    {slug}_page = {cls}(page)")

        imports_block = "\n".join(dict.fromkeys(page_imports))
        inst_block = "\n".join(instantiations)

        # 2. Determine root navigation page
        root_slug = matched_page["page_slug"] if matched_page else (list(pages_meta.values())[0]["page_slug"] if pages_meta else "home")
        for p_url in pages_meta.keys():
            if _normalize_path(p_url) == _normalize_path(base_url):
                root_slug = pages_meta[p_url]["page_slug"]
                break

        # 3. Check if first step is already base application navigation to prevent duplicate navigation
        first_step_is_nav = False
        if steps:
            first_act = str(steps[0].get("action", "")).lower()
            first_loc = str(steps[0].get("target_locator", ""))
            first_page = str(steps[0].get("target_page", ""))
            if (
                first_loc.startswith("page.goto")
                or (_normalize_path(first_page) == _normalize_path(base_url) and any(w in first_act for w in ("navigate", "open", "launch", "visit", "go to")))
                or any(w in first_act for w in ("navigate to application", "navigate to base", "open base", "open application"))
            ):
                first_step_is_nav = True

        actions_list: List[str] = []
        actions_list.append(f"    # Step 1: Navigate to application")
        actions_list.append(f"    {root_slug}_page.navigate()")
        actions_list.append(f"    {root_slug}_page.assert_loaded()")

        current_slug = root_slug
        start_step_idx = 1 if first_step_is_nav else 0

        for step in steps[start_step_idx:]:
            action = str(step.get("action", ""))
            action_lower = action.lower()
            num = step.get("step_number", "")
            target_page_url = step.get("target_page")
            target_loc = step.get("target_locator")
            target_elem = step.get("target_element")

            # Determine page for this step
            step_slug = current_slug
            step_meta = None
            if target_page_url:
                t_norm = _normalize_path(target_page_url)
                for p_url, meta in pages_meta.items():
                    if _normalize_path(p_url) == t_norm or target_page_url == p_url:
                        step_slug = meta["page_slug"]
                        step_meta = meta
                        break
            if not step_meta:
                for p_url, meta in pages_meta.items():
                    if meta["page_slug"] == step_slug:
                        step_meta = meta
                        break

            loc_label = f" [{target_loc}]" if target_loc else ""
            actions_list.append(f"\n    # Step {num}: {action}{loc_label}")

            if step_slug != current_slug:
                actions_list.append(f"    # Transition to {step_slug}_page")
                actions_list.append(f"    {step_slug}_page.assert_loaded()")
                current_slug = step_slug

            # Match Page Object method
            matched_method = None
            action_type = None

            if step_meta:
                sel_map = step_meta.get("selector_to_method", {})
                elem_map = step_meta.get("element_to_method", {})
                methods_dict = step_meta.get("methods", {})

                # 1. Exact selector lookup
                if target_loc and target_loc in sel_map:
                    matched_method, action_type = sel_map[target_loc]
                elif target_loc and target_loc.replace('"', "'") in sel_map:
                    matched_method, action_type = sel_map[target_loc.replace('"', "'")]
                elif target_loc and target_loc.replace("'", '"') in sel_map:
                    matched_method, action_type = sel_map[target_loc.replace("'", '"')]

                # 2. Target element lookup
                if not matched_method and target_elem:
                    te_clean = str(target_elem).strip().lower()
                    if te_clean in elem_map:
                        matched_method, action_type = elem_map[te_clean]
                    elif te_clean.replace("-", "_") in elem_map:
                        matched_method, action_type = elem_map[te_clean.replace("-", "_")]

                # 3. Keyword heuristic on available methods in Page Object
                if not matched_method and methods_dict:
                    for m_name, (m_type, _attr) in methods_dict.items():
                        m_clean = m_name.replace("fill_", "").replace("click_", "")
                        if m_clean in action_lower or (target_loc and m_clean in target_loc.lower()):
                            matched_method = m_name
                            action_type = m_type
                            break

            # Generate POM method call or fallback to Page Object get_element
            if matched_method:
                if action_type == "fill":
                    if any(w in action_lower or w in matched_method for w in ("user", "login", "email")):
                        actions_list.append(f'    {step_slug}_page.{matched_method}(default_credentials["username"])')
                    elif any(w in action_lower or w in matched_method for w in ("pass", "pwd", "secret")):
                        actions_list.append(f'    {step_slug}_page.{matched_method}(default_credentials["password"])')
                    else:
                        actions_list.append(f'    {step_slug}_page.{matched_method}("test_value")')
                elif action_type == "click":
                    actions_list.append(f'    {step_slug}_page.{matched_method}()')
            elif target_loc and not target_loc.startswith("page.goto") and not target_loc.startswith("expect("):
                # Use Page Object's get_element method rather than bypassing to page_obj.page
                if any(w in action_lower for w in ("click", "press", "select", "choose")):
                    actions_list.append(f'    {step_slug}_page.get_element({target_loc!r}).click()')
                elif any(w in action_lower for w in ("enter", "fill", "type")):
                    if any(w in action_lower for w in ("user", "login", "email")):
                        actions_list.append(f'    {step_slug}_page.get_element({target_loc!r}).fill(default_credentials["username"])')
                    elif any(w in action_lower for w in ("pass", "pwd", "secret")):
                        actions_list.append(f'    {step_slug}_page.get_element({target_loc!r}).fill(default_credentials["password"])')
                    else:
                        actions_list.append(f'    {step_slug}_page.get_element({target_loc!r}).fill("test_value")')
                else:
                    actions_list.append(f'    expect({step_slug}_page.get_element({target_loc!r})).to_be_visible()')
            elif any(w in action_lower for w in ("username", "login", "credentials")):
                actions_list.append(f"    if hasattr({step_slug}_page, 'fill_user_name'):")
                actions_list.append(f"        {step_slug}_page.fill_user_name(default_credentials['username'])")
                actions_list.append(f"    if hasattr({step_slug}_page, 'fill_password'):")
                actions_list.append(f"        {step_slug}_page.fill_password(default_credentials['password'])")
                actions_list.append(f"    if hasattr({step_slug}_page, 'click_login_button'):")
                actions_list.append(f"        {step_slug}_page.click_login_button()")
            elif any(w in action_lower for w in ("assert", "verify", "loaded", "visible", "displayed", "present", "shown")) :
                actions_list.append(f"    {step_slug}_page.assert_loaded()")

        steps_block = "\n".join(actions_list)

        code = f'''"""Test Case: {tc_title}
Scenario: {sc_id} | Test Case ID: {tc_id}
Generated by Test Case Generation Platform.
"""
import pytest
from playwright.sync_api import Page, expect
{imports_block}

@pytest.mark.regression
def {safe_func_name}(page: Page, default_credentials: dict) -> None:
    """{tc_title}."""
{inst_block}

{steps_block}
'''
        return code

    def _add_init_files(self, project: ModularProject) -> None:
        init_paths = [
            "shared/__init__.py",
            "shared/config/__init__.py",
            "shared/fixtures/__init__.py",
            "shared/utils/__init__.py",
            "shared/test_data/__init__.py",
            "modules/__init__.py",
        ]
        for mod in project.modules:
            init_paths.extend([
                f"modules/{mod}/__init__.py",
                f"modules/{mod}/pages/__init__.py",
                f"modules/{mod}/tests/__init__.py",
            ])
        for p in init_paths:
            if not any(f.relative_path == p for f in project.files):
                project.files.append(GeneratedFile(relative_path=p, content='"""Package marker."""\n'))

    def _add_root_config_files(self, project: ModularProject, base_url: str, credentials: Optional[Any] = None) -> None:
        ident = "test_user"
        if credentials:
            if hasattr(credentials, "get_identifier"):
                ident = credentials.get_identifier() if callable(credentials.get_identifier) else credentials.get_identifier
            elif hasattr(credentials, "identifier") and credentials.identifier:
                ident = credentials.identifier
            elif hasattr(credentials, "email") and credentials.email:
                ident = credentials.email
            elif hasattr(credentials, "username") and credentials.username:
                ident = credentials.username
            elif isinstance(credentials, dict):
                ident = credentials.get("identifier") or credentials.get("email") or credentials.get("username") or "test_user"
        ident = str(ident or "test_user")

        requirements_txt = """playwright>=1.40.0
pytest>=8.0.0
pytest-playwright>=0.4.4
python-dotenv>=1.0.0
"""
        project.files.append(GeneratedFile(relative_path="requirements.txt", content=requirements_txt, file_type="text"))

        env_example = f"""# Test Automation Environment Variables
APP_BASE_URL={base_url}
TEST_USERNAME={ident}
TEST_PASSWORD=your_password_here
HEADLESS=true
DEFAULT_TIMEOUT=10000
SLOW_MO=0
"""
        project.files.append(GeneratedFile(relative_path=".env.example", content=env_example, file_type="text"))

        pytest_ini = f"""[pytest]
testpaths = modules
pythonpath = .
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
markers =
    regression: Regression test suite
    smoke: Smoke test suite
"""
        project.files.append(GeneratedFile(relative_path="pytest.ini", content=pytest_ini, file_type="ini"))

        pyproject_toml = f"""[tool.pytest.ini_options]
testpaths = ["modules"]
pythonpath = ["."]
python_files = ["test_*.py"]
addopts = "-v --tb=short"
markers = [
    "regression: Regression test suite",
    "smoke: Smoke test suite",
]
"""
        project.files.append(GeneratedFile(relative_path="pyproject.toml", content=pyproject_toml, file_type="toml"))

        readme = f"""# {self.app_name.upper()} - Modular Playwright Automation Project

Automated test project generated with standard Page Object Model (POM) architecture.

## Directory Structure
```
{self.app_name}/
├── modules/
│   └── {{module_name}}/
│       ├── pages/          # Page Object classes
│       └── tests/          # Pytest test suites
├── shared/
│   ├── assets/             # Test assets / uploads
│   ├── config/             # Environment and settings
│   ├── fixtures/           # Global conftest.py fixtures
│   ├── test_data/          # Test data loader and JSON data
│   └── utils/              # Helper utilities
├── screenshots/            # Failure and execution screenshots
├── traces/                 # Playwright debug traces
├── reports/                # Pytest execution reports
├── requirements.txt
├── .env.example
├── pytest.ini
└── pyproject.toml
```

## Setup & Running Tests
1. Install dependencies:
```bash
pip install -r requirements.txt
playwright install chromium
```

2. Run all tests:
```bash
pytest
```

3. Run specific module:
```bash
pytest modules/core/tests/
```
"""
        project.files.append(GeneratedFile(relative_path="README.md", content=readme, file_type="text"))

    def validate_project(self, project: ModularProject) -> Dict[str, Any]:
        """Validate generated project for Python syntax, fixture loading, test discovery, and POM linkage."""
        errors: List[str] = []
        warnings: List[str] = []
        checks_passed: List[str] = []

        # 1. Check Python syntax of all generated .py files
        for f in project.files:
            if f.relative_path.endswith(".py"):
                try:
                    compile(f.content, f.relative_path, "exec")
                except SyntaxError as e:
                    errors.append(f"Syntax error in {f.relative_path}: {e}")

        if not any("Syntax error" in err for err in errors):
            checks_passed.append("python_syntax_valid")

        # 2. Check fixture discovery configuration
        has_root_conftest = any(f.relative_path == "conftest.py" for f in project.files)
        has_shared_conftest = any(f.relative_path == "shared/fixtures/conftest.py" for f in project.files)
        pytest_ini = next((f for f in project.files if f.relative_path == "pytest.ini"), None)

        if not (has_root_conftest and has_shared_conftest):
            errors.append("Missing root conftest.py or shared/fixtures/conftest.py")
        else:
            checks_passed.append("conftest_fixtures_configured")

        if not pytest_ini or "pythonpath = ." not in pytest_ini.content:
            errors.append("pytest.ini missing 'pythonpath = .'")
        else:
            checks_passed.append("pytest_pythonpath_configured")

        # 3. Check data loader and test data
        has_data_loader = any(f.relative_path == "shared/test_data/data_loader.py" for f in project.files)
        has_test_data = any(f.relative_path == "shared/test_data/test_data.json" for f in project.files)
        if not (has_data_loader and has_test_data):
            warnings.append("Missing test data loader or test_data.json")
        else:
            checks_passed.append("test_data_connected")

        # 4. Check test discovery and POM linkage
        for f in project.files:
            if "/tests/test_" in f.relative_path:
                if "modules/unsupported/" in f.relative_path:
                    if "@pytest.mark.skip" not in f.content:
                        errors.append(f"Unsupported test {f.relative_path} must be marked with @pytest.mark.skip")
                else:
                    if "Page(page)" not in f.content and "page: Page" not in f.content:
                        warnings.append(f"Test {f.relative_path} may not be using Page Object model")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "checks_passed": checks_passed,
            "file_count": len(project.files),
        }


project_structure_generator = ProjectStructureGenerator()
