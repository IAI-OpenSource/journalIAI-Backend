from uuid import UUID
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.db.models.enums import EventStatus  # corrigé : vient de enums pas de event
from app.schemas import ApiBaseResponse


# ── Base ──────────────────────────────────────────────────────────────────────

class EventBase(BaseModel):
    """
    Modèle de base représentant un événement.

    Contient les champs communs utilisés par la création,
    la mise à jour et la lecture des événements.
    """
    title: str = Field(..., min_length=3, max_length=255, description="Titre de l'event")
    slug: str = Field(..., max_length=255, description="Slug de l'event")
    description: Optional[str] = Field(None, description="La description de l'event")
    location: Optional[str] = Field(None, max_length=255, description="Lieu de l'événement")
    start_date: datetime = Field(..., description="Date et heure de début de l'événement")  # corrigé : ... obligatoire
    end_date: Optional[datetime] = Field(None, description="Date et heure de fin de l'événement")
    organizer_club_id: Optional[UUID] = Field(None, description="Identifiant du club organisateur")
    parent_event_id: Optional[UUID] = Field(None, description="Identifiant de l'événement parent")


# ── Création ──────────────────────────────────────────────────────────────────

class EventCreate(EventBase):
    """
    Schéma utilisé pour la création d'un événement.

    Hérite de EventBase. Le status est géré par le modèle (défaut DRAFT),
    il n'est donc pas exposé à la création.
    """
    pass


# ── Mise à jour ───────────────────────────────────────────────────────────────

class EventUpdate(BaseModel):
    """
    Schéma utilisé pour la mise à jour partielle ou complète d'un événement.

    Tous les champs sont optionnels (PATCH / PUT).
    """
    title: Optional[str] = Field(None, max_length=255, description="Titre de l'event")
    slug: Optional[str] = Field(None, max_length=255, description="Slug de l'event")
    description: Optional[str] = Field(None, description="Description de l'événement")
    location: Optional[str] = Field(None, max_length=255, description="Lieu de l'événement")
    start_date: Optional[datetime] = Field(None, description="Date et heure de début de l'événement")
    end_date: Optional[datetime] = Field(None, description="Date et heure de fin de l'événement")
    organizer_club_id: Optional[UUID] = Field(None, description="Identifiant du club organisateur")
    status: Optional[EventStatus] = Field(None, description="Statut actuel de l'événement")  # corrigé : None par défaut pas DRAFT
    parent_event_id: Optional[UUID] = Field(None, description="Identifiant de l'événement parent")


# ── Lecture complète ──────────────────────────────────────────────────────────

class EventRead(EventBase):
    """Schéma complet de lecture d'un événement."""

    id: UUID = Field(..., description="Identifiant unique de l'événement")
    status: EventStatus = Field(..., description="Statut actuel de l'événement")  # ajouté : géré par le modèle
    deleted_at: Optional[datetime] = Field(None, description="Date de suppression (si supprimé)")
    created_at: datetime = Field(..., description="Date de création de l'événement")
    updated_at: datetime = Field(..., description="Date de dernière mise à jour")
    published_at: Optional[datetime] = Field(None, description="Date de publication (si publié)")

    model_config = {"from_attributes": True}

    def is_deleted(self) -> bool:
        return self.deleted_at is not None


# ── Résumé léger ──────────────────────────────────────────────────────────────

class EventSummary(BaseModel):
    """
    Schéma léger pour représenter un événement dans des listes.

    Contient uniquement les informations essentielles
    afin d'optimiser les performances des requêtes.
    """
    id: UUID = Field(..., description="Identifiant unique de l'événement")
    title: str = Field(..., description="Titre de l'événement")
    slug: str = Field(..., description="Slug URL-friendly de l'événement")
    status: EventStatus = Field(..., description="Statut actuel de l'événement")
    start_date: datetime = Field(..., description="Date et heure de début de l'événement")
    location: Optional[str] = Field(None, description="Lieu de l'événement")

    model_config = {"from_attributes": True}


# ── Réponses API ──────────────────────────────────────────────────────────────

class EventInfo(ApiBaseResponse):
    result: Optional[EventRead] = Field(None, description="Informations de l'événement")

class EventCarte(ApiBaseResponse):
    result: EventSummary = Field(..., description="Informations de l'événement pour carte")


class EventListReponse(BaseModel):
    events: List[EventRead]  # corrigé : List[EventRead] pas List[EventInfo]
    next_cursor: Optional[UUID] = None  # corrigé : UUID pas str, cohérent avec la pagination

class ApiEventListReponse(ApiBaseResponse):
    result: Optional[EventListReponse] = None