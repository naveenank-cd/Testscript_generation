from __future__ import annotations

import uuid
from typing import Any
from sqlalchemy.exc import DBAPIError, IntegrityError, SQLAlchemyError

from app.core.config import settings
from app.core.exceptions import DatabaseUnavailable, DuplicateEntity, ProjectNotFound
from app.models.project import Project
from app.repositories.project_repository import ProjectRepository



class ProjectService:
    def __init__(self, session):
        self.session = session
        self.repo = ProjectRepository(session)

    @staticmethod
    def _database_details() -> dict[str, object]:
        url = settings.database_url
        from sqlalchemy.engine import make_url

        parsed = make_url(url)
        return {"host": parsed.host or "127.0.0.1", "port": parsed.port or 5432}

    async def create(self, data):
        try:
            row = await self.repo.add(Project(**data))
            await self.session.commit()
            await self.session.refresh(row)
            return row
        except IntegrityError as exc:
            await self.session.rollback()
            raise DuplicateEntity("A project with the supplied values already exists") from exc
        except (DBAPIError, OSError) as exc:
            await self.session.rollback()
            raise DatabaseUnavailable(
                "Unable to connect to the PostgreSQL database.",
                details=self._database_details(),
            ) from exc
        except SQLAlchemyError as exc:
            await self.session.rollback()
            raise DatabaseUnavailable(
                "Unable to complete the PostgreSQL database operation.",
                details=self._database_details(),
            ) from exc

    async def list(self):
        try:
            return await self.repo.list_active()
        except (SQLAlchemyError, OSError) as exc:
            await self.session.rollback()
            raise DatabaseUnavailable(
                "Unable to connect to the PostgreSQL database.",
                details=self._database_details(),
            ) from exc

    async def get(self, entity_id):
        try:
            row = await self.repo.get(entity_id)
        except (SQLAlchemyError, OSError) as exc:
            await self.session.rollback()
            raise DatabaseUnavailable(
                "Unable to connect to the PostgreSQL database.",
                details=self._database_details(),
            ) from exc
        if not row or not row.is_active:
            raise ProjectNotFound("Project was not found")
        return row

    async def update(self, entity_id, data):
        row = await self.get(entity_id)
        try:
            for key, value in data.items():
                if value is not None:
                    setattr(row, key, value)
            await self.session.commit()
            await self.session.refresh(row)
            return row
        except SQLAlchemyError as exc:
            await self.session.rollback()
            raise DatabaseUnavailable(
                "Unable to complete the PostgreSQL database operation.",
                details=self._database_details(),
            ) from exc

    async def delete(self, entity_id):
        row = await self.get(entity_id)
        try:
            await self.repo.soft_delete(row)
            await self.session.commit()
        except SQLAlchemyError as exc:
            await self.session.rollback()
            raise DatabaseUnavailable(
                "Unable to complete the PostgreSQL database operation.",
                details=self._database_details(),
            ) from exc

    async def get_by_name(self, name: str):
        try:
            return await self.repo.get_by_name(name)
        except (SQLAlchemyError, OSError) as exc:
            await self.session.rollback()
            raise DatabaseUnavailable(
                "Unable to connect to the PostgreSQL database.",
                details=self._database_details(),
            ) from exc

    async def get_crawl_knowledge(self, entity_id: uuid.UUID):
        row = await self.get(entity_id)
        if not row.crawl_knowledge:
            raise ProjectNotFound("No crawl knowledge found for this project.")
        return row.crawl_knowledge

    async def save_crawl_knowledge(
        self,
        entity_id: uuid.UUID,
        crawl_knowledge: dict,
        latest_crawl_id: str | None = None,
        application_url: str | None = None,
        auth_config: dict | None = None,
    ):
        row = await self.get(entity_id)
        try:
            row.crawl_knowledge = crawl_knowledge
            if latest_crawl_id:
                row.latest_crawl_id = latest_crawl_id
            if application_url:
                row.application_url = application_url
            if auth_config:
                row.auth_config = auth_config
            await self.session.commit()
            await self.session.refresh(row)
            return row
        except SQLAlchemyError as exc:
            await self.session.rollback()
            raise DatabaseUnavailable(
                "Unable to complete the PostgreSQL database operation.",
                details=self._database_details(),
            ) from exc

    async def get_or_create_project(
        self,
        project_id: uuid.UUID | None = None,
        project_name: str | None = None,
        application_url: str | None = None,
        auth_config: dict | None = None,
    ):
        if project_id:
            try:
                row = await self.get(project_id)
                updated = False
                if application_url and row.application_url != application_url:
                    row.application_url = application_url
                    updated = True
                if auth_config and row.auth_config != auth_config:
                    row.auth_config = auth_config
                    updated = True
                if project_name and project_name.strip() and row.name != project_name.strip():
                    row.name = project_name.strip()
                    updated = True
                if updated:
                    await self.session.commit()
                    await self.session.refresh(row)
                return row
            except ProjectNotFound:
                name = (project_name.strip() if project_name and project_name.strip() else f"Project {str(project_id)[:8]}")
                data = {
                    "id": project_id,
                    "name": name,
                    "application_url": application_url,
                    "auth_config": auth_config,
                }
                return await self.create(data)

        if project_name and project_name.strip():
            clean_name = project_name.strip()
            existing = await self.get_by_name(clean_name)
            if existing:
                updated = False
                if application_url and existing.application_url != application_url:
                    existing.application_url = application_url
                    updated = True
                if auth_config and existing.auth_config != auth_config:
                    existing.auth_config = auth_config
                    updated = True
                if updated:
                    await self.session.commit()
                    await self.session.refresh(existing)
                return existing
            return await self.create({
                "name": clean_name,
                "application_url": application_url,
                "auth_config": auth_config,
            })

        new_name = f"Project {uuid.uuid4().hex[:8]}"
        return await self.create({
            "name": new_name,
            "application_url": application_url,
            "auth_config": auth_config,
        })

    async def get_generations(self, project_id: uuid.UUID) -> list[dict]:
        """Return all persistent requirement generations (workflows) for this project."""
        project = await self.get(project_id)
        from app.services.workflow_service import workflow_service
        workflows = workflow_service.get_workflows_for_project(project_id)
        generations = []
        for wf in workflows:
            input_payload = wf.get("input_payload") or {}
            user_stories = input_payload.get("user_stories") or []
            acceptance_criteria = input_payload.get("acceptance_criteria") or []
            scenarios = wf.get("scenarios") or []
            test_cases = wf.get("test_cases") or []
            generations.append({
                "workflow_id": str(wf.get("workflow_id")),
                "project_id": str(project_id),
                "project_name": project.name,
                "status": wf.get("status", "unknown"),
                "current_stage": wf.get("current_stage", "unknown"),
                "started_at": wf.get("started_at"),
                "completed_at": wf.get("completed_at"),
                "user_story_count": len(user_stories),
                "acceptance_criteria_count": len(acceptance_criteria),
                "scenario_count": len(scenarios),
                "test_case_count": len(test_cases),
                "user_stories": user_stories,
                "acceptance_criteria": acceptance_criteria,
                "scenarios": scenarios,
                "test_cases": test_cases,
                "crawl_id": wf.get("crawl_knowledge", {}).get("crawl_id") if isinstance(wf.get("crawl_knowledge"), dict) else None,
            })
        return generations

