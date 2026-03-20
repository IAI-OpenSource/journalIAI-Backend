from dataclasses import dataclass


@dataclass
class ApiTags:
    """Cette classe contient les tags utilisés pour organiser les endpoints de l'API dans la documentation Swagger."""
    AUTHENTIFICATION: str = "Authentification"
    CLUB: str = "Routes clubs"
    ADMINISTRATEUR: str = "Routes Administrateur"
    ETUDIANT: str = "Routes étudiants"
    POSTS: str = "Routes Posts"
    UPLOADS: str = "Routes Uploads"

