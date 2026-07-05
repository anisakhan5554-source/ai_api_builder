from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db
from dependencies.auth import get_current_user
from models import Project, GeneratedAPI

router = APIRouter(tags=["Projects"])

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

@router.post("/projects")
async def create_project(
    project: ProjectCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    new_project = Project(
        user_id=current_user.id,
        name=project.name,
        description=project.description
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return {
        "status": "success",
        "project": {
            "id": new_project.id,
            "name": new_project.name,
            "description": new_project.description,
            "created_at": new_project.created_at
        }
    }

@router.get("/projects")
async def get_projects(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    projects = db.query(Project).filter(
        Project.user_id == current_user.id
    ).all()
    return {
        "status": "success",
        "count": len(projects),
        "projects": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "created_at": p.created_at
            }
            for p in projects
        ]
    }

@router.get("/projects/{project_id}")
async def get_project(
    project_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    apis = db.query(GeneratedAPI).filter(
        GeneratedAPI.project_id == project_id,
        GeneratedAPI.is_deleted != True
    ).all()

    return {
        "status": "success",
        "project": {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "created_at": project.created_at
        },
        "apis": [
            {
                "id": a.id,
                "prompt": a.prompt,
                "provider": a.provider,
                "created_at": a.created_at
            }
            for a in apis
        ]
    }

@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()

    return {"status": "success", "message": f"Project {project_id} deleted"}