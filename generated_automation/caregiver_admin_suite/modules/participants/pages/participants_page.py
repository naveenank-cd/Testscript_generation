"""Page Object Model for ParticipantsPage."""
from playwright.sync_api import Page, expect
from shared.config.settings import settings

class ParticipantsPage:
    """Page Object for https://qa-caregiver-adminpanel.cdians.com/participants."""

    PAGE_URL: str = "https://qa-caregiver-adminpanel.cdians.com/participants"

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
        self.search_input = self.page.locator("input[name="search"]")
        self.open_map_button = self.page.locator("button:nth-of-type(1)")
        self.upload_participants_button = self.page.locator("button:nth-of-type(2)")
        self.export_participants_button = self.page.locator("button:nth-of-type(3)")
        self.new_participant_button = self.page.locator("button:nth-of-type(4)")
        self.id_sorted_ascending_span = self.page.locator("span:nth-of-type(1)")
        self.elem_div_10_div = self.page.locator("#_r_14_")
        self.elem_div_10_25_50_div = self.page.locator("div:nth-of-type(3)")
        self.elem_ul_10_25_50_ul = self.page.locator("#_r_16_")
        self.elem_li_10_li = self.page.locator("li:nth-of-type(1)")
        self.elem_li_25_li = self.page.locator("li:nth-of-type(2)")
        self.elem_li_50_li = self.page.locator("li:nth-of-type(3)")
        self.browse_files_label = self.page.locator("label:nth-of-type(1)")

    def navigate(self) -> "ParticipantsPage":
        """Navigate to https://qa-caregiver-adminpanel.cdians.com/participants."""
        self.page.goto(self.PAGE_URL)
        return self

    def assert_loaded(self) -> "ParticipantsPage":
        """Assert the page is loaded and body is visible."""
        expect(self.page.locator("body")).to_be_visible()
        return self

    def click_dashboard(self) -> "ParticipantsPage":
        """Click the Dashboard control."""
        self.dashboard_a.click()
        return self

    def click_appointments(self) -> "ParticipantsPage":
        """Click the Appointments control."""
        self.appointments_a.click()
        return self

    def click_caregivers(self) -> "ParticipantsPage":
        """Click the Caregivers control."""
        self.caregivers_a.click()
        return self

    def click_participants(self) -> "ParticipantsPage":
        """Click the Participants control."""
        self.participants_a.click()
        return self

    def click_users(self) -> "ParticipantsPage":
        """Click the Users control."""
        self.users_a.click()
        return self

    def click_availability(self) -> "ParticipantsPage":
        """Click the Availability control."""
        self.availability_a.click()
        return self

    def click_audit_trails(self) -> "ParticipantsPage":
        """Click the Audit Trails control."""
        self.audit_trails_a.click()
        return self

    def click_pto_approval(self) -> "ParticipantsPage":
        """Click the PTO Approval control."""
        self.pto_approval_a.click()
        return self

    def click_settings(self) -> "ParticipantsPage":
        """Click the Settings control."""
        self.settings_a.click()
        return self

    def fill_search(self, value: str) -> "ParticipantsPage":
        """Enter value into search field."""
        self.search_input.fill(value)
        return self

    def click_open_map(self) -> "ParticipantsPage":
        """Click the Open map control."""
        self.open_map_button.click()
        return self

    def click_upload_participants(self) -> "ParticipantsPage":
        """Click the Upload Participants control."""
        self.upload_participants_button.click()
        return self

    def click_export_participants(self) -> "ParticipantsPage":
        """Click the Export Participants control."""
        self.export_participants_button.click()
        return self

    def click_new_participant(self) -> "ParticipantsPage":
        """Click the New Participant control."""
        self.new_participant_button.click()
        return self

    def click_id_sorted_ascending(self) -> "ParticipantsPage":
        """Click the ID
sorted ascending control."""
        self.id_sorted_ascending_span.click()
        return self

    def click_browse_files(self) -> "ParticipantsPage":
        """Click the Browse Files control."""
        self.browse_files_label.click()
        return self
