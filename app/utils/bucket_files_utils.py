

class BucketFilesUtils:
    """
    Class pour les methodes utilitaires sur les fichiers dans le bucket Minio, comme la génération de noms d'objets
    uniques pour les fichiers vidéo bruts à uploader, en utilisant des templates de nommage
    """

    _RAW_VIDEO_UPLOAD_TEMPLATE = "raw_uploads/video/{user_id}/{filename}"

    @classmethod
    def get_object_name_for_raw_video(cls, filename: str, user_id: str) -> str:
        """
        Génère un nom d'objet unique pour un fichier vidéo brut à uploader dans le bucket Minio, en utilisant le nom du fichier et l'ID de l'utilisateur
        Args:
            filename: Le nom du fichier à uploader, incluant son extension, par exemple 'video.mp4'
            user_id: L'ID de l'utilisateur qui upload le fichier

        Returns:
            Un nom d'objet unique pour le fichier vidéo brut, par exemple 'raw_uploads/user123/video_abc123.mp4'
        """
        formatted_file_name = f"{filename.rsplit('.', 1)[0]}.{filename.split('.')[-1]}"

        return cls._RAW_VIDEO_UPLOAD_TEMPLATE.format(user_id=user_id, filename=formatted_file_name)