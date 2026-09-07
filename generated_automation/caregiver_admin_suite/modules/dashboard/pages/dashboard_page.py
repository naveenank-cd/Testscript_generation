"""Page Object Model for DashboardPage."""
from playwright.sync_api import Page, expect
from shared.config.settings import settings

class DashboardPage:
    """Page Object for https://qa-caregiver-adminpanel.cdians.com/dashboard."""

    PAGE_URL: str = "https://qa-caregiver-adminpanel.cdians.com/dashboard"

    def __init__(self, page: Page) -> None:
        self.page = page
        self.dashboard_a = self.page.locator("a:nth-of-type(1)")
        self.appointments_a = self.page.locator("a:nth-of-type(2)")
        self.caregivers_a = self.page.locator("a:nth-of-type(3)")
        self.participants_a = self.page.locator("a:nth-of-type(4)")
        self.users_a = self.page.locator("a:nth-of-type(5)")
        self.availability_a = self.page.locator("a:nth-of-type(6)")
        self.audit_trails_a = self.page.locator("a:nth-of-type(7)")
        self.pto_approval_a = self.page.locator("a:nth-of-type(8)")
        self.settings_a = self.page.locator("a:nth-of-type(9)")

    def navigate(self) -> "DashboardPage":
        """Navigate to https://qa-caregiver-adminpanel.cdians.com/dashboard."""
        self.page.goto(self.PAGE_URL)
        return self

    def assert_loaded(self) -> "DashboardPage":
        """Assert the page is loaded and body is visible."""
        expect(self.page.locator("body")).to_be_visible()
        return self

    def click_dashboard(self) -> "DashboardPage":
        """Click the Dashboard control."""
        self.dashboard_a.click()
        return self

    def click_appointments(self) -> "DashboardPage":
        """Click the Appointments control."""
        self.appointments_a.click()
        return self

    def click_caregivers(self) -> "DashboardPage":
        """Click the Caregivers control."""
        self.caregivers_a.click()
        return self

    def click_participants(self) -> "DashboardPage":
        """Click the Participants control."""
        self.participants_a.click()
        return self

    def click_users(self) -> "DashboardPage":
        """Click the Users control."""
        self.users_a.click()
        return self

    def click_availability(self) -> "DashboardPage":
        """Click the Availability control."""
        self.availability_a.click()
        return self

    def click_audit_trails(self) -> "DashboardPage":
        """Click the Audit Trails control."""
        self.audit_trails_a.click()
        return self

    def click_pto_approval(self) -> "DashboardPage":
        """Click the PTO Approval control."""
        self.pto_approval_a.click()
        return self

    def click_settings(self) -> "DashboardPage":
        """Click the Settings control."""
        self.settings_a.click()
        return self
