"""Page Object Model for TermsAndConditionsPage."""
from playwright.sync_api import Page, expect
from shared.config.settings import settings

class TermsAndConditionsPage:
    """Page Object for https://qa-caregiver-adminpanel.cdians.com/terms-and-conditions."""

    PAGE_URL: str = "https://qa-caregiver-adminpanel.cdians.com/terms-and-conditions"

    def __init__(self, page: Page) -> None:
        self.page = page
        self.elem_a_1_866224_2680_a = self.page.locator("a:nth-of-type(1)")
        self.supportconclavesai_a = self.page.locator("a:nth-of-type(1)")

    def navigate(self) -> "TermsAndConditionsPage":
        """Navigate to https://qa-caregiver-adminpanel.cdians.com/terms-and-conditions."""
        self.page.goto(self.PAGE_URL)
        return self

    def assert_loaded(self) -> "TermsAndConditionsPage":
        """Assert the page is loaded and body is visible."""
        expect(self.page.locator("body")).to_be_visible()
        return self

    def click_item_1_866224_2680(self) -> "TermsAndConditionsPage":
        """Click the +1 (866)224-2680 control."""
        self.elem_a_1_866224_2680_a.click()
        return self

    def click_supportconclavesai(self) -> "TermsAndConditionsPage":
        """Click the support@conclaves.ai control."""
        self.supportconclavesai_a.click()
        return self
