

class BucketFilesUtils:
    """
    Class pour les methodes utilitaires sur les fichiers dans le bucket Minio, comme la génération de noms d'objets
    uniques pour les fichiers vidéo bruts à uploader, en utilisant des templates de nommage
    """

    _RAW_VIDEO_UPLOAD_PATH_TEMPLATE: str = "raw_uploads/videos/{intent_id}.{extension}"

    _RAW_IMAGE_UPLOAD_PATH_TEMPLATE: str = "raw_uploads/images/{intent_id}.{extension}"

    _PROCESSED_VIDEO_UPLOAD_PATH_TEMPLATE: str = "processed-videos/{intent_id}"

    _PROCESSED_IMAGES_UPLOAD_PATH_TEMPLATE: str = "processed-images/{intent_id}"

    _PROCESSED_VIDEO_THUMBNAIL_PATH_TEMPLATE: str = "videos_thumb/{intent_id}.webp"

    @classmethod
    def generate_object_name_for_raw_video(cls, intent_id: str, filename: str) -> str:
        """
        Génère un nom d'objet unique pour un fichier vidéo brut à uploader dans le bucket Minio
        Args:
            intent_id: Id de l'intent
            filename: Le nom du fichier vidéo à uploader, juste pour retirer l'extension de la vidéo

        Returns:
            Un nom d'objet unique pour le fichier vidéo brut
        """
        extension = filename.split(".")[-1]
        return cls._RAW_VIDEO_UPLOAD_PATH_TEMPLATE.format(intent_id=intent_id, extension=extension)

    @classmethod
    def generate_object_path_for_raw_image(cls, intent_id: str, filename: str) -> str:
        """
        Génère un nom d'objet unique pour un fichier image brut à uploader dans le bucket Minio
        Args:
            intent_id: Id de l'intent
            filename: Le nom du fichier image à uploader, juste pour retirer l'extension de l'image

        Returns:
            Un nom d'objet unique pour le fichier image brut
        """
        extension = filename.split(".")[-1]
        return cls._RAW_IMAGE_UPLOAD_PATH_TEMPLATE.format(intent_id=intent_id, extension=extension)

    @classmethod
    def generate_objects_path_for_processed_video(cls, intent_id: str) -> str:
        """
        Genere un nom d'objet unique pour un fichier vidéo traité à uploader dans le bucket Minio
        Args:
            intent_id: Id de l'intent
        Returns:
            Un nom d'objet unique pour le fichier vidéo traité
        """
        return cls._PROCESSED_VIDEO_UPLOAD_PATH_TEMPLATE.format(intent_id=intent_id)

    @classmethod
    def generate_objects_path_for_processed_image(cls, intent_id: str) -> str:
        """
        Genere un nom d'objet unique pour un fichier image traité à uploader dans le bucket Minio
        Args:
            intent_id: Id de l'intent
        Returns:
            Un nom d'objet unique pour le fichier image traité
        """
        return cls._PROCESSED_IMAGES_UPLOAD_PATH_TEMPLATE.format(intent_id=intent_id)

    @classmethod
    def generate_objects_path_for_video_thumbnail(cls, intent_id: str) -> str:
        """
        Genere un nom d'objet unique pour une minia d'un fichier vidéo traité dans le bucket Minio
        Args:
            intent_id: Id de l'intent
        Returns:
            Un nom d'objet unique pour la minia du fichier vidéo traité
        """
        return cls._PROCESSED_VIDEO_THUMBNAIL_PATH_TEMPLATE.format(intent_id=intent_id)