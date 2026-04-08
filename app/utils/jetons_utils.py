from dataclasses import dataclass
import secrets
import pandas as pd
from io import BytesIO

from pydantic import ValidationError

from app.globals.status_codes import StatusCode
from app.schemas.registration_schemas import CreateMultileRegistration
from app.services import ServiceResult


## methodes utilitaires
COLUMN_MAPPING = {
    "prenom": "first_name",
    "nom": "last_name",
    "sexe": "sexe",
    "email": "email"
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
  async def read_excel_file(cls, file: BytesIO) -> ServiceResult[dict[str, list]]:
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
            student.first_name = student.first_name.title()
            student.last_name = student.last_name.upper()
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

      return ServiceResult.service_success(
        data={"data": all_valid_data, "errors": errors},
        status_code=StatusCode._200_STATUS_SUCCESS.value,
        service_name="Lecture fichier"
      )

    except Exception as e:
      return ServiceResult.service_error(
        message="Erreur lors de la lecture du fichier",
        status_code=StatusCode._400_STATUS_BAD_REQUEST.value,
        service_name="Lecture fichier"
      )