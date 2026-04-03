"""Contexte d'exécution pour le traitement des médias."""

import os
from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID, uuid4

from app.cache.helpers.base import CacheWrapper
from app.cache.post_cache import PostCache
from app.schemas.post_upload_schemas import CreateMediaUploadIntentFullData, FileToUploadSchema
from app.worker.tasks.tasks_utils.base.processing_step import ProcessingStep

def calculate_media_progress_weight(
    medias: list[FileToUploadSchema]
) -> dict[str, float]:
    total_size = 0
    for media in medias:
        total_size += media.file_size
    media_progress_weight = {}
    for media in medias:
        media_progress_weight[media.file_name] = round(media.file_size / total_size, 4)

    return media_progress_weight

@dataclass
class ProcessingContext:
    """
    Contexte centralisé pour l'exécution du traitement d'un média.
    
    Encapsule tous les paramètres, états et ressources nécessaires au traitement,
    réduisant le nombre de paramètres à passer entre les fonctions.
    
    Attributes:
        user_id: ID de l'utilisateur auteur.
        intent_id: ID de l'intent d'upload.
        post_data: Données du post à créer.
        cache: Connexion Redis pour le cache.
        upload_cache: Cache spécialisé pour les uploads.
        global_progress_percentage: Pourcentage de progression global (0-100).
        current_step: Étape actuelle du traitement.
        error_message: Message d'erreur si applicable.
    """

    user_id: str
    intent_id: str
    post_data: CreateMediaUploadIntentFullData
    
    # Cache et connexions
    cache: CacheWrapper
    upload_cache: PostCache
    _locals_paths: dict[str, dict[str, str]] = field(default_factory=dict, init=False, repr=False)
    # État du traitement
    global_progress_percentage: int = field(default=0, init=False)
    current_step: ProcessingStep = field(default=ProcessingStep.UNKNOWN, init=False)
    error_message: Optional[str] = field(default=None, init=False)
    _progress_weight: dict[str, float] = field(default=None, init=False)

    
    # Ressources à nettoyer
    temp_files: list[str] = field(default_factory=list, init=False)
    temp_dirs: list[str] = field(default_factory=list, init=False)

    def __post_init__(self):
        """Initialiser les chemins temporaires s'ils ne sont pas définis."""

        self._progress_weight = calculate_media_progress_weight(self.post_data.files)

        for file in self.post_data.files:
            r_path = f"/tmp/{uuid4()}_raw"
            p_path = f"/tmp/{uuid4()}_processed_files"
            try:
                os.makedirs(p_path, exist_ok=True)
            except Exception as e:
                raise RuntimeError(f"Impossible de créer le répertoire temporaire {p_path}: {e}")
            
            self._locals_paths[file.file_name] = {"raw": r_path, "processed": p_path}
            self.register_temp_file(r_path)
            self.register_temp_dir(p_path)



    def get_local_raw_path(self, file_name: str) -> str:
        return self._locals_paths[file_name]["raw"]

    def get_local_processed_dir(self, file_name: str) -> str:
        return self._locals_paths[file_name]["processed"]

    def get_file_progress_weight(self, file_name: str) -> float:
        return self._progress_weight[file_name]

    def get_all_processed_dirs_paths(self) -> list[str]:
        to_return = []
        for file_name in self._locals_paths:
            to_return.append(self._locals_paths[file_name]["processed"])
        return to_return

    def get_all_raw_paths(self) -> list[str]:
        to_return = []
        for file_name in self._locals_paths:
            to_return.append(self._locals_paths[file_name]["raw"])

        return to_return
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