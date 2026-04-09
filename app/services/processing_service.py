from logging import getLogger
from time import time
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect, status

from app.cache.helpers.base import CacheWrapper
from app.cache.processing_cache import ProcessingCache
from app.globals.messages import Messages
from app.schemas.post_upload_schemas import WsMediasProcessingInfoSchema, WsMediasProcessingInfoSchemaSteps
from app.schemas.user_schemas import ReadUser
from app.services import ServiceResult

logger = getLogger(__name__)

class ProcessingService:

    def __init__(self, cache: CacheWrapper) -> None:
        self._processing_cache = ProcessingCache(cache)

    async def service_listen_media_processing_intent(
        self, current_user: ReadUser, intent_id: str,ws: WebSocket
    ) -> None:
        """
        Suis l'avancée d'un intent d'upload de média en écoutant les messages de progression du post-traitement du
        média dans le cache, et retourne les infos de progression à l'utilisateur via le websocket
        Args:
            current_user: L'utilisateur courant
            intent_id: Id de l'intent d'upload média
            ws: Websocket de suivi

        Returns:
            Jsp encore
        """
        user_id_str = str(current_user.id)

        verification = await self._processing_cache.verify_a_upload_is_in_processing(user_id_str, intent_id)

        try:
            if not verification:
                logger.info(
                    f"Aucun upload en cours de post-traitement trouvé pour l'intent d'upload média avec id {intent_id} et user_id {user_id_str}")
                await ws.send_text(
                    WsMediasProcessingInfoSchema(
                        progress=0,
                        step=WsMediasProcessingInfoSchemaSteps.UNKNOWN,
                        timestamp=time(),
                        error_message=Messages.ERROR_MEDIA_UPLOAD_INTENT_NOT_FOUND
                    ).model_dump_json()
                )
                return

            last_id = None
            MAX_WAIT_ATEMPT = 10  # 10 minut
            attempts = 0
            has_finished = False

            while attempts < MAX_WAIT_ATEMPT and not has_finished:
                res = await self._processing_cache.read_upload_progress_event_in_a_stream(user_id_str, intent_id,
                                                                                          last_id)

                progress_data = res[0]

                if progress_data is None:
                    attempts += 1
                    logger.debug(
                        f"Aucun nouvel événement de progression trouvé pour l'intent d'upload média avec id {intent_id} et user_id {user_id_str}, tentative {attempts + 1}/{MAX_WAIT_ATEMPT}")
                    continue

                last_id = res[1]
                logger.info(
                    f"Nouvel événement de progression trouvé pour l'intent d'upload média avec id {intent_id} et user_id {user_id_str}, étape: {progress_data.step}, progression: {progress_data.progress}%, timestamp: {progress_data.timestamp}, message d'erreur: {progress_data.error_message}")

                await ws.send_json(progress_data.model_dump_json())

                if progress_data.step == WsMediasProcessingInfoSchemaSteps.COMPLETED or progress_data.error_message is not None:
                    has_finished = True
                    break

            if has_finished:
                logger.info(
                    f"Traitement de l'intent d'upload média avec id {intent_id} et user_id {user_id_str} terminé, fermeture du websocket")
                await self._processing_cache.delete_upload_progress_stream(user_id_str,
                                                                           intent_id)  # Nettoyage du stream après la fin du suivi

            else:
                logger.error(
                    f"Nombre maximum de tentatives atteint pour la lecture su stream d'upload média avec id {intent_id} et user_id {user_id_str}, fermeture du websocket")
                await ws.send_json(
                    WsMediasProcessingInfoSchema(
                        progress=0,
                        step=WsMediasProcessingInfoSchemaSteps.UNKNOWN,
                        timestamp=0,
                        error_message=Messages.INTERNAL_SERVER_ERROR
                    ).model_dump_json()
                )

        except WebSocketDisconnect:
            logger.info(
                f"Websocket de suivi de l'intent d'upload média avec id {intent_id} et user_id {user_id_str} déconnecté par le client")
            raise
        except Exception as e:
            logger.exception(
                f"Exception {e.__class__.__name__} lors de l'écoute du websocket de suivi de l'intent d'upload média avec id {intent_id} et user_id {user_id_str} : {e}",
                exc_info=e)
            try:
                await ws.send_json(
                    WsMediasProcessingInfoSchema(
                        progress=0,
                        step=WsMediasProcessingInfoSchemaSteps.UNKNOWN,
                        timestamp=0,
                        error_message=Messages.INTERNAL_SERVER_ERROR
                    ).model_dump_json()
                )
            except WebSocketDisconnect:
                return
        finally:
            try:
                await ws.close()
            except WebSocketDisconnect:
                pass


    async def send_processing_task(
        self, task_name: str, task_kwargs: dict[str, Any],
        queue_name: str, user_id: str, intent_id: str
    ) -> ServiceResult[str]:
        """
        Envoie une tâche de post-traitement de média dans le worker de traitement
        Args:
            task_name: Le nom de la tâche à envoyer
            task_kwargs: Les arguments de la tâche à envoyer
            queue_name: La queue dans laquelle lla task doit etre envoyée
            user_id: L'id de l'utilisateur pour lequel on lance la tâche, utilisé pour le suivi de la progression dans le cache
            intent_id: L'id de l'intent d'upload de média pour lequel on lance la tâche, utilisé pour le suivi de la progression dans le cache

        Returns:
            Un ServiceResult contenant l'id de la tâche envoyée en cas de succès, ou un message d'erreur en cas d'échec
        """

        try:

            await self._processing_cache.add_upload_event_in_a_stream(
                user_id=user_id, intent_id=intent_id,
                data=WsMediasProcessingInfoSchema(
                    step=WsMediasProcessingInfoSchemaSteps.IN_QUEUE,
                    progress=0,
                    timestamp=time(),
                    error_message=None
                ),
                must_add_ttl=True
            )

            from app.worker.celery_app import celery_app        # nsm les circular imports

            res = celery_app.send_task(
                name=task_name,
                kwargs=task_kwargs,
                queue=queue_name
            )
            return ServiceResult.service_success(data=res.id)
        except Exception as e:
            logger.error(
                f"Erreur {e.__class__.__name__} lors de l'envoi de la tâche {task_name} pour l'intent_id : {intent_id}"
                f" et le user_id : {user_id} dans le worker : {e}"
            )
            await self._processing_cache.delete_upload_progress_stream(user_id, intent_id)   # Nettoyage du stream en cas d'erreur pour éviter les mems leakkssss
            return ServiceResult.service_error(
                message=Messages.ERROR_LAUNCHING_MEDIA_PROCESSING_TASK,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
