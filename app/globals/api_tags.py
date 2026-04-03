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
    JETON_ENREGISTREMENT: str = "Routes pour les jetons"
    ADMIN_MODERATEUR: str = "Routes ADMIN ou MODERATEUR"
    ALL_USERS: str = "Routes pour tous les utilisateurs"
    EVENT: str = "Routes events"
    CLUB_MEMBER : str = "Routes Club members"
    ACADEMIC_YEAR: str = "Routes années académiques"
    CLASSE: str = "Routes classes"
    USER: str = "Route utilisateurs"

