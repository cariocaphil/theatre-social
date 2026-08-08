"""Idempotent seed data for the Production catalogue.

Run with:
    uv run python -m app.db.seed
or, against a running container:
    podman compose exec backend uv run python -m app.db.seed
    docker compose exec backend uv run python -m app.db.seed

Each entry has a stable, explicit `slug`, used as the natural key: the
script looks up each slug before inserting, so re-running it never creates
duplicates.

Data-integrity note: entries that stage a public-domain play (e.g.
"Hamlet" / William Shakespeare, "A Doll's House" / Henrik Ibsen) use the
real, historically-attributed playwright as `creator_names`, since that is
a verifiable fact about the underlying work. Every *staging* detail
(company, director, venue, dates) is a clearly fictional placeholder
(`Example ...`, `Sample ...`) and is not presented as a real production.
Entries with wholly original/devised premises are fictional throughout.
"""

import asyncio
from datetime import date

from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.production import Production

SEED_PRODUCTIONS: list[dict] = [
    # Traditional theatre, full metadata, closed run.
    {
        "title": "Hamlet",
        "slug": "hamlet",
        "description": "A fictional example staging of Shakespeare's tragedy, used as seed data.",
        "work_title": "Hamlet",
        "creator_names": "William Shakespeare",
        "company_name": "Example Ensemble",
        "director_name": "Sample Director",
        "venue_name": "Example Theatre",
        "city": "Berlin",
        "country_code": "DE",
        "premiere_date": date(2026, 3, 10),
        "closing_date": date(2026, 5, 18),
    },
    # Traditional theatre, full metadata, different country.
    {
        "title": "A Doll's House",
        "slug": "a-dolls-house",
        "description": "A fictional example staging of Ibsen's play, used as seed data.",
        "work_title": "A Doll's House",
        "creator_names": "Henrik Ibsen",
        "company_name": "Example Repertory Theatre",
        "director_name": "Sample Director",
        "venue_name": "Example Playhouse",
        "city": "London",
        "country_code": "GB",
        "premiere_date": date(2026, 1, 15),
        "closing_date": date(2026, 3, 1),
    },
    # Traditional theatre, adaptation with an original title.
    {
        "title": "Chalk Circles",
        "slug": "chalk-circles",
        "description": None,
        "work_title": "The Caucasian Chalk Circle",
        "creator_names": "Bertolt Brecht",
        "company_name": "Example Touring Company",
        "director_name": "Sample Director",
        "venue_name": "Example Civic Theatre",
        "city": "Sydney",
        "country_code": "AU",
        "premiere_date": date(2026, 6, 4),
        "closing_date": date(2026, 6, 28),
    },
    # Traditional theatre, well-known text, still running (no closing date).
    {
        "title": "Waiting for Godot",
        "slug": "waiting-for-godot",
        "description": None,
        "work_title": "Waiting for Godot",
        "creator_names": "Samuel Beckett",
        "company_name": "Example Stage Company",
        "director_name": "Sample Director",
        "venue_name": "Example Abbey Hall",
        "city": "Dublin",
        "country_code": "IE",
        "premiere_date": date(2026, 4, 2),
        "closing_date": None,
    },
    # Stand-up, with venue, single fixed run.
    {
        "title": "Solo Stand-Up Hour",
        "slug": "solo-stand-up-hour",
        "description": "An example stand-up comedy set, used as seed data.",
        "work_title": None,
        "creator_names": "Sample Comedian",
        "company_name": None,
        "director_name": None,
        "venue_name": "Example Comedy Club",
        "city": "Berlin",
        "country_code": "DE",
        "premiere_date": date(2026, 2, 20),
        "closing_date": None,
    },
    # Stand-up, multiple comedians, both dates known.
    {
        "title": "Late Night Laughs: An Evening of Stand-Up",
        "slug": "late-night-laughs",
        "description": None,
        "work_title": None,
        "creator_names": "Example Comedians Collective",
        "company_name": None,
        "director_name": None,
        "venue_name": "Example Downtown Club",
        "city": "New York",
        "country_code": "US",
        "premiere_date": date(2026, 7, 1),
        "closing_date": date(2026, 7, 3),
    },
    # Improv, no venue, no dates, ensemble-created.
    {
        "title": "Impro Night Berlin",
        "slug": "impro-night-berlin",
        "description": "An example recurring improv night, used as seed data.",
        "work_title": None,
        "creator_names": "Created by the ensemble",
        "company_name": "Example Improv Collective",
        "director_name": None,
        "venue_name": None,
        "city": "Berlin",
        "country_code": "DE",
        "premiere_date": None,
        "closing_date": None,
    },
    # Improv, with venue, no dates.
    {
        "title": "Impro Jam Session",
        "slug": "impro-jam-session",
        "description": None,
        "work_title": None,
        "creator_names": "Created by the ensemble",
        "company_name": "Example Improv Collective",
        "director_name": None,
        "venue_name": "Example Rehearsal Loft",
        "city": "Toronto",
        "country_code": "CA",
        "premiere_date": None,
        "closing_date": None,
    },
    # Devised theatre, no source work, open-ended run.
    {
        "title": "Six Objects, One Room",
        "slug": "six-objects-one-room",
        "description": "An example devised theatre piece, used as seed data.",
        "work_title": None,
        "creator_names": "Created by the ensemble",
        "company_name": "Example Devised Theatre Collective",
        "director_name": None,
        "venue_name": "Example Black Box Studio",
        "city": "London",
        "country_code": "GB",
        "premiere_date": date(2026, 5, 5),
        "closing_date": None,
    },
    # Devised theatre, original work, single director credited.
    {
        "title": "Nocturne: An Original Work",
        "slug": "nocturne-an-original-work",
        "description": None,
        "work_title": None,
        "creator_names": "Example Ensemble",
        "company_name": None,
        "director_name": "Sample Director",
        "venue_name": "Example Studio Theatre",
        "city": "New York",
        "country_code": "US",
        "premiere_date": date(2026, 9, 12),
        "closing_date": None,
    },
    # Performance art / dance, full metadata.
    {
        "title": "Bodies in Transit",
        "slug": "bodies-in-transit",
        "description": "An example dance/performance-art piece, used as seed data.",
        "work_title": None,
        "creator_names": "Sample Choreographer",
        "company_name": "Example Dance Company",
        "director_name": None,
        "venue_name": "Example Arts Centre",
        "city": "Paris",
        "country_code": "FR",
        "premiere_date": date(2026, 10, 1),
        "closing_date": date(2026, 10, 10),
    },
    # Performance art, venue known, no dates.
    {
        "title": "Silent Hours",
        "slug": "silent-hours",
        "description": None,
        "work_title": None,
        "creator_names": "Sample Performance Artist",
        "company_name": None,
        "director_name": None,
        "venue_name": "Example Gallery Space",
        "city": "Tokyo",
        "country_code": "JP",
        "premiere_date": None,
        "closing_date": None,
    },
    # Fully undated, unlocated, touring production.
    {
        "title": "Traveling Light: A Devised Piece",
        "slug": "traveling-light",
        "description": "An example touring devised piece with no fixed venue, used as seed data.",
        "work_title": None,
        "creator_names": "Example Ensemble",
        "company_name": None,
        "director_name": None,
        "venue_name": None,
        "city": None,
        "country_code": None,
        "premiere_date": None,
        "closing_date": None,
    },
    # Cabaret/performance, company known, no director, no dates.
    {
        "title": "Midnight Cabaret",
        "slug": "midnight-cabaret",
        "description": None,
        "work_title": None,
        "creator_names": None,
        "company_name": "Example Cabaret Company",
        "director_name": None,
        "venue_name": "Example Nightclub",
        "city": "Berlin",
        "country_code": "DE",
        "premiere_date": None,
        "closing_date": None,
    },
]


async def seed() -> None:
    created = 0
    skipped = 0

    async with async_session_factory() as session:
        for data in SEED_PRODUCTIONS:
            existing = await session.execute(
                select(Production.id).where(Production.slug == data["slug"])
            )
            if existing.scalar_one_or_none() is not None:
                skipped += 1
                continue

            session.add(Production(**data))
            created += 1

        await session.commit()

    print(f"Seed complete: {created} created, {skipped} already present (skipped).")


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
