from dataclasses import dataclass
import secrets
from typing import Any, Dict
import pandas as pd
from io import BytesIO

from pydantic import ValidationError

from app.schemas.registration_schemas import CreateMultileRegistration


## methodes utilitaires
COLUMN_MAPPING = {
    "first_name": "prenom",
    "last_name": "nom",
    "sexe": "sexe",
  }

def normalize_key(key: str) -> str:
    return key.strip().lower()


def map_row(row: dict) -> dict:
  mapped = {}

  for k, v in row.items():
      normalized = normalize_key(str(k))

      new_key = COLUMN_MAPPING.get(normalized)

      if new_key:
          mapped[new_key] = v
      else:
          #ignorer colonnes inconnues (optionnel)
          pass

  return mapped



@dataclass
class JetonUtils:
  _JETON_PREFIX = "IAI-"
  @classmethod
  def generate_code_jeton(cls, length: int) -> str:
    """function pour générer lejeton de token"""
    code = secrets.token_hex(length // 2).upper()
    return cls._JETON_PREFIX + code


  @classmethod
  async def read_excel_file(cls, file: BytesIO) -> Dict[str, Any]:
    try:

      excel_file = pd.ExcelFile(file)

      all_valid_data = []
      errors = []

      for sheet_name in excel_file.sheet_names:
        df = excel_file.parse(sheet_name)

        df.columns = [normalize_key(col) for col in df.columns]

        df = df.dropna(how="all")

        rows = df.to_dict(orient="records")

        for index, row in enumerate(rows):
          try:
            row = map_row(row)

            if not row:
                continue

            # validation Pydantic
            student = CreateMultileRegistration(**row)

            all_valid_data.append(student.model_dump())

          except ValidationError as ve:
            errors.append({
              "sheet": sheet_name,
              "row": index + 2,
              "error": ve.errors()
            })

          except Exception as e:
            errors.append({
              "sheet": sheet_name,
              "row": index + 2,
              "error": str(e)
            })

      return {
        "data": all_valid_data,
        "errors": errors,
      }

    except Exception as e:
      return Exception(f"Erreur lecture Excel: {str(e)}")