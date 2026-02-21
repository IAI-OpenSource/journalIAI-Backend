from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from app.db.models.event import Event, EventStatus
from app.schemas.events import EventCreate, EventUpdate
from typing import List
from uuid import UUID
from datetime import datetime




"""
Renvoie tous les events 
"""
async def get_event(db: AsyncSession) -> List[Event]: 
    stmt = select(Event)
    result = await db.execute(stmt)
    events = result.scalars().all()
    return events

"""
Renvoie un events par son id
"""

async def get_event(db: AsyncSession, event_id: UUID):
    stmt = select(Event).where(Event.id == event_id)
    result = await db.execute(stmt)
    event_ById = result.scalar_one_or_none()
    return event_ById


"""
Renvoie un event par son status et si il n'est pas supprimer
"""
async def get_events_by_status(db: AsyncSession, status: EventStatus) -> List[Event]:
    stmt = select(Event).where(Event.status == status).where(Event.deleted_at == None).order_by(Event.start_date)
    result = await db.execute(stmt)
    events = result.scalars().all()
    return events


"""
Creation de l'event
"""
async def create_event(db: AsyncSession, data: EventCreate):
    event = Event(**data.model_dump())
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


"""
Mis a jour de l'event
"""
async def update_event(db: AsyncSession, event_id: UUID, data: EventUpdate):
    await db.execute(
        update(Event)
        .where(Event.id == event_id)
        .values(**data.model_dump(exclude_unset=True))
    )
    await db.commit()



"""
Suppression logique d'un event
"""
async def soft_delete_event(db: AsyncSession, event_id: UUID):
    await db.execute(
        update(Event)
        .where(Event.id == event_id)
        .values(deleted_at=datetime.utcnow())
    )
    await db.commit()



"""
Pagination affiche juste 10 events par page
"""
async def get_events_paginated(db: AsyncSession, skip: int = 0, limit: int = 10):
    result = await db.execute(
        select(Event)
        .where(Event.deleted_at == None)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()