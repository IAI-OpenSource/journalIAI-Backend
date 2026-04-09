"""
Tâche Celery pour traiter l'upload d'une story.
Gère le traitement d'un seul média (image ou vidéo) avec compression et upload.
"""

from logging import getLogger
from uuid import UUID

from celery import shared_task
from minio.datatypes import Object

from app.cache.helpers.base import cache_manager
from app.cache.story_cache import StoryCache
from app.db.models.stories import Story
from app.db.models.story_groups import StoryGroups
from app.globals.others_constants import OtherConstants
from app.repositories import CRUDResult
from app.schemas.story_upload_schemas import CreateStoryUploadIntentFullData
from app.storage.minio_config import BucketName
from app.worker.tasks.async_loop_manager import task_async_loop_manager
from app.worker.tasks.tasks_utils.base import ProcessingContext, ProcessingStep, ProcessingResult
from app.worker.tasks.tasks_utils.handlers import CleanupHandler, ProgressHandler
from app.worker.tasks.tasks_utils.medias_process_helper import MediasProcessHelper
from app.worker.tasks.tasks_utils.minio import MinIOManager
from app.worker.tasks.workers_task_names import WorkersTaskNames

logger = getLogger(__name__)


@shared_task(name=WorkersTaskNames.PROCESS_STORY_UPLOAD, queue=OtherConstants.MEDIA_PROCESSING_WORKER_QUEUE_NAME)
def process_story_upload_task(
    intent_id: str,
    user_id: str,
    story_data: str
) -> None:
    """
    Tâche pour traiter un seul média d'une story et l'ajouter en BD.

    Args:
        user_id: ID de l'utilisateur propriétaire
        intent_id: ID de l'intent d'upload
        story_data: JSON string contenant les données de la story
    """

    def send_error_to_user(error: str) -> None:
        """Envoie un message d'erreur au client via le stream de progression."""
        try:
            task_async_loop_manager.run_async(progress_handler.error(error))
        except Exception as ee:
            logger.error(f"Erreur {ee.__class__.__name__} lors de l'envoi du message d'erreur pour {intent_id}: {ee}")

    try:
        story_data_obj: CreateStoryUploadIntentFullData = CreateStoryUploadIntentFullData.model_validate_json(story_data)
    except Exception as e:
        logger.error(f"Erreur validation JSON du story_data pour intent {intent_id}: {e}")
        return

    redis_cache = cache_manager.get_redis_connection_from_pool()
    upload_cache = StoryCache(redis_cache)

    # Créer un contexte compatible avec ProcessingContext (utilisant upload_cache qui accepte StoryCache)
    context = ProcessingContext(
        user_id=user_id,
        intent_id=intent_id,
        post_data=story_data_obj,
        cache=redis_cache,
        upload_cache=upload_cache,
    )

    progress_handler = ProgressHandler(context)
    helper = MediasProcessHelper(progress_handler, intent_id, logger)
    cleanup_handler = CleanupHandler()
    cleanup_handler.register_many_files(context.get_all_raw_paths())
    cleanup_handler.register_many_directories(context.get_all_processed_dirs_paths())

    current_step = ProcessingStep.VERIFICATION
    downloaded_file: Object | None = None
    uploaded_files_to_cleanup: list[tuple[str, str]] = []  # [(bucket_name, object_path), ...]

    try:
        file = story_data_obj.file

        down_res = helper.verify_file_existing_and_download(
            step=current_step,
            local_raw_path=context.get_local_raw_path(file.file_name),
            media_progress_weight=1.0,
            file_info=file
        )

        if down_res.is_error():
            send_error_to_user(down_res.error)
            return

        downloaded_file = down_res.data

        current_step = ProcessingStep.COMPRESSING

        compress_res: ProcessingResult[tuple[str | None, int, int, int | None ]] = helper.compress_file(
            step=current_step,
            local_raw_path=context.get_local_raw_path(file.file_name),
            media_progress_weight=1.0,
            file_info=file,
            output_dir=context.get_local_processed_dir(file.file_name),
            is_story=True
        )

        if compress_res.is_error():
            send_error_to_user(compress_res.error)
            return

        local_thumbnail_path, height, width, duration = compress_res.data


        current_step = ProcessingStep.CREATING

        upload_res = helper.upload_files_to_minio(
            step=current_step,
            file_info=file,
            media_progress_weight=1.0,
            output_dir=context.get_local_processed_dir(file.file_name),
            thumbnail_path=local_thumbnail_path,
            is_story=True
        )

        if upload_res.is_error():
            send_error_to_user(upload_res.error)
            return

        media_url, thumbnail_url = upload_res.data

        if media_url:
            uploaded_files_to_cleanup.append((BucketName.STORIES_EPHEMERAL_CONTENT.value, media_url))
        if thumbnail_url:
            uploaded_files_to_cleanup.append((BucketName.USER_IDENTITY_ASSETS.value, thumbnail_url))


        # Récupérer ou créer le groupe de stories
        story_group_res = task_async_loop_manager.run_async(
            _get_or_create_story_group(UUID(user_id))
        )

        if story_group_res.is_error():
            send_error_to_user(story_group_res.error)
            return

        story_group_object = story_group_res.data

        # Créer l'objet Story
        story_object = Story(
            author_id=UUID(user_id),
            group_id=story_group_object.id,
            club_id=story_data_obj.club_id,
            target_classe_id=story_data_obj.target_classe_id,
            media_url=media_url,
            media_type=file.media_type,
            thumbnail_url=thumbnail_url,
            legend=story_data_obj.legend,
            file_size=downloaded_file.size if downloaded_file else None,
            width=width,
            height=height,
            duration_seconds=duration,
            expires_at=story_group_object.expires_at
        )


        db_result = task_async_loop_manager.run_async(
            _save_story_to_database(story_object)
        )

        if db_result.is_error():
            send_error_to_user(db_result.error)
            return


        task_async_loop_manager.run_async(progress_handler.complete())

        logger.info(f"Traitement de la story terminé avec succès pour l'intent {intent_id}")

    except Exception as e:
        error_msg = f"Exception {e.__class__.__name__} lors du traitement de la story {intent_id}: {e}"
        logger.exception(error_msg)
        task_async_loop_manager.run_async(progress_handler.error())


    finally:

        # Nettoyage des fichiers locaux
        cleanup_handler.cleanup_all()

        if downloaded_file:
            MinIOManager.delete_file(BucketName.STORIES_EPHEMERAL_CONTENT.value, downloaded_file.object_name)

        task_async_loop_manager.run_async(redis_cache.close())

async def _get_or_create_story_group(user_id: UUID) -> CRUDResult[StoryGroups]:
    """
    Récupère ou crée le groupe actif de stories pour un utilisateur.

    Args:
        user_id: ID de l'utilisateur

    Returns:
        CRUDResult avec le groupe de stories
    """
    from app.repositories.story_repository import StoryRepository
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        repo = StoryRepository(db)
        result = await repo.get_or_create_active_story_group(user_id)
        return result


async def _save_story_to_database(story: Story) -> ProcessingResult[Story]:
    """
    Sauvegarde une story en base de données.

    Args:
        story: Objet Story à sauvegarder

    Returns:
    """
    from app.repositories.story_repository import StoryRepository
    from app.db.session import AsyncSessionLocal

    try:
        async with AsyncSessionLocal() as db:
            repo = StoryRepository(db)
            result = await repo.save_story(story)
            if result.is_error():
                return ProcessingResult.error_response(result.error)
            return ProcessingResult.ok_response(result.data)
    except Exception as e:
        error_msg = f"Exception {e.__class__.__name__} lors de la sauvegarde de la story : {e}"
        logger.error(error_msg)
        return ProcessingResult.error_response("Erreur lors de la sauvegarde de la story en base de données")



