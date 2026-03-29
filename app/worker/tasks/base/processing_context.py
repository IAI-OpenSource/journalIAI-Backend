"""Contexte d'exécution pour le traitement des médias."""

import os
from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID

from app.cache.helpers.base import CacheWrapper
from app.cache.uploads_cache import MediaUploadsCache
from app.schemas.post_upload_schemas import CreateMediaUploadIntentFullData
from app.worker.tasks.base.processing_step import ProcessingStep


@dataclass
class ProcessingContext:
    """
    Contexte centralisé pour l'exécution du traitement d'un média.
    
    Encapsule tous les paramètres, états et ressources nécessaires au traitement,
    réduisant le nombre de paramètres à passer entre les fonctions.
    
    Attributes:
        raw_bucket_name: Bucket MinIO du fichier brut.
        raw_object_name: Nom du fichier brut dans MinIO.
        user_id: ID de l'utilisateur auteur.
        intent_id: ID de l'intent d'upload.
        post_data: Données du post à créer.
        cache: Connexion Redis pour le cache.
        upload_cache: Cache spécialisé pour les uploads.
        local_raw_path: Chemin local du fichier téléchargé.
        local_processed_dir: Répertoire de traitement local.
        global_progress_percentage: Pourcentage de progression global (0-100).
        current_step: Étape actuelle du traitement.
        error_message: Message d'erreur si applicable.
    """

    # Identifiants et données métier
    raw_bucket_name: str
    raw_object_name: str
    user_id: str
    intent_id: str
    post_data: CreateMediaUploadIntentFullData
    
    # Cache et connexions
    cache: CacheWrapper
    upload_cache: MediaUploadsCache
    
    # Chemins locaux
    local_raw_path: str = field(default="")
    local_processed_dir: str = field(default="")
    
    # État du traitement
    global_progress_percentage: int = field(default=0)
    current_step: ProcessingStep = field(default=ProcessingStep.UNKNOWN)
    error_message: Optional[str] = field(default=None)
    
    # Ressources à nettoyer
    temp_files: list[str] = field(default_factory=list)
    temp_dirs: list[str] = field(default_factory=list)

    def __post_init__(self):
        """Initialiser les chemins temporaires s'ils ne sont pas définis."""
        from uuid import uuid4
        
        if not self.local_raw_path:
            self.local_raw_path = f"/tmp/{uuid4()}_raw"
        if not self.local_processed_dir:
            self.local_processed_dir = f"/tmp/{uuid4()}_processed_files"
            os.makedirs(self.local_processed_dir, exist_ok=True)

    def register_temp_file(self, file_path: str) -> None:
        """Enregistre un fichier temporaire à nettoyer."""
        if file_path and file_path not in self.temp_files:
            self.temp_files.append(file_path)

    def register_temp_dir(self, dir_path: str) -> None:
        """Enregistre un répertoire temporaire à nettoyer."""
        if dir_path and dir_path not in self.temp_dirs:
            self.temp_dirs.append(dir_path)

    def update_progress(self, step: ProcessingStep, increment: int, error: Optional[str] = None) -> None:
        """
        Met à jour l'état de progression du traitement.
        
        Args:
            step: Nouvelle étape du traitement.
            increment: Incrément de progression (0-100).
            error: Message d'erreur si applicable.
        """
        self.current_step = step
        if error:
            self.error_message = error
        else:
            self.global_progress_percentage = min(self.global_progress_percentage + increment, 100)

    @property
    def user_id_as_uuid(self) -> UUID:
        """Récupère l'ID utilisateur en tant que UUID."""
        return UUID(self.user_id)

    @property
    def intent_id_as_uuid(self) -> UUID:
        """Récupère l'ID intent en tant que UUID."""
        return UUID(self.intent_id)

