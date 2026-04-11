
from enum import Enum as enum

class CacheDurartion(int, enum):
  """Classe  enumérartion pour définir la durée(en S) des données en cache"""

  USER_DURATION = 1500 # 25 min
  SESSION_DURATION = 1020 # 20 min
  UPLOAD_INTENT_DURATION = 60 * 60 # 1 heure
  UPLOAD_PROGRESS_STREAM_DURATION = 60 * 60 * 2 # Deux heures, je supposes que le traitement ne deppassera pas 2h
  EVENT_DURATION = 1500
  CLUB_MEMBER_DURATION = 1500
  OTP_DURATION = 1500 # 25 min pour les tests. ca va eviter de checker chaque fois le mail. on change aprés 
  AVATAR_UPLOAD_URL = 1000
