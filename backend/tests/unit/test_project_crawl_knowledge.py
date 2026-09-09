import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import pytest

from app.models.project import Project
from app.services.project_service import ProjectService
from app.services.automation_service import AutomationService
from app.schemas.automation_schema import (
    CrawlAndGenerateRequest,
    CrawlApplicationRequest,
    DiscoveredElement,
)
from app.schemas.input_schema import WorkflowStartRequest
from app.core.exceptions import ProjectNotFound


@pytest.mark.asyncio
async def test_project_represents_one_application():
    session = AsyncMock()
    service = ProjectService(session)
    project_id = uuid.uuid4()
    exact_name = "My Enterprise Portal"
    app_url = "https://portal.enterprise.internal/app"
    auth_config = {"auth_mode": "credentials", "identifier": "qa_user", "password": "qa_password"}

    # Mock repository
    mock_project = Project(
        id=project_id,
        name=exact_name,
        application_url=app_url,
        auth_config=auth_config,
        status="active",
        is_active=True,
    )
    service.repo.add = AsyncMock(return_value=mock_project)

    created = await service.create({
        "name": exact_name,
        "application_url": app_url,
        "auth_config": auth_config,
    })

    assert created.name == exact_name
    assert created.application_url == app_url
    assert created.auth_config == auth_config
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_save_and_retrieve_crawl_knowledge_by_project_id():
    session = AsyncMock()
    service = ProjectService(session)
    project_id = uuid.uuid4()
    crawl_id = f"crawl-{uuid.uuid4()}"

    crawl_knowledge = {
        "crawl_id": crawl_id,
        "application_url": "https://example.com",
        "page_title": "Example Domain",
        "crawl_status": "crawl_completed",
        "pages_crawled": 3,
        "elements_found": 15,
        "crawl_report": {"pages_completed": 3, "status": "crawl_completed"},
        "application_map": {
            "pages": [{"url": "https://example.com/login", "title": "Login"}],
            "relationships": [{"from": "https://example.com", "to": "https://example.com/login"}],
            "locators": {"login_btn": "button[type='submit']"},
        },
        "locators": {"login_btn": "button[type='submit']"},
        "discovered_elements": [{"role": "button", "name": "Login", "test_id": "login-submit"}],
    }

    project = Project(
        id=project_id,
        name="Example App",
        application_url="https://example.com",
        is_active=True,
        crawl_knowledge=None,
    )
    service.get = AsyncMock(return_value=project)

    # Save knowledge
    updated = await service.save_crawl_knowledge(
        entity_id=project_id,
        crawl_knowledge=crawl_knowledge,
        latest_crawl_id=crawl_id,
        application_url="https://example.com",
    )

    assert updated.crawl_knowledge == crawl_knowledge
    assert updated.latest_crawl_id == crawl_id
    session.commit.assert_awaited_once()

    # Retrieve knowledge using project_id
    retrieved = await service.get_crawl_knowledge(project_id)
    assert retrieved == crawl_knowledge
    assert retrieved["pages_crawled"] == 3
    assert len(retrieved["application_map"]["pages"]) == 1
    assert retrieved["locators"]["login_btn"] == "button[type='submit']"


@pytest.mark.asyncio
async def test_get_crawl_knowledge_raises_not_found_when_empty():
    session = AsyncMock()
    service = ProjectService(session)
    project_id = uuid.uuid4()
    project = Project(id=project_id, name="Uncrawled App", is_active=True, crawl_knowledge=None)
    service.get = AsyncMock(return_value=project)

    with pytest.raises(ProjectNotFound, match="No crawl knowledge found"):
        await service.get_crawl_knowledge(project_id)


@pytest.mark.asyncio
async def test_automation_service_persists_crawl_to_project(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.automation_service.settings.automation_artifacts_path",
        str(tmp_path),
    )
    auto_service = AutomationService()
    project_id = uuid.uuid4()
    crawl_id = "crawl-test-123"

    mock_project = SimpleNamespace(id=project_id, name="Test Project")

    with patch("app.services.project_service.ProjectService.get_or_create_project", new_callable=AsyncMock) as mock_get_or_create, \
         patch("app.services.project_service.ProjectService.save_crawl_knowledge", new_callable=AsyncMock) as mock_save_knowledge:
        mock_get_or_create.return_value = mock_project

        resolved_id, resolved_name = await auto_service._persist_crawl_to_project(
            project_id=project_id,
            project_name="Test Project",
            application_url="https://testapp.com",
            auth_config={"auth_mode": "no_auth"},
            crawl_id=crawl_id,
            crawl_status="crawl_completed",
            pages_crawled=2,
            elements_found=5,
            page_title="Test App",
            crawl_report={"status": "crawl_completed"},
            application_map={"pages": [{"url": "https://testapp.com"}], "relationships": []},
            discovered_elements=[{"role": "button", "name": "Submit"}],
        )

        assert resolved_id == project_id
        assert resolved_name == "Test Project"
        mock_get_or_create.assert_awaited_once()
        mock_save_knowledge.assert_awaited_once()

    # Knowledge is retrievable via get_project_crawl_knowledge
    knowledge = await auto_service.get_project_crawl_knowledge(project_id)
    assert knowledge is not None
    assert knowledge["crawl_id"] == crawl_id
    assert knowledge["pages_crawled"] == 2
    assert knowledge["application_url"] == "https://testapp.com"


@pytest.mark.asyncio
async def test_workflow_reuses_persisted_crawl_knowledge_without_recrawling(monkeypatch):
    project_id = uuid.uuid4()
    crawl_knowledge = {
        "crawl_id": "crawl-cached-001",
        "application_url": "https://myapp.internal",
        "pages_crawled": 5,
        "application_map": {"pages": [{"url": "https://myapp.internal/dashboard"}]},
    }

    mock_project = SimpleNamespace(
        id=project_id,
        name="Cached Project",
        crawl_knowledge=crawl_knowledge,
    )

    with patch("app.services.project_service.ProjectService.get_or_create_project", new_callable=AsyncMock) as mock_get_or_create:
        mock_get_or_create.return_value = mock_project
        from app.services.workflow_service import workflow_service

        request = WorkflowStartRequest(
            project_id=project_id,
            project_name="Cached Project",
            input_payload={"user_stories": ["As a user, I want to login"]},
            mock_mode=True,
        )

        state = await workflow_service.start(request)
        assert state["project_id"] == project_id
        assert state["crawl_knowledge"] == crawl_knowledge
        assert state["crawl_knowledge"]["crawl_id"] == "crawl-cached-001"


@pytest.mark.asyncio
async def test_partial_crawl_persists_partial_knowledge(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.automation_service.settings.automation_artifacts_path",
        str(tmp_path),
    )
    auto_service = AutomationService()
    project_id = uuid.uuid4()
    crawl_id = "crawl-partial-456"

    mock_project = SimpleNamespace(id=project_id, name="Partial Crawl App")

    with patch("app.services.project_service.ProjectService.get_or_create_project", new_callable=AsyncMock) as mock_get_or_create, \
         patch("app.services.project_service.ProjectService.save_crawl_knowledge", new_callable=AsyncMock) as mock_save_knowledge:
        mock_get_or_create.return_value = mock_project

        resolved_id, _ = await auto_service._persist_crawl_to_project(
            project_id=project_id,
            project_name="Partial Crawl App",
            application_url="https://partial.testapp.com",
            auth_config=None,
            crawl_id=crawl_id,
            crawl_status="crawl_incomplete",
            pages_crawled=1,
            elements_found=3,
            page_title="Partial App",
            crawl_report={"status": "crawl_incomplete", "pages_completed": 1, "events": ["crawl_stopped"]},
            application_map={"pages": [{"url": "https://partial.testapp.com"}], "relationships": []},
            discovered_elements=[{"role": "link", "name": "Docs"}],
        )

        assert resolved_id == project_id
        mock_save_knowledge.assert_awaited_once()

    knowledge = await auto_service.get_project_crawl_knowledge(project_id)
    assert knowledge is not None
    assert knowledge["crawl_status"] == "crawl_incomplete"
    assert knowledge["pages_crawled"] == 1
    assert len(knowledge["discovered_elements"]) == 1


@pytest.mark.asyncio
async def test_api_get_project_crawl_knowledge_endpoint():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api.dependencies import get_db

    project_id = uuid.uuid4()
    crawl_knowledge = {
        "crawl_id": "crawl-api-999",
        "application_url": "https://api.testapp.com",
        "pages_crawled": 4,
        "crawl_status": "crawl_completed",
    }

    mock_service = AsyncMock()
    mock_service.get_crawl_knowledge.return_value = crawl_knowledge

    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch("app.api.v1.project_router.ProjectService", return_value=mock_service):
            client = TestClient(app)
            response = client.get(f"/api/v1/projects/{project_id}/crawl-knowledge")
            assert response.status_code == 200
            data = response.json()
            assert data["crawl_id"] == "crawl-api-999"
            assert data["pages_crawled"] == 4
            assert data["crawl_status"] == "crawl_completed"
    finally:
        app.dependency_overrides.pop(get_db, None)

