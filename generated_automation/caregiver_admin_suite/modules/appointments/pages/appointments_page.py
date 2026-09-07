"""Page Object Model for AppointmentsPage."""
from playwright.sync_api import Page, expect
from shared.config.settings import settings

class AppointmentsPage:
    """Page Object for https://qa-caregiver-adminpanel.cdians.com/appointments."""

    PAGE_URL: str = "https://qa-caregiver-adminpanel.cdians.com/appointments"

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
        self.weekly_button = self.page.locator("button:nth-of-type(1)")
        self.view_in_calendar_button = self.page.locator("button:nth-of-type(1)")
        self.search_input = self.page.locator("input[name="search"]")
        self.upload_button = self.page.locator("button:nth-of-type(1)")
        self.export_button = self.page.locator("button:nth-of-type(2)")
        self.filter_button = self.page.locator("button:nth-of-type(3)")
        self.new_appointment_button = self.page.locator("button:nth-of-type(4)")
        self.id_span = self.page.locator("span:nth-of-type(1)")
        self.participant_span = self.page.locator("span:nth-of-type(1)")
        self.date_sorted_ascending_span = self.page.locator("span:nth-of-type(1)")
        self.time_span = self.page.locator("span:nth-of-type(1)")
        self.status_span = self.page.locator("span:nth-of-type(1)")
        self.appointment_type_span = self.page.locator("span:nth-of-type(1)")
        self.caregiver_span = self.page.locator("span:nth-of-type(1)")
        self.elem_div_10_div = self.page.locator("#_r_7_")
        self.go_to_next_page_button = self.page.locator("button:nth-of-type(2)")
        self.elem_div_10_25_50_div = self.page.locator("div:nth-of-type(3)")
        self.elem_ul_10_25_50_ul = self.page.locator("#_r_9_")
        self.elem_li_10_li = self.page.locator("li:nth-of-type(1)")
        self.elem_li_25_li = self.page.locator("li:nth-of-type(2)")
        self.elem_li_50_li = self.page.locator("li:nth-of-type(3)")

    def navigate(self) -> "AppointmentsPage":
        """Navigate to https://qa-caregiver-adminpanel.cdians.com/appointments."""
        self.page.goto(self.PAGE_URL)
        return self

    def assert_loaded(self) -> "AppointmentsPage":
        """Assert the page is loaded and body is visible."""
        expect(self.page.locator("body")).to_be_visible()
        return self

    def click_dashboard(self) -> "AppointmentsPage":
        """Click the Dashboard control."""
        self.dashboard_a.click()
        return self

    def click_appointments(self) -> "AppointmentsPage":
        """Click the Appointments control."""
        self.appointments_a.click()
        return self

    def click_caregivers(self) -> "AppointmentsPage":
        """Click the Caregivers control."""
        self.caregivers_a.click()
        return self

    def click_participants(self) -> "AppointmentsPage":
        """Click the Participants control."""
        self.participants_a.click()
        return self

    def click_users(self) -> "AppointmentsPage":
        """Click the Users control."""
        self.users_a.click()
        return self

    def click_availability(self) -> "AppointmentsPage":
        """Click the Availability control."""
        self.availability_a.click()
        return self

    def click_audit_trails(self) -> "AppointmentsPage":
        """Click the Audit Trails control."""
        self.audit_trails_a.click()
        return self

    def click_pto_approval(self) -> "AppointmentsPage":
        """Click the PTO Approval control."""
        self.pto_approval_a.click()
        return self

    def click_settings(self) -> "AppointmentsPage":
        """Click the Settings control."""
        self.settings_a.click()
        return self

    def click_weekly(self) -> "AppointmentsPage":
        """Click the Weekly control."""
        self.weekly_button.click()
        return self

    def click_view_in_calendar(self) -> "AppointmentsPage":
        """Click the View in Calendar control."""
        self.view_in_calendar_button.click()
        return self

    def fill_search(self, value: str) -> "AppointmentsPage":
        """Enter value into search field."""
        self.search_input.fill(value)
        return self

    def click_upload(self) -> "AppointmentsPage":
        """Click the Upload control."""
        self.upload_button.click()
        return self

    def click_export(self) -> "AppointmentsPage":
        """Click the Export control."""
        self.export_button.click()
        return self

    def click_filter(self) -> "AppointmentsPage":
        """Click the Filter control."""
        self.filter_button.click()
        return self

    def click_new_appointment(self) -> "AppointmentsPage":
        """Click the New Appointment control."""
        self.new_appointment_button.click()
        return self

    def click_id(self) -> "AppointmentsPage":
        """Click the ID control."""
        self.id_span.click()
        return self

    def click_participant(self) -> "AppointmentsPage":
        """Click the PARTICIPANT control."""
        self.participant_span.click()
        return self

    def click_date_sorted_ascending(self) -> "AppointmentsPage":
        """Click the DATE
sorted ascending control."""
        self.date_sorted_ascending_span.click()
        return self

    def click_time(self) -> "AppointmentsPage":
        """Click the TIME control."""
        self.time_span.click()
        return self

    def click_status(self) -> "AppointmentsPage":
        """Click the STATUS control."""
        self.status_span.click()
        return self

    def click_appointment_type(self) -> "AppointmentsPage":
        """Click the APPOINTMENT TYPE control."""
        self.appointment_type_span.click()
        return self

    def click_caregiver(self) -> "AppointmentsPage":
        """Click the CAREGIVER control."""
        self.caregiver_span.click()
        return self

    def click_go_to_next_page(self) -> "AppointmentsPage":
        """Click the Go to next page control."""
        self.go_to_next_page_button.click()
        return self
