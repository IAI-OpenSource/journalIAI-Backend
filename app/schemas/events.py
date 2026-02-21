from uuid import UUID
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field



#Les status des evenements

class EventStatus(str, Enum):
  DRAFT = "DRAFT"
  PUBLISHED = "PUBLISHED"
  CANCELLED = "CANCELED"
  ARCHIVED = "ARCHIVED"

#Base des shemas
class EventBase(BaseModel):
  title : str = Field(..., max_length=255)
  slug  : str = Field(..., max_length=255)
  description : Optional[str]  = None
  location : Optional[str]  = Field(None, max_length=255)
  start_date : datetime
  end_date : Optional[datetime] = None
  cover_image_url : Optional[str]  = Field(None, max_length=500)
  organizer_club_id : Optional[UUID] = None
  status : EventStatus    = EventStatus.DRAFT
  parent_event_id : Optional[UUID] = None



#Creation des evenements
class EventCreate(EventBase):
  pass

#Modificaton des evenements (Put et Pacth)
class EventUpdate(BaseModel):
  title : Optional[str] = Field(None, max_length=255)
  slug : Optional[str] = Field(None, max_length=255)
  description :Optional[str] = None
  location : Optional[str] = Field(None, max_length=255)
  start_date : Optional[datetime] = None
  end_date : Optional[datetime] = None
  cover_image_url : Optional[str]  = Field(None, max_length=500)
  organizer_club_id : Optional[UUID] = None
  status : Optional[EventStatus] = None
  parent_event_id : Optional[UUID] = None


#Pour tous les details de l'evenement 
class EventRead(EventBase):
    id : UUID
    deleted_at : Optional[datetime] = None
    created_at : datetime
    updated_at : datetime
    published_at : Optional[datetime] = None

    model_config = {"from_attributes": True}



#Juste les informations minimum de l'evenement
class EventSummary(BaseModel):
    id         : UUID
    title      : str
    slug       : str
    status     : EventStatus
    start_date : datetime
    location   : Optional[str] = None
    cover_image_url : Optional[str] = None

    model_config = {"from_attributes": True}    