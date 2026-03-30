## fichier contenant le service/logique métier des posts
## vous y trouverez les appels aux repositories (DB + Storage)

import logging
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.globals.status_codes import StatusCode
from app.globals.messages import Messages as msg
from app.repositories.post_repository import PostRepository
from app.storage.post_storage_repository import PostStorageRepository ## TODO : repositary à implementer 
from app.storage.minio_config import BucketName
from app.schemas.post_schemas import (
    CreatePost,
    UpdatePost,
    ConfirmMediaUpload,
    ReadPost,
    ReadPostList,
    ReadPostMedia,
    PresignedUploadUrlResponse,
)
from app.db.models.enums import MediaType
from app.worker.tasks.media_tasks import task_process_media

from . import ServiceResult

logger = logging.getLogger(__name__)


class PostService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.post_repo = PostRepository(self.db)
        self.storage_repo = PostStorageRepository()

    # Création d'un post

    async def service_create_post(
        self,
        author_id: UUID,
        academic_year_id: UUID,
        post_data: CreatePost,
    ) -> ServiceResult[ReadPost]:
        """Crée un post en base de données.

        author_id et academic_year_id sont injectés depuis le token JWT
        et le contexte académique actif — jamais depuis le body client.
        """
        result = await self.post_repo.insert_post(
            author_id=author_id,
            academic_year_id=academic_year_id,
            post_data=post_data,
        )

        if result.is_error():
            logger.error("Erreur création post : %s", result.error)
            return ServiceResult.service_error(
                message=result.error,
                status_code=result.status_code,
                service_name=msg.POST_SERVICE,
            )

        post_read = ReadPost.model_validate(result.data)
        return ServiceResult.service_success(
            data=post_read,
            status_code=result.status_code,
        )

    # Récupération d'un post par ID

    async def service_get_post(self, post_id: UUID) -> ServiceResult[ReadPost]:
        """Récupère un post par son ID avec ses médias."""
        result = await self.post_repo.get_post_by_id(post_id=post_id)

        if result.is_error():
            logger.error("Erreur récupération post id=%s : %s", post_id, result.error)
            return ServiceResult.service_error(
                message=result.error,
                status_code=result.status_code,
                service_name=msg.POST_SERVICE,
            )

        post_read = ReadPost.model_validate(result.data)
        return ServiceResult.service_success(
            data=post_read,
            status_code=result.status_code,
        )

    # Feed paginé


    async def service_get_feed(
        self,
        user_id: UUID,
        academic_year_id: UUID,
        cursor: str | None = None,
        page_size: int = 20,
    ) -> ServiceResult[ReadPostList]:
        """Retourne une page du feed (cursor-based pagination)."""
        
        seen_post_ids = await self.feed_cache.get_seen_post_ids(user_id=user_id)
        if seen_post_ids is None:
            logger.warning(
                "Redis indisponible — fallback PostgreSQL user=%s", user_id
            )
            fallback = await self.post_repo.get_seen_post_ids_from_db(user_id=user_id)
            # Si PostgreSQL aussi en erreur → feed sans exclusion (dégradé fonctionnel)
            seen_post_ids = fallback.data if not fallback.is_error() else []
            
        result = await self.post_repo.get_feed(
            academic_year_id=academic_year_id,
            seen_post_ids=seen_post_ids,
            cursor=cursor,
            page_size=page_size,
        )    
        
        if result.is_error():
            logger.error("Erreur récupération feed : %s", result.error)
            return ServiceResult.service_error(
                message=result.error,
                status_code=result.status_code,
                service_name=msg.POST_SERVICE,
            )
        items = result.data["items"]
        
        if items:
            await self.feed_cache.mark_posts_as_seen(
                user_id=user_id,
                post_ids=[post.id for post in items],
            )  

        feed = ReadPostList(
            items=[ReadPost.model_validate(p) for p in items],
            next_cursor=result.data["next_cursor"],
            has_more=result.data["has_more"],
        )
        return ServiceResult.service_success(
            data=feed,
            status_code=result.status_code,
        )

    # Demande d'URL d'upload (étape 1)
    
    async def service_count_new_posts(
        self,
        academic_year_id: UUID,
        since: datetime,
    ) -> ServiceResult[dict]:
        """COUNT(*) posts créés depuis `since`. Appelé toutes les 60s.
 
        Retourne {"new_count": N}.
        Requête ultra-légère utilisant l'index sur created_at.
        """
        result = await self.post_repo.count_new_posts_since(
            academic_year_id=academic_year_id,
            since=since,
        )
        if result.is_error():
            return ServiceResult.service_error(
                message=result.error,
                status_code=result.status_code,
                service_name=msg.POST_SERVICE,
            )
        return ServiceResult.service_success(
            data={"new_count": result.data},
            status_code=result.status_code,)

    async def service_request_upload_url(
        self,
        post_id: UUID,
        filename: str,
        media_type: MediaType,
    ) -> ServiceResult[PresignedUploadUrlResponse]:
        """Génère une presigned PUT URL pour que le client uploade
        directement sur MinIO (posts-raw-uploads).

        Utilise _public_client via PostStorageRepository pour que
        l'URL générée soit accessible depuis le mobile/web du client.
        """
        try:
            presigned = await self.storage_repo.generate_upload_url(
                post_id=post_id,
                filename=filename,
                media_type=media_type,
            )
            return ServiceResult.service_success(
                data=presigned,
                status_code=StatusCode._200_STATUS_SUCCESS.value,
            )
        except Exception as e:
            logger.error("Erreur génération URL upload : %s", e)
            return ServiceResult.service_error(
                message=msg.STORAGE_ERROR,
                status_code=StatusCode._500_STATUS_INTERNAL_SERVER_ERROR.value,
                service_name=msg.POST_SERVICE,
            )

    # Confirmation d'upload (étape 3) + déclenchement worker

    async def service_confirm_media_upload(
        self,
        post_id: UUID,
        media_data: ConfirmMediaUpload,
    ) -> ServiceResult[ReadPostMedia]:
        """Confirme qu'un upload MinIO a réussi et crée l'entrée PostMedia.

        Vérifie d'abord que l'objet existe vraiment dans MinIO
        (évite les entrées DB orphelines si le client ment).
        Puis déclenche le worker Celery pour la conversion WebP.
        """

        # 1. Vérification existence dans MinIO avant création DB
        exists = await self.storage_repo.object_exists(
            bucket=media_data.source_bucket,
            object_key=media_data.object_key,
        )

        if not exists:
            logger.error(
                "Objet introuvable dans MinIO bucket=%s key=%s",
                media_data.source_bucket,
                media_data.object_key,
            )
            return ServiceResult.service_error(
                message=msg.MEDIA_NOT_FOUND_IN_STORAGE,
                status_code=StatusCode._404_STATUS_NOT_FOUND.value,
                service_name=msg.POST_SERVICE,
            )

        # 2. Création de l'entrée PostMedia en base (is_processed=False)
        result = await self.post_repo.insert_post_media(
            post_id=post_id,
            media_data=media_data,
        )

        if result.is_error():
            logger.error("Erreur création PostMedia : %s", result.error)
            return ServiceResult.service_error(
                message=result.error,
                status_code=result.status_code,
                service_name=msg.POST_SERVICE,
            )

        media_read = ReadPostMedia.model_validate(result.data)

        # 3. Déclenchement asynchrone du worker Celery
        # Le worker convertira l'image en WebP, génèrera le thumbnail
        # et appellera mark_media_as_processed() pour mettre is_processed=True
        if media_data.media_type == MediaType.IMAGE:
            task_process_media.delay(
                media_id=str(media_read.id),
                post_id=str(post_id),
                raw_key=media_data.object_key,
                media_type=media_data.media_type.value,
            )
            logger.info(
                "Worker de conversion déclenché pour media_id=%s", media_read.id
            )

        return ServiceResult.service_success(
            data=media_read,
            status_code=result.status_code,
        )

    # Enregistrement d'une vue

    async def service_record_view(
        self, post_id: UUID, user_id: UUID
    ) -> ServiceResult[None]:
        """Enregistre la vue d'un post — opération idempotente."""
        result = await self.post_repo.insert_post_view(
            post_id=post_id,
            user_id=user_id,
        )

        if result.is_error():
            logger.error("Erreur enregistrement vue : %s", result.error)
            return ServiceResult.service_error(
                message=result.error,
                status_code=result.status_code,
                service_name=msg.POST_SERVICE,
            )

        return ServiceResult.service_success(
            data=None,
            status_code=result.status_code,
        )
