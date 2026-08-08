"""Production catalogue routes (`/api/v1/productions`)."""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.pagination import Page
from app.schemas.production import (
    ProductionCreate,
    ProductionRead,
    ProductionSummary,
    ProductionUpdate,
)
from app.services import production as production_service

router = APIRouter(prefix="/api/v1/productions", tags=["productions"])


@router.get("", response_model=Page[ProductionSummary], summary="List productions")
async def list_productions(
    search: str | None = Query(
        None,
        description=(
            "Matches title, work title, creator names, company, director, "
            "venue, or city (case-insensitive)"
        ),
    ),
    work_title: str | None = None,
    company_name: str | None = None,
    director_name: str | None = None,
    venue_name: str | None = None,
    city: str | None = None,
    country_code: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    limit: int = Query(production_service.DEFAULT_LIMIT, ge=1, le=production_service.MAX_LIMIT),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> Page[ProductionSummary]:
    items, total = await production_service.list_productions(
        session,
        search=search,
        work_title=work_title,
        company_name=company_name,
        director_name=director_name,
        venue_name=venue_name,
        city=city,
        country_code=country_code,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
    )
    return Page[ProductionSummary](
        items=[ProductionSummary.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=ProductionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a production",
)
async def create_production(
    payload: ProductionCreate, session: AsyncSession = Depends(get_db)
) -> ProductionRead:
    try:
        production = await production_service.create_production(session, payload)
    except production_service.DuplicateSlugError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except production_service.InvalidDateRangeError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return ProductionRead.model_validate(production)


# Registered before GET /{production_id} so the literal "slug" path segment
# is never captured by the {production_id} path parameter.
@router.get(
    "/slug/{slug}",
    response_model=ProductionRead,
    summary="Get a production by slug",
)
async def get_production_by_slug(
    slug: str, session: AsyncSession = Depends(get_db)
) -> ProductionRead:
    try:
        production = await production_service.get_production_by_slug(session, slug)
    except production_service.ProductionNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Production not found") from exc
    return ProductionRead.model_validate(production)


@router.get(
    "/{production_id}",
    response_model=ProductionRead,
    summary="Get a production by ID",
)
async def get_production(
    production_id: uuid.UUID, session: AsyncSession = Depends(get_db)
) -> ProductionRead:
    try:
        production = await production_service.get_production_by_id(session, production_id)
    except production_service.ProductionNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Production not found") from exc
    return ProductionRead.model_validate(production)


@router.patch(
    "/{production_id}",
    response_model=ProductionRead,
    summary="Partially update a production",
)
async def patch_production(
    production_id: uuid.UUID,
    payload: ProductionUpdate,
    session: AsyncSession = Depends(get_db),
) -> ProductionRead:
    try:
        production = await production_service.update_production(session, production_id, payload)
    except production_service.ProductionNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Production not found") from exc
    except production_service.DuplicateSlugError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except production_service.InvalidDateRangeError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return ProductionRead.model_validate(production)


@router.delete(
    "/{production_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a production",
)
async def delete_production(
    production_id: uuid.UUID, session: AsyncSession = Depends(get_db)
) -> Response:
    try:
        await production_service.delete_production(session, production_id)
    except production_service.ProductionNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Production not found") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
