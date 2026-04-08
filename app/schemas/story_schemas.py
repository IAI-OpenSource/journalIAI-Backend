from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.post_upload_schemas import FileToUploadSchema


class CreateStory(BaseModel):
    """Schéma de validation pour la création d'une story"""

    legend: Optional[str] = Field(
        default=None,
        description="Légende de la story, un texte court qui accompagne le média et qui sera affiché sous celui-ci,"
                    " max 200 caractères",
        max_length=200
    )

    club_id: Optional[UUID] = Field(None, description="L'ID du club auquel la story est associée, si applicable")

    only_for_a_class: Optional[bool] = Field(
        default=None,
        description="Indique si la story doit etre limité seulement aux étudiants d'une classe précise, si `true` "
                    "la story sera visible uniquement par eux sinon la story sera visible pour tous les étudiants de "
                    "l'école. CET ATTRIBUT NE PEUT ETRE MIS A `true` QUE POUR LES DELEGUES DES SALLES, SI LE USER"
                    " N'EST PAS DELEGUE D'UNE SALLE LA REQUETE RENVERRA UNE BELLE `ERREUR 404`"
    )

    file_info: FileToUploadSchema = Field(
        ...,
        description="Les informations du fichier à uploader pour la story, incluant son nom, sa taille et son type de"
                    " média"
    )