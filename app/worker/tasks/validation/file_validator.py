"""Validateur centralisé pour les fichiers."""

from logging import getLogger

import magic

from app.globals.messages import Messages
from app.worker.tasks.tasks_utils.base import ProcessingResult

logger = getLogger(__name__)


class FileValidator:
    """
    Validateur centralisé pour les fichiers uploadés.
    
    Gère la vérification des types MIME et la validation des fichiers vidéo et image.
    """

    @staticmethod
    def validate_video(file_path: str) -> ProcessingResult[None]:
        """
        Valide qu'un fichier est bien une vidéo.
        
        Args:
            file_path: Chemin du fichier à vérifier.
            
        Returns:
            ProcessingResult(True) si valide, ProcessingResult(False, error_message) sinon.
        """
        return FileValidator._validate_mime_type(file_path, "video/")

    @staticmethod
    def validate_image(file_path: str) -> ProcessingResult[None]:
        """
        Valide qu'un fichier est bien une image.
        
        Args:
            file_path: Chemin du fichier à vérifier.
            
        Returns:
            ProcessingResult(True) si valide, ProcessingResult(False, error_message) sinon.
        """
        return FileValidator._validate_mime_type(file_path, "image/")

    @staticmethod
    def _validate_mime_type(file_path: str, expected_prefix: str) -> ProcessingResult[None]:
        """
        Valide le type MIME d'un fichier.
        
        Analyse le contenu du fichier via python-magic pour déterminer son type réel,
        indépendamment de l'extension.
        
        Args:
            file_path: Chemin du fichier à vérifier.
            expected_prefix: Préfixe MIME attendu (ex: "video/", "image/").
            
        Returns:
            ProcessingResult(True) si le MIME type correspond, ProcessingResult(False, error) sinon.
        """
        try:
            with open(file_path, "rb") as file:
                buffer_type = magic.from_buffer(file.read(2048), mime=True)
                
                if buffer_type and buffer_type.startswith(expected_prefix):
                    return ProcessingResult.ok_response(None)
                
                media_type = expected_prefix.rstrip("/").capitalize()
                error_msg = (
                    f"Le fichier n'est pas un {media_type} valide. "
                    f"Type MIME détecté: {buffer_type}. "
                    f"Veuillez envoyer un fichier {media_type} valide."
                )
                return ProcessingResult.error_response(error_msg)
                
        except FileNotFoundError:
            return ProcessingResult.error_response(f"Le fichier n'existe pas: {file_path}")
        except Exception as e:
            logger.error(f"Erreur lors de la validation du fichier: {e.__class__.__name__} : {e}")
            return ProcessingResult.error_response(Messages.INTERNAL_SERVER_ERROR)

