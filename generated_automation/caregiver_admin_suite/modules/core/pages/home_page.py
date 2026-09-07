"""Page Object Model for HomePage."""
from playwright.sync_api import Page, expect
from shared.config.settings import settings

class HomePage:
    """Page Object for https://qa-caregiver-adminpanel.cdians.com/."""

    PAGE_URL: str = "https://qa-caregiver-adminpanel.cdians.com/"

    def __init__(self, page: Page) -> None:
        self.page = page
        self.email_address_email_address_password_password_forgot_password_reset_here_sign_in_or_sign_in_with_microsoft_by_using_this_application_you_agree_to_our_terms_conditions_and_privacy_policy_form = self.page.locator("form:nth-of-type(1)")
        self.email_address_input = self.page.locator("#_r_0_")
        self.reset_here_a = self.page.locator("a:nth-of-type(1)")
        self.sign_in_button = self.page.locator("button:nth-of-type(1)")
        self.microsoft_button = self.page.locator("button:nth-of-type(2)")
        self.terms_conditions_a = self.page.locator("a:nth-of-type(1)")
        self.privacy_policy_a = self.page.locator("a:nth-of-type(2)")

    def navigate(self) -> "HomePage":
        """Navigate to https://qa-caregiver-adminpanel.cdians.com/."""
        self.page.goto(self.PAGE_URL)
        return self

    def assert_loaded(self) -> "HomePage":
        """Assert the page is loaded and body is visible."""
        expect(self.page.locator("body")).to_be_visible()
        return self

    def fill_email_address(self, value: str) -> "HomePage":
        """Enter value into Email Address field."""
        self.email_address_input.fill(value)
        return self

    def click_reset_here(self) -> "HomePage":
        """Click the Reset here control."""
        self.reset_here_a.click()
        return self

    def click_sign_in(self) -> "HomePage":
        """Click the Sign In control."""
        self.sign_in_button.click()
        return self

    def click_microsoft(self) -> "HomePage":
        """Click the Microsoft control."""
        self.microsoft_button.click()
        return self

    def click_terms_conditions(self) -> "HomePage":
        """Click the Terms & Conditions control."""
        self.terms_conditions_a.click()
        return self

    def click_privacy_policy(self) -> "HomePage":
        """Click the Privacy Policy control."""
        self.privacy_policy_a.click()
        return self
