from dataclasses import dataclass
from logging import Logger
from uuid import UUID

from minio.datatypes import Object
from sqlalchemy.orm import Mapped

from app.db.models.post_media import PostMedia
from app.globals.messages import Messages
from app.schemas.post_upload_schemas import FileToUploadSchema
from app.storage.bucket_files_utils import BucketFilesUtils
from app.storage.minio_config import BucketName
from app.storage.post_video_storage import PostUploadStorage
from app.worker.tasks.async_loop_manager import task_async_loop_manager
from app.worker.tasks.tasks_utils.base import ProcessingStep, ProcessingResult
from app.worker.tasks.tasks_utils.common_media_utils import generate_blurhash_str
from app.worker.tasks.tasks_utils.handlers import ProgressHandler
from app.worker.tasks.tasks_utils.image_process_task_utils import get_image_metadata, process_image_with_pillow, \
    upload_images_to_minio
from app.worker.tasks.tasks_utils.minio import MinIOManager
from app.worker.tasks.tasks_utils.video_process_task_utils import generate_hls_command, get_video_metadata, \
    get_target_qualities, process_video_file_with_ffmpeg, generate_thumbnail, upload_hls_to_minio
from app.worker.tasks.validation import FileValidator


@dataclass
class ManyMediasProcessHelper:
    progress_handler: ProgressHandler
    intent_id: str
    logger: Logger

    @staticmethod
    def _return_error(error: str) -> ProcessingResult:
        return ProcessingResult.error_response(error=error)

    def verify_file_existing_and_download(
        self,
        step: ProcessingStep,
        file_info: FileToUploadSchema,
        local_raw_path: str,
        media_progress_weight: float
    ) -> ProcessingResult[Object]:

        type_fichier = "vidéo" if file_info.is_video else "photo"

        raw_object_result = PostUploadStorage.get_video_upload_intent_file_info(self.intent_id, file_info.file_name) \
            if file_info.is_video else PostUploadStorage.get_image_upload_intent_file_info(self.intent_id, file_info.file_name)

        if raw_object_result is None:
            self.logger.error(f"Fichier {type_fichier} non trouvé dans MinIO pour l'intent {self.intent_id} et le fichier {file_info.file_name}")
            return self._return_error(error=Messages.INTERNAL_SERVER_ERROR)

        self.logger.info(f"Fichier {type_fichier} trouvé dans MinIO pour l'intent {self.intent_id} et le fichier {file_info.file_name}")

        download_result = MinIOManager.download_file(
            bucket_name=raw_object_result.bucket_name,
            object_path=raw_object_result.object_name,
            local_destination=local_raw_path
        )

        if download_result.is_error():
            self.logger.error(f"Erreur lors du téléchargement du fichier {type_fichier} depuis MinIO pour l'intent {self.intent_id} et le fichier {file_info.file_name}: {download_result.error}")
            return self._return_error(error=Messages.INTERNAL_SERVER_ERROR)

        self.logger.info(f"Fichier {type_fichier} téléchargé avec succès depuis MinIO pour l'intent {self.intent_id} et le fichier {file_info.file_name}")

        validation_res = FileValidator.validate_video(local_raw_path) if file_info.is_video else FileValidator.validate_image(local_raw_path)

        if validation_res.is_error():
            self.logger.error(f"Validation du fichier {type_fichier} échouée pour l'intent {self.intent_id} et le fichier {file_info.file_name}: {validation_res.error}")
            return self._return_error(error=Messages.INTERNAL_SERVER_ERROR)

        task_async_loop_manager.run_async(self.progress_handler.update_step(step=step, weight=media_progress_weight))

        return ProcessingResult.ok_response(raw_object_result)

    def compress_file(
        self,
        step: ProcessingStep,
        file_info: FileToUploadSchema,
        local_raw_path: str,
        output_dir: str,
        media_progress_weight: float
    ) -> ProcessingResult[tuple[str | None, int, int, int | None ]]:
        """local_thumbnail_path, height, width, duration"""

        thumb_path, h, w, duration = None, None, None, None
        if file_info.is_video:
            metadata_result = get_video_metadata(local_raw_path)
            if metadata_result.is_error():
                self.logger.error(f"Erreur lors de l'extraction des métadonnées vidéo pour l'intent {self.intent_id} et le fichier {file_info.file_name}: {metadata_result.error}")
                return self._return_error(metadata_result.error)

            video_metadata = metadata_result.data
            self.logger.info(f"Métadonnées vidéo pour l'intent {self.intent_id} et le fichier {file_info.file_name} : {video_metadata}")

            # Traiter la vidéo
            qualities = get_target_qualities(video_metadata['height'])
            self.logger.info(f"Qualités cibles pour la compression vidéo pour l'intent {self.intent_id} et le fichier {file_info.file_name} : {qualities}")

            hls_command = generate_hls_command(
                local_raw_path=local_raw_path,
                qualities=qualities,
                output_dir=output_dir,
                has_audio=video_metadata['has_audio']
            )

            process_result = process_video_file_with_ffmpeg(hls_command)

            if process_result.is_error():
                self.logger.error(f"Erreur lors de la compression vidéo pour l'intent {self.intent_id} et le fichier {file_info.file_name} : {process_result.error}")
                return self._return_error(process_result.error)

            self.logger.info(f"Compression vidéo réussie pour l'intent {self.intent_id} et le fichier {file_info.file_name}")

            try:
                thumbnail_path = generate_thumbnail(
                    local_raw_path=local_raw_path,
                    output_dir=output_dir,
                    ss_time=max(int(video_metadata['duration'] * 0.1), 1)
                )
            except Exception as e:
                self.logger.warning(f"Génération de la miniature échouée pour l'intent {self.intent_id} et le fichier {file_info.file_name}, mais on continue : {e}")
                thumbnail_path = None

            thumb_path = thumbnail_path
            h = video_metadata['height']
            w = video_metadata['width']
            duration = video_metadata['duration']
        else:
            metadata_result = get_image_metadata(local_raw_path)

            if metadata_result.is_error():
                self.logger.error(f"Erreur lors de l'extraction des métadonnées image pour l'intent {self.intent_id} et le fichier {file_info.file_name} : {metadata_result.error}")
                return self._return_error(metadata_result.error)
            image_metadata = metadata_result.data
            process_result = process_image_with_pillow(local_raw_path, output_dir)
            if process_result.is_error():
                self.logger.error(f"Erreur lors de la compression image pour l'intent {self.intent_id} et le fichier {file_info.file_name} : {process_result.error}")
                return self._return_error(Messages.INTERNAL_SERVER_ERROR)

            processed_images_paths = process_result.data
            self.logger.info(f"Images traitées (pour intent_id : {self.intent_id}, fichier : {file_info.file_name}) créées: {list(processed_images_paths.keys())}")

            thumb_path = processed_images_paths.get("thumbnail")
            h = image_metadata['height']
            w = image_metadata['width']

        task_async_loop_manager.run_async(self.progress_handler.update_step(step=step, weight=media_progress_weight))
        return ProcessingResult.ok_response((thumb_path, h, w, duration))

    def upload_files_to_minio(
        self,
        step: ProcessingStep,
        file_info: FileToUploadSchema,
        thumbnail_path: str | None,
        output_dir: str,
        media_progress_weight: float
    ) -> ProcessingResult[tuple[str, str | None]]:
        """minio_media_url et minio_thumbnail_url"""

        if file_info.is_video:
            final_bucket_objects_path = BucketFilesUtils.generate_objects_path_for_processed_video()

            upload_result = task_async_loop_manager.run_async(
                upload_hls_to_minio(output_dir, final_bucket_objects_path)
            )

            if upload_result.is_error():
                self.logger.error(f"Erreur lors de l'upload de la vidéo traitée vers MinIO pour l'intent {self.intent_id} et le fichier {file_info.file_name} : {upload_result.error}")
                return self._return_error(upload_result.error)

            # Upload miniature
            final_bucket_thumbnail_path = None

            if thumbnail_path:
                final_bucket_thumbnail_path = BucketFilesUtils.generate_objects_path_for_video_thumbnail()
                res = MinIOManager.upload_file(
                    BucketName.USER_IDENTITY_ASSETS.value,
                    final_bucket_thumbnail_path,
                    thumbnail_path,
                    content_type="image/webp"
                )
                if res.is_error():
                    self.logger.error(f"Erreur upload miniature mais lets go on continue pour l'intent {self.intent_id} et le fichier {file_info.file_name}: {res.error}")
                    final_bucket_thumbnail_path = None

            media_url, thumbnail_url = final_bucket_objects_path, final_bucket_thumbnail_path
        else:
            final_bucket_objects_path = BucketFilesUtils.generate_objects_path_for_processed_image()
            upload_result = task_async_loop_manager.run_async(
                upload_images_to_minio(output_dir, final_bucket_objects_path)
            )

            if upload_result.is_error():
                self.logger.error(f"Erreur lors de l'upload des images traitées vers MinIO pour l'intent {self.intent_id} et le fichier {file_info.file_name} : {upload_result.error}")
                return self._return_error(upload_result.error)
            self.logger.info(f"Upload des images traitées vers MinIO réussi pour l'intent {self.intent_id} et le fichier {file_info.file_name}")
            final_bucket_thumbnail_path = None
            if thumbnail_path:
                final_bucket_thumbnail_path = BucketFilesUtils.generate_objects_path_for_image_thumbnail()
                res = MinIOManager.upload_file(
                    BucketName.USER_IDENTITY_ASSETS.value,
                    final_bucket_thumbnail_path,
                    thumbnail_path,
                    content_type="image/webp"
                )
                if res.is_error():
                    self.logger.error(f"Erreur upload miniature mais lets go on continue pour l'intent {self.intent_id} et le fichier {file_info.file_name}: {res.error}")
                    final_bucket_thumbnail_path = None

            media_url, thumbnail_url = final_bucket_objects_path, final_bucket_thumbnail_path

        task_async_loop_manager.run_async(self.progress_handler.update_step(step=step, weight=media_progress_weight))
        return ProcessingResult.ok_response((media_url, thumbnail_url))

    def create_post_media_object(
            self,
            post_id: Mapped[UUID],
            index: int,
            duration: int | None,
            width: int,
            height: int,
            file_info: FileToUploadSchema,
            local_thumbnail_path: str | None,
            bucket_thumbnail_path: str | None,
            file_size: int,
            bucket_media_url: str,
    ) -> ProcessingResult[PostMedia]:
        try:
            post_media = PostMedia(
                post_id=post_id,
                blur_hash=generate_blurhash_str(local_thumbnail_path),
                media_url=bucket_media_url,
                media_type=file_info.media_type,
                file_size=file_size,
                thumbnail_url=bucket_thumbnail_path,
                stored_bucket_name=BucketName.POSTS_PERMANENT_CONTENT.value,
                duration=duration,
                width=width,
                height=height
            )

            post_media.display_order = index
            post_media.is_processed = True
            return ProcessingResult.ok_response(post_media)
        except Exception as e:
            self.logger.error(f"Erreur lors de la création de l'objet PostMedia pour l'intent {self.intent_id} et le fichier {file_info.file_name} : {e}")
            return self._return_error(Messages.INTERNAL_SERVER_ERROR)












