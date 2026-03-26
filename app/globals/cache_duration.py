
from enum import Enum as enum

class CacheDurartion(int, enum):
  """Classe  enumérartion pour définir la durée(en S) des données en cache"""

  USER_DURATION = 1500 # 25 min
  SESSION_DURATION = 1200 # 20 min
  VIDEO_UPLOAD_INTENT_DURATION = 60 * 60 * 24 # Une Journée
  VIDEO_UPLOAD_PROGRESS_STREAM_DURATION = 60 * 60 * 2 # Deux heures, je supposes que le traitement ne deppassera pas 2h