"""Page Object Model for CaregiversPage."""
from playwright.sync_api import Page, expect
from shared.config.settings import settings

class CaregiversPage:
    """Page Object for https://qa-caregiver-adminpanel.cdians.com/caregivers."""

    PAGE_URL: str = "https://qa-caregiver-adminpanel.cdians.com/caregivers"

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
        self.upload_button = self.page.locator("button:nth-of-type(1)")
        self.export_button = self.page.locator("button:nth-of-type(2)")
        self.new_caregiver_button = self.page.locator("button:nth-of-type(3)")
        self.id_sorted_ascending_span = self.page.locator("span:nth-of-type(1)")
        self.elem_div_10_div = self.page.locator("#_r_c_")
        self.upload_caregivers_upload_caregiver_records_using_an_excel_file_xls_or_xlsx_download_the_template_complete_the_required_fields_then_upload_need_a_template_download_template_drop_your_excel_file_here_or_browse_files_supported_formats_xlsx_xls_max_10mb_cancel_import_div = self.page.locator("div:nth-of-type(3)")
        self.browse_files_label = self.page.locator("label:nth-of-type(1)")

    def navigate(self) -> "CaregiversPage":
        """Navigate to https://qa-caregiver-adminpanel.cdians.com/caregivers."""
        self.page.goto(self.PAGE_URL)
        return self

    def assert_loaded(self) -> "CaregiversPage":
        """Assert the page is loaded and body is visible."""
        expect(self.page.locator("body")).to_be_visible()
        return self

    def click_dashboard(self) -> "CaregiversPage":
        """Click the Dashboard control."""
        self.dashboard_a.click()
        return self

    def click_appointments(self) -> "CaregiversPage":
        """Click the Appointments control."""
        self.appointments_a.click()
        return self

    def click_caregivers(self) -> "CaregiversPage":
        """Click the Caregivers control."""
        self.caregivers_a.click()
        return self

    def click_participants(self) -> "CaregiversPage":
        """Click the Participants control."""
        self.participants_a.click()
        return self

    def click_users(self) -> "CaregiversPage":
        """Click the Users control."""
        self.users_a.click()
        return self

    def click_availability(self) -> "CaregiversPage":
        """Click the Availability control."""
        self.availability_a.click()
        return self

    def click_audit_trails(self) -> "CaregiversPage":
        """Click the Audit Trails control."""
        self.audit_trails_a.click()
        return self

    def click_pto_approval(self) -> "CaregiversPage":
        """Click the PTO Approval control."""
        self.pto_approval_a.click()
        return self

    def click_settings(self) -> "CaregiversPage":
        """Click the Settings control."""
        self.settings_a.click()
        return self

    def fill_search(self, value: str) -> "CaregiversPage":
        """Enter value into search field."""
        self.search_input.fill(value)
        return self

    def click_upload(self) -> "CaregiversPage":
        """Click the Upload control."""
        self.upload_button.click()
        return self

    def click_export(self) -> "CaregiversPage":
        """Click the Export control."""
        self.export_button.click()
        return self

    def click_new_caregiver(self) -> "CaregiversPage":
        """Click the New Caregiver control."""
        self.new_caregiver_button.click()
        return self

    def click_id_sorted_ascending(self) -> "CaregiversPage":
        """Click the ID
sorted ascending control."""
        self.id_sorted_ascending_span.click()
        return self

    def click_browse_files(self) -> "CaregiversPage":
        """Click the Browse Files control."""
        self.browse_files_label.click()
        return self
