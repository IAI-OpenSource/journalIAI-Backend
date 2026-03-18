import secrets

def generate_code_jeton(length: int) -> str:
  """function pour générer lejeton de token"""
  code = secrets.token_hex(length // 2).upper()
  return code