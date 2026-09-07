"""Page Object Model for PrivacyPolicyPage."""
from playwright.sync_api import Page, expect
from shared.config.settings import settings

class PrivacyPolicyPage:
    """Page Object for https://qa-caregiver-adminpanel.cdians.com/privacy-policy."""

    PAGE_URL: str = "https://qa-caregiver-adminpanel.cdians.com/privacy-policy"

    def __init__(self, page: Page) -> None:
        self.page = page
        self.elem_a_1_866224_2680_a = self.page.locator("a:nth-of-type(1)")
        self.supportconclavesai_a = self.page.locator("a:nth-of-type(1)")

    def navigate(self) -> "PrivacyPolicyPage":
        """Navigate to https://qa-caregiver-adminpanel.cdians.com/privacy-policy."""
        self.page.goto(self.PAGE_URL)
        return self

    def assert_loaded(self) -> "PrivacyPolicyPage":
        """Assert the page is loaded and body is visible."""
        expect(self.page.locator("body")).to_be_visible()
        return self

    def click_item_1_866224_2680(self) -> "PrivacyPolicyPage":
        """Click the +1 (866)224-2680 control."""
        self.elem_a_1_866224_2680_a.click()
        return self

    def click_supportconclavesai(self) -> "PrivacyPolicyPage":
        """Click the support@conclaves.ai control."""
        self.supportconclavesai_a.click()
        return self
