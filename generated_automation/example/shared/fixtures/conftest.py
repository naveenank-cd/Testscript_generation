"""Pytest global fixtures for Playwright browser and page management."""
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
        viewport={"width": 1280, "height": 720},
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
    default_creds = test_data.get("credentials", {}).get("default", {})
    return {
        "username": os.getenv("TEST_USERNAME", default_creds.get("username", "test_user")),
        "password": os.getenv("TEST_PASSWORD", default_creds.get("password", "")),
    }
