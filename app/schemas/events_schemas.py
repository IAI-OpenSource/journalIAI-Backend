from uuid import UUID
from datetime import datetime
from typing import Optional,List
from pydantic import BaseModel, Field
from db.models.enums import EventStatus
from app.schemas import ApiBaseResponse




#Les status des evenements



#Base des shemas
class EventBase(BaseModel):
  """
    Modèle de base représentant un événement.

    Contient les champs communs utilisés par la création,
    la mise à jour et la lecture des événements.

    Attributes:
        title (str): Titre de l'événement (max 255 caractères).
        slug (str): Identifiant URL-friendly de l'événement.
        description (Optional[str]): Description de l'événement.
        location (Optional[str]): Lieu de l'événement (max 255).
        start_date (datetime): Date et heure de début.
        end_date (Optional[datetime]): Date et heure de fin (optionnel).
        cover_image_url (Optional[str]): URL de l'image de couverture (max 500).
        organizer_club_id (Optional[UUID]): ID du club organisateur.
        status (EventStatus): Statut de l'événement.
        parent_event_id (Optional[UUID]): ID de l'événement parent (si sous-événement).
    """
  title : str = Field(...,min_length=3, max_length=255 , description= "Titre de l'event")
  slug  : str = Field(..., max_length=255, description= "slug de l'event"  )
  description : Optional[str]  = Field(None, description= "La description de l'event")
  location : Optional[str]  = Field(None, max_length=255,  description="Lieu de l'événement")
  start_date : datetime =  Field(None,   description="Date et heure de  debut l'événement")
  end_date : Optional[datetime] =  Field( None, description="Date et heure de fin de l'événement ")
  organizer_club_id : Optional[UUID] = Field(None, description="Identifiant du club organisateur ")
  status : EventStatus    = Field(EventStatus.DRAFT, description="Statut actuel de l'événement ")
  parent_event_id : Optional[UUID] = Field(None, description="Identifiant de l'événement parent")



#Creation des evenements
class EventCreate(EventBase):
  """
    Schéma utilisé pour la création d'un événement.

    Hérite de EventBase car tous les champs du modèle
    de base sont nécessaires lors de la création.
    """
  pass

#Modificaton des evenements (Put et Pacth)
class EventUpdate(BaseModel):
  """
    Schéma utilisé pour la mise à jour d'un événement.

    Tous les champs sont optionnels afin de permettre
    des mises à jour partielles (PATCH) ou complètes (PUT).

    Attributes:
        title (Optional[str]): Nouveau titre.
        slug (Optional[str]): Nouveau slug.
        description (Optional[str]): Nouvelle description.
        location (Optional[str]): Nouveau lieu.
        start_date (Optional[datetime]): Nouvelle date de début.
        end_date (Optional[datetime]): Nouvelle date de fin.
        cover_image_url (Optional[str]): Nouvelle image de couverture.
        organizer_club_id (Optional[UUID]): Nouveau club organisateur.
        status (Optional[EventStatus]): Nouveau statut.
        parent_event_id (Optional[UUID]): Nouvel événement parent.
    """
  title : Optional[str] = Field(None, max_length=255,description= "Titre de l'event")
  slug : Optional[str] = Field(None, max_length=255, description= "slug de l'event"  )
  description :Optional[str] = Field(None, max_length=255,  description="Lieu de l'événement")
  location : Optional[str] = Field(None, max_length=255,description="Lieu de l'événement")
  start_date : Optional[datetime] = Field(None,   description="Date et heure de  debut l'événement")
  end_date : Optional[datetime] = Field(None,   description="Date et heure de fin l'événement")
  organizer_club_id : Optional[UUID] = Field(None, description="Identifiant du club organisateur ")
  status : Optional[EventStatus]   = Field(EventStatus.DRAFT, description="Statut actuel de l'événement ")
  parent_event_id : Optional[UUID] = Field(None, description="Identifiant de l'événement parent")



#Pour tous les details de l'evenement 
class EventRead(EventBase):
    
    id: UUID = Field(..., description="Identifiant unique de l'événement ")

    deleted_at: Optional[datetime] = Field(None,description="Date de suppression de l'événement (si supprimé)")

    created_at: datetime = Field(..., description="Date de création de l'événement")

    updated_at: datetime = Field(..., description="Date de dernière mise à jour de l'événement")

    published_at: Optional[datetime] = Field(None, description="Date de publication de l'événement (si publié)")

    model_config = {"from_attributes": True}



    



#Juste les informations minimum de l'evenement
class EventSummary(BaseModel):
    """
    Schéma léger pour représenter un événement dans des listes.

    Contient uniquement les informations essentielles
    afin d'optimiser les performances des requêtes.

    Attributes:
        id (UUID): Identifiant de l'événement.
        title (str): Titre de l'événement.
        slug (str): Slug URL-friendly.
        status (EventStatus): Statut de l'événement.
        start_date (datetime): Date de début.
        location (Optional[str]): Lieu (si disponible).
        cover_image_url (Optional[str]): Image de couverture.
    """
    id: UUID = Field(..., description="Identifiant unique de l'événement")

    title: str = Field( ..., description="Titre de l'événement" )

    slug: str = Field( ...,  description="Slug URL-friendly de l'événement" )

    status: EventStatus = Field(..., description="Statut actuel de l'événement")

    start_date: datetime = Field( ..., description="Date et heure de début de l'événement" )

    location: Optional[str] = Field(None, description="Lieu de l'événement (optionnel)")

    cover_image_url: Optional[str] = Field(None , description="URL de l'image de couverture (optionnel)")

    model_config = {"from_attributes": True}    

class EventInfo(ApiBaseResponse):
  result : EventRead =  Field(description="Informations de l'evenement") 


class EventCarte(ApiBaseResponse):
   result : EventSummary = Field(description="Informations de l'evenement pour carte ")


class EventListReponse(BaseModel):
   events: List[EventInfo]
   next_cursor : Optional[str] = None