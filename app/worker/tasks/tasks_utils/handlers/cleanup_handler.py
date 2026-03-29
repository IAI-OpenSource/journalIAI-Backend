"""Handler pour le nettoyage des ressources."""

import os
import shutil
from logging import getLogger
from typing import Callable, List

logger = getLogger(__name__)


class CleanupHandler:
    """
    Handler pour gérer le nettoyage des ressources temporaires.
    
    Permet d'enregistrer des ressources à nettoyer et les nettoie dans l'ordre inverse.
    """

    def __init__(self):
        """Initialise le handler de nettoyage."""
        self.cleanup_functions: List[Callable[[], None]] = []
        self.logger = logger

    def register_file(self, file_path: str) -> None:
        """
        Enregistre un fichier à supprimer.
        
        Args:
            file_path: Chemin du fichier à supprimer.
        """
        if file_path:
            self.register_cleanup(lambda: self._remove_file(file_path))

    def register_directory(self, dir_path: str) -> None:
        """
        Enregistre un répertoire à supprimer.
        
        Args:
            dir_path: Chemin du répertoire à supprimer.
        """
        if dir_path:
            self.register_cleanup(lambda: self._remove_directory(dir_path))

    def register_cleanup(self, cleanup_func: Callable[[], None]) -> None:
        """
        Enregistre une fonction de nettoyage personnalisée.
        
        Args:
            cleanup_func: Fonction à exécuter pour nettoyer une ressource.
        """
        self.cleanup_functions.append(cleanup_func)

    async def cleanup_all(self) -> None:
        """
        Exécute toutes les fonctions de nettoyage enregistrées.
        
        Exécute les nettoyages dans l'ordre inverse de l'enregistrement (LIFO).
        Continue même en cas d'erreur pour nettoyer toutes les ressources.
        """
        for cleanup_func in reversed(self.cleanup_functions):
            try:
                cleanup_func()
            except Exception as e:
                self.logger.error(
                    f"Erreur lors du nettoyage : {e.__class__.__name__}: {e}"
                )

    @staticmethod
    def _remove_file(file_path: str) -> None:
        """Supprime un fichier en toute sécurité."""
        try:
            if os.path.exists(file_path) and os.path.isfile(file_path):
                os.remove(file_path)
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du fichier {file_path}: {e}")

    @staticmethod
    def _remove_directory(dir_path: str) -> None:
        """Supprime un répertoire en toute sécurité."""
        try:
            if os.path.exists(dir_path) and os.path.isdir(dir_path):
                shutil.rmtree(dir_path)
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du répertoire {dir_path}: {e}")

