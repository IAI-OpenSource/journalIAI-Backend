import secrets
from logging import getLogger
from time import time

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status, WebSocket, WebSocketDisconnect

from app.cache.helpers.base import CacheWrapper
from app.cache.uploads_cache import VideoUploadsCache
from app.globals.messages import Messages
from app.schemas.upload_schemas import CreateVideoUploadIntent, UploadURLSchema, VideoUploadCompleteSchema, \
    WsPostProcessingInfoSchema, WsPostProcessingInfoSchemaSteps
from app.services import ServiceResult

from app.storage.post_video_storage import PostVideoStorage
from app.worker.celery_app import celery_app
from app.worker.tasks.workers_task_names import WorkersTaskNames

logger = getLogger(__name__)


def generate_random_intent_id(longueur: int) -> str:
    """Genere un ID unique pour un intent d'upload video."""
    return secrets.token_hex(longueur)

class VideoUploadsService:

    def __init__(self, cache: CacheWrapper, bd: AsyncSession):
        self._cache = VideoUploadsCache(cache)
        self._bd = bd

    async def service_process_video_upload_intent(
        self, user_id: str, intent_data: CreateVideoUploadIntent
    ) -> ServiceResult[UploadURLSchema]:
        """
        Logique métier pour process un intent d'upload video
        Args:
            user_id: Id de l'utilisateur
            intent_data: Le données de l'intent d'upload à enregistrer, conformes au schéma CreateVideoUploadIntent

        Returns:
            ServiceResult indiquant le succès ou l'échec de l'opération, avec un message approprié
        """
        random_intent_id = generate_random_intent_id(16)

        upload_url = PostVideoStorage.get_video_upload_intent_presigned_upload_url(random_intent_id,
                                                                                   intent_data.file_name)

        if not upload_url:
            logger.error("Erreur lors de la génération de l'URL d'upload pour l'intent d'upload video")
            return ServiceResult.service_error(message=Messages.ERROR_UPLOAD_URL_GENERATION, status_code=500)

        logger.info(f"URL d'upload générée avec succès pour l'intent d'upload video générée avec succès")

        await self._cache.save_video_upload_intent(user_id, random_intent_id, intent_data)

        data_to_return = UploadURLSchema(upload_url=upload_url, intent_id=random_intent_id)

        return ServiceResult.service_success(data=data_to_return)

    async def service_verify_complete_video_upload(self, user_id: str, intent_id: str) -> ServiceResult[VideoUploadCompleteSchema]:
        """
        Logique métier pour finaliser un upload de vidéo et lancer une tache de traitement dans le worker
        Args:
            user_id: Id de l'utilisateur
            intent_id: Id de l'intent d'upload video
        Returns:
            ServiceResult indiquant le succès ou l'échec de l'opération, avec un message approprié
        """
        intent_data = await self._cache.get_video_upload_intent(user_id, intent_id)

        if not intent_data:
            return ServiceResult.service_error(message=Messages.ERROR_VIDEO_UPLOAD_INTENT_NOT_FOUND, status_code=status.HTTP_404_NOT_FOUND)

        intent_file_metadata = PostVideoStorage.get_video_upload_intent_file_info(intent_id, intent_data.file_name)

        if not intent_file_metadata:
            return ServiceResult.service_error(message=Messages.ERROR_VIDEO_UPLOAD_INTENT_NOT_FOUND, status_code=status.HTTP_404_NOT_FOUND)

        await self._cache.add_upload_event_in_a_stream(
            user_id=user_id,
            intent_id=intent_id,
            data=WsPostProcessingInfoSchema(
                step=WsPostProcessingInfoSchemaSteps.PROCESSING,
                progress=0,
                timestamp=time(),
                error_message=None
            )
        )

        celery_app.send_task(
            name=WorkersTaskNames.PROCESS_VIDEO,
            kwargs={
                "raw_object": intent_file_metadata,
                "intent_id": intent_id
            }
        )

        return ServiceResult.service_success(
            data=VideoUploadCompleteSchema(
                job_id=intent_id
            )
        )

    async def listen_video_processing_intent(self, user_id: str, intent_id: str, ws: WebSocket) -> ServiceResult[None]:
        """
        Suis l'avancée d'un intent d'upload video en écoutant les messages de progression du post-traitement de la
        vidéo dans le cache, et retourne les infos de progression à l'utilisateur via le websocket
        Args:
            user_id: Id de l'utilisateur
            intent_id: Id de l'intent d'upload video
            ws: Websocket de suivi

        Returns:
            Jsp encore
        """
        verification = self._cache.verify_a_upload_is_in_processing(user_id, intent_id)

        try:
            if not verification:
                logger.info(f"Aucun upload en cours de post-traitement trouvé pour l'intent d'upload video avec id {intent_id} et user_id {user_id}")
                await ws.send_json(
                    WsPostProcessingInfoSchema(
                        progress=0,
                        step=WsPostProcessingInfoSchemaSteps.UNKNOWN,
                        timestamp=0,
                        error_message=Messages.ERROR_VIDEO_UPLOAD_INTENT_NOT_FOUND
                    ).model_dump_json()
                )
                await ws.close()
                return ServiceResult.service_error(message=Messages.ERROR_VIDEO_UPLOAD_INTENT_NOT_FOUND, status_code=status.HTTP_404_NOT_FOUND)

            last_id = None
            MAX_WAIT_ATEMPT = 10
            attempts = 0

            while True:
                res = await self._cache.read_upload_progress_event_in_a_stream(user_id, intent_id, last_id)

                if res[0] is None:
                    logger.debug(f"Aucun nouvel événement de progression trouvé pour l'intent d'upload video avec id {intent_id} et user_id {user_id}, tentative {attempts+1}/{MAX_WAIT_ATEMPT}")
                    if attempts >= MAX_WAIT_ATEMPT:
                        logger.error(f"Nombre maximum de tentatives atteint pour l'intent d'upload video avec id {intent_id} et user_id {user_id}, fermeture du websocket")
                        await ws.send_json(
                            WsPostProcessingInfoSchema(
                                progress=0,
                                step=WsPostProcessingInfoSchemaSteps.UNKNOWN,
                                timestamp=0,
                                error_message=Messages.INTERNAL_SERVER_ERROR
                            ).model_dump_json()
                        )
                        return ServiceResult.service_error(message=Messages.INTERNAL_SERVER_ERROR, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

                    attempts+=1
                    continue
                logger.info(f"Nouvel événement de progression trouvé pour l'intent d'upload video avec id {intent_id} et user_id {user_id}, étape: {res[0].step}, progression: {res[0].progress}%, timestamp: {res[0].timestamp}, message d'erreur: {res[0].error_message}")

                progress_data = res[0]
                last_id = res[1]

                await ws.send_json(
                    progress_data.model_dump_json()
                )

                if progress_data.step == WsPostProcessingInfoSchemaSteps.COMPLETED or progress_data.error_message is not None:
                    logger.info(f"Traitement de l'intent d'upload video avec id {intent_id} et user_id {user_id} terminé, fermeture du websocket")
                    await ws.close()
                    return ServiceResult.service_success(None)

            logger.warning(f"Sortie de la boucle d'écoute du websocket pour l'intent d'upload video avec id {intent_id} et user_id {user_id} sans fermeture du websocket, fermeture forcée du websocket")
            await ws.close()
            return ServiceResult.service_error(message=Messages.INTERNAL_SERVER_ERROR,
                                       status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except WebSocketDisconnect:
            logger.info(f"Websocket de suivi de l'intent d'upload video avec id {intent_id} et user_id {user_id} déconnecté par le client")
        except Exception as e:
            logger.exception(f"Exception {e.__class__.__name__} lors de l'écoute du websocket de suivi de l'intent d'upload video avec id {intent_id} et user_id {user_id} : {e}", exc_info=e)
            try:
                await ws.send_json(
                    WsPostProcessingInfoSchema(
                        progress=0,
                        step=WsPostProcessingInfoSchemaSteps.UNKNOWN,
                        timestamp=0,
                        error_message=Messages.INTERNAL_SERVER_ERROR
                    ).model_dump_json()
                )
                await ws.close()
            except:
                pass
        finally:
            return ServiceResult.service_success(None)






