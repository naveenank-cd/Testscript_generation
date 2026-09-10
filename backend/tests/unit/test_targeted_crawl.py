import uuid
import pytest
from app.schemas.automation_schema import CrawlAndGenerateRequest
from app.services.automation_service import AutomationService

@pytest.fixture
def automation_service():
    return AutomationService()

@pytest.mark.asyncio
async def test_targeted_crawl_invalid_boundary(automation_service):
    """Confirm target_url outside deployed application boundary is blocked."""
    req = CrawlAndGenerateRequest(
        url="https://example.com",
        target_url="https://attacker.evil.com/phish",
        page_limit=5,
        project_id=uuid.uuid4(),
    )
    title, elements = await automation_service._discover(
        str(req.url),
        target_url=str(req.target_url),
    )
    assert title is None
    assert elements == []
    report = automation_service._crawl_reports.get("https://example.com/")
    assert report is not None
    assert report["status"] == "crawl_blocked"
    assert "does not belong to the permitted application boundary" in report["failure_reason"]
