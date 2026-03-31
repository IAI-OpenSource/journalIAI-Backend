## Ce fichier contient le repository de stockage MinIO pour les posts.
## Il gère les presigned URLs (upload et lecture) en s'appuyant sur
## MinioClientFactory qui distingue client interne et client public.

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from app.storage.minio_client import MinioClientFactory
from app.storage.minio_config import BucketName
from app.db.models.enums import MediaType
from app.schemas.post_schemas import (
    PresignedUploadUrlResponse,
    #ConfirmMediaUpload,
)

logger = logging.getLogger(__name__)

# Durée de validité des presigned URLs en secondes
UPLOAD_URL_TTL = 60 * 15       # 15 minutes pour uploader
READ_URL_TTL   = 60 * 60      # 1 heure pour lire/afficher


def _build_raw_key(media_type: MediaType, post_id, filename: str) -> str:
    """Construit la clé objet dans posts-raw-uploads.

    Format : images/2024/03/{post_id}/{uuid}.{ext}
    Le post_id dans la clé permet de supprimer tous les médias
    d'un post en une seule opération (remove_objects avec prefix).
    """
    prefix = date.today().strftime("%Y/%m")
    folder = "images" if media_type == MediaType.IMAGE else "videos"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"{folder}/{prefix}/{post_id}/{uuid.uuid4()}.{ext}"


def _build_permanent_key(media_type: MediaType, post_id, original_key: str) -> str:
    """Construit la clé objet dans posts-permanent-content.

    Conserve la même structure que raw mais dans le bucket permanent.
    Le worker appelera cette fonction pour déplacer le fichier traité.
    """
    # Récupère juste le nom de fichier depuis la clé raw
    filename = original_key.split("/")[-1]
    prefix = date.today().strftime("%Y/%m")
    folder = "images" if media_type == MediaType.IMAGE else "videos"
    return f"{folder}/{prefix}/{post_id}/{filename}"


@dataclass
class PostStorageRepository:
    """Repository MinIO pour les médias de posts.

    Utilise deux clients distincts de MinioClientFactory :
    - _private_client (get_backend_client) : opérations internes serveur
      (vérification existence, suppression, copy entre buckets)
    - _public_client (get_public_client) : génération de presigned URLs
      retournées au client (upload PUT, lecture GET)

    Tous les appels MinIO sont wrappés dans asyncio.to_thread() car
    la librairie minio est synchrone et ne doit pas bloquer l'event loop.
    """

    # ------------------------------------------------------------------
    # Presigned URL d'upload (étape 1 du flow)
    # ------------------------------------------------------------------

    async def generate_upload_url(
        self,
        post_id,
        filename: str,
        media_type: MediaType,
    ) -> PresignedUploadUrlResponse:
        """Génère une presigned PUT URL pour que le client uploade directement.

        Utilise _public_client pour que l'URL générée pointe vers
        MINIO_PUBLIC_URL (accessible depuis le client mobile/web)
        et non vers l'IP interne du serveur.

        Args:
            post_id: ID du post auquel sera rattaché ce média.
            filename: Nom original du fichier (ex: photo.jpg).
            media_type: IMAGE ou VIDEO.

        Returns:
            PresignedUploadUrlResponse avec upload_url et object_key.
        """
        object_key = _build_raw_key(media_type, post_id, filename)

        # _public_client génère des URLs avec MINIO_PUBLIC_URL
        # → accessibles depuis le navigateur/mobile du client
        public_client = MinioClientFactory.get_public_client()

        upload_url = await asyncio.to_thread(
            public_client.presigned_put_object,
            BucketName.POSTS_RAW_UPLOADS.value,
            object_key,
            expires=timedelta(seconds=UPLOAD_URL_TTL),
        )

        logger.info(
            "Presigned PUT URL générée pour post_id=%s key=%s", post_id, object_key
        )

        return PresignedUploadUrlResponse(
            upload_url=upload_url,
            object_key=object_key,
        )

    # ------------------------------------------------------------------
    # Presigned URL de lecture (affichage dans le feed)
    # ------------------------------------------------------------------

    async def generate_read_url(self, object_key: str) -> str:
        """Génère une presigned GET URL pour qu'un client puisse lire un média.

        Utilise _public_client pour la même raison que generate_upload_url :
        l'URL doit pointer vers MINIO_PUBLIC_URL, pas l'IP interne.

        Le bucket dépend de l'étape du média :
        - Avant traitement worker → POSTS_RAW_UPLOADS
        - Après traitement worker → POSTS_PERMANENT_CONTENT (cas normal du feed)

        Args:
            object_key: Clé objet MinIO stockée dans PostMedia.media_url.

        Returns:
            URL signée valable READ_URL_TTL secondes.
        """
        public_client = MinioClientFactory.get_public_client()

        url = await asyncio.to_thread(
            public_client.presigned_get_object,
            BucketName.POSTS_PERMANENT_CONTENT.value,
            object_key,
            expires=timedelta(seconds=READ_URL_TTL),
        )

        logger.info("Presigned GET URL générée pour key=%s", object_key)
        return url

    # ------------------------------------------------------------------
    # Vérification existence (avant confirmation d'upload)
    # ------------------------------------------------------------------

    async def object_exists(self, bucket: BucketName, object_key: str) -> bool:
        """Vérifie qu'un objet existe dans MinIO avant de créer l'entrée DB.

        Utilise _private_client : opération interne serveur → serveur,
        l'URL interne suffit.

        Args:
            bucket: Le bucket à interroger.
            object_key: La clé objet à vérifier.

        Returns:
            True si l'objet existe, False sinon.
        """
        private_client = MinioClientFactory.get_backend_client()

        try:
            await asyncio.to_thread(
                private_client.stat_object,
                bucket.value,
                object_key,
            )
            return True
        except Exception:
            # stat_object lève une exception si l'objet n'existe pas
            return False

    # ------------------------------------------------------------------
    # Suppression d'un média (soft delete post → nettoyage MinIO)
    # ------------------------------------------------------------------

    async def delete_object(self, bucket: BucketName, object_key: str) -> None:
        """Supprime un objet MinIO.

        Utilise _private_client : opération interne, jamais exposée au client.

        Args:
            bucket: Le bucket source.
            object_key: La clé objet à supprimer.
        """
        private_client = MinioClientFactory.get_backend_client()

        await asyncio.to_thread(
            private_client.remove_object,
            bucket.value,
            object_key,
        )

        logger.info("Objet supprimé bucket=%s key=%s", bucket.value, object_key)

    # ------------------------------------------------------------------
    # Déplacement raw → permanent (appelé par le worker après traitement)
    # ------------------------------------------------------------------

    async def move_to_permanent(
        self,
        raw_key: str,
        media_type: MediaType,
        post_id,
    ) -> str:
        """Copie un objet de posts-raw-uploads vers posts-permanent-content
        puis supprime l'original.

        Appelé par le worker (Celery/ARQ) après compression et génération
        du thumbnail. Retourne la clé permanente à enregistrer en DB.

        Utilise _private_client : copie serveur → serveur, jamais exposée.

        Args:
            raw_key: Clé dans posts-raw-uploads.
            media_type: IMAGE ou VIDEO (pour construire la clé permanente).
            post_id: ID du post (pour construire la clé permanente).

        Returns:
            permanent_key: Clé dans posts-permanent-content à stocker en DB.
        """
        from minio.commonconfig import CopySource

        private_client = MinioClientFactory.get_backend_client()
        permanent_key = _build_permanent_key(media_type, post_id, raw_key)

        # Copie entre buckets (serveur → serveur, pas de transit réseau client)
        await asyncio.to_thread(
            private_client.copy_object,
            BucketName.POSTS_PERMANENT_CONTENT.value,
            permanent_key,
            CopySource(BucketName.POSTS_RAW_UPLOADS.value, raw_key),
        )

        # Suppression de l'original dans raw (le lifecycle de 7j le ferait aussi,
        # mais autant libérer l'espace immédiatement)
        await self.delete_object(BucketName.POSTS_RAW_UPLOADS, raw_key)

        logger.info(
            "Fichier déplacé raw→permanent : %s → %s", raw_key, permanent_key
        )
        return permanent_key