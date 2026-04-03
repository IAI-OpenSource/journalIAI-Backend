from uuid import uuid4


class BucketFilesUtils:
    """
    Class pour les methodes utilitaires sur les fichiers dans le bucket Minio, comme la génération de noms d'objets
    uniques pour les fichiers vidéo bruts à uploader, en utilisant des templates de nommage
    """

    _RAW_VIDEO_UPLOAD_PATH_TEMPLATE: str = "raw_uploads/videos/{intent_id}{file_name}"

    _RAW_IMAGE_UPLOAD_PATH_TEMPLATE: str = "raw_uploads/images/{intent_id}{file_name}"

    _PROCESSED_VIDEO_UPLOAD_PATH_TEMPLATE: str = "processed-videos/{random_id}"

    _PROCESSED_IMAGES_UPLOAD_PATH_TEMPLATE: str = "processed-images/{random_id}"

    _PROCESSED_VIDEO_THUMBNAIL_PATH_TEMPLATE: str = "videos_thumb/{random_id}.webp"

    _PROCESSED_IMAGES_THUMBNAIL_PATH_TEMPLATE: str = "images_thumb/{random_id}.webp"

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
        return cls._RAW_VIDEO_UPLOAD_PATH_TEMPLATE.format(intent_id=intent_id, file_name=filename)

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
        return cls._RAW_IMAGE_UPLOAD_PATH_TEMPLATE.format(intent_id=intent_id, file_name=filename)

    @classmethod
    def generate_objects_path_for_processed_video(cls) -> str:
        """
        Genere un nom d'objet unique pour un fichier vidéo traité à uploader dans le bucket Minio
        Returns:
            Un nom d'objet unique pour le fichier vidéo traité
        """
        return cls._PROCESSED_VIDEO_UPLOAD_PATH_TEMPLATE.format(random_id=uuid4())

    @classmethod
    def generate_objects_path_for_processed_image(cls) -> str:
        """
        Genere un nom d'objet unique pour un fichier image traité à uploader dans le bucket Minio
        Returns:
            Un nom d'objet unique pour le fichier image traité
        """
        return cls._PROCESSED_IMAGES_UPLOAD_PATH_TEMPLATE.format(random_id=uuid4())

    @classmethod
    def generate_objects_path_for_video_thumbnail(cls) -> str:
        """
        Genere un nom d'objet unique pour une minia d'un fichier vidéo traité dans le bucket Minio
        Returns:
            Un nom d'objet unique pour la minia du fichier vidéo traité
        """
        return cls._PROCESSED_VIDEO_THUMBNAIL_PATH_TEMPLATE.format(random_id=uuid4())

    @classmethod
    def generate_objects_path_for_image_thumbnail(cls) -> str:
        """
        Genere un nom d'objet unique pour une minia d'un fichier image traité dans le bucket Minio
        Returns:
            Un nom d'objet unique pour la minia du fichier image traité
        """
        return cls._PROCESSED_IMAGES_THUMBNAIL_PATH_TEMPLATE.format(random_id=uuid4())