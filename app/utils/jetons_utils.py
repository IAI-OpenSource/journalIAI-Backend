import secrets
import pandas as pd
from fastapi import UploadFile
from io import BytesIO

def generate_code_jeton(length: int) -> str:
  """function pour générer lejeton de token"""
  code = secrets.token_hex(length // 2).upper()
  return code


async def read_excel_file(file: UploadFile) -> list[dict]:
  """function pour lire un fichier excel et récupérer plusieurs etudiants"""
  content = await file.read()
  df = pd.read_excel(BytesIO(content))
  return df.to_dict(orient="records")