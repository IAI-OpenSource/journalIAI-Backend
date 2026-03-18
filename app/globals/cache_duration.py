
from enum import Enum as enum

class CacheDurartion(int, enum):
  """Classe  enumérartion pour définir la durée(en S) des données en cache"""

  USER_DURATION = 1500 # 25 min
  SESSION_DURATION = 1200 # 20 min
  EVENT_DURATION = 1500