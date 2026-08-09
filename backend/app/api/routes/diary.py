"""Diary routes (`/api/v1/diary`): the current authenticated user's log.

Every route requires authentication (`Depends(get_current_user)`) and scopes
all reads/writes to that user -- there is no way to pass another user's id
through a query parameter, path, or request body (see
`app/services/diary.py`).
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.diary import DiaryEntryCreate, DiaryEntryRead, DiaryEntryUpdate
from app.schemas.pagination import Page
from app.services import diary as diary_service
from app.services.production import ProductionNotFoundError

router = APIRouter(prefix="/api/v1/diary", tags=["diary"])


@router.get("", response_model=Page[DiaryEntryRead], summary="List the current user's diary")
async def list_diary_entries(
    limit: int = Query(diary_service.DEFAULT_LIMIT, ge=1, le=diary_service.MAX_LIMIT),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Page[DiaryEntryRead]:
    entries, total = await diary_service.list_diary_entries(
        session, current_user.id, limit=limit, offset=offset
    )
    return Page[DiaryEntryRead](
        items=[DiaryEntryRead.from_model(entry) for entry in entries],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=DiaryEntryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Log a production (create a diary entry)",
)
async def create_diary_entry(
    payload: DiaryEntryCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DiaryEntryRead:
    try:
        entry = await diary_service.create_diary_entry(session, current_user.id, payload)
    except ProductionNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Production not found") from exc
    return DiaryEntryRead.from_model(entry)


@router.get("/{entry_id}", response_model=DiaryEntryRead, summary="Get a diary entry")
async def get_diary_entry(
    entry_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DiaryEntryRead:
    try:
        entry = await diary_service.get_diary_entry(session, entry_id, current_user.id)
    except diary_service.DiaryEntryNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Diary entry not found") from exc
    return DiaryEntryRead.from_model(entry)


@router.patch("/{entry_id}", response_model=DiaryEntryRead, summary="Update a diary entry")
async def patch_diary_entry(
    entry_id: uuid.UUID,
    payload: DiaryEntryUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DiaryEntryRead:
    try:
        entry = await diary_service.update_diary_entry(session, entry_id, current_user.id, payload)
    except diary_service.DiaryEntryNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Diary entry not found") from exc
    return DiaryEntryRead.from_model(entry)


@router.delete(
    "/{entry_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a diary entry"
)
async def delete_diary_entry(
    entry_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    try:
        await diary_service.delete_diary_entry(session, entry_id, current_user.id)
    except diary_service.DiaryEntryNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Diary entry not found") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
