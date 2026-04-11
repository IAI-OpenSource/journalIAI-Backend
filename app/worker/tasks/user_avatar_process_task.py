import os
import shutil
from uuid import UUID
from app.cache.helpers.base import cache_manager
from app.db.session import AsyncSessionLocal
from app.schemas.user_schemas import UpdateAvatarUrl
from app.services.user_service import UserService
from app.storage.bucket_files_utils import BucketFilesUtils
from app.storage.minio_client import MinioClientFactory
from app.storage.minio_config import BucketName
from app.worker.celery_app import celery_app
from app.worker.tasks.tasks_utils.image_process_task_utils import process_image_with_pillow, upload_images_to_minio
from app.worker.tasks.async_loop_manager import task_async_loop_manager
from app.worker.tasks.tasks_utils.minio.minio_operations import MinIOManager
from app.worker.tasks.workers_task_names import WorkersTaskNames


@celery_app.task(bind=True, name=WorkersTaskNames.USER_AVATAR_PROCESS)
def process_user_avatar_task(self, user_id: str, intent_id: str, filename: str):
    """Tâche Celery pour traiter l'avatar d'un utilisateur après upload."""
    
    raw_path = BucketFilesUtils.generate_object_path_for_raw_image(intent_id, filename)
    local_tmp_path = f"/tmp/{intent_id}_{filename}"
    output_dir = f"/tmp/processed_{intent_id}"
    os.makedirs(output_dir, exist_ok=True)

    minio_backend = MinioClientFactory.get_backend_client()
    
    try:

        minio_backend.fget_object(BucketName.MEDIAS_RAW_UPLOADS.value, raw_path, local_tmp_path)

        process_res = process_image_with_pillow(local_tmp_path, output_dir)
        
        if process_res.is_success():
            processed_files = os.listdir(output_dir)
            for f_name in processed_files:
                local_file = os.path.join(output_dir, f_name)
                remote_file_path = f"{user_id}/{f_name}"
                
                upload_res = MinIOManager.upload_file(
                    bucket_name=BucketName.USER_IDENTITY_ASSETS.value,
                    object_path=remote_file_path,
                    local_file_path=local_file,
                    content_type="image/webp"
                )
                if upload_res.is_error():
                    return upload_res.error

            MinIOManager.delete_file(
                bucket_name=BucketName.MEDIAS_RAW_UPLOADS.value,
                object_path=raw_path,
            )

            async def update_user_avatar():
                redis_instance = cache_manager.get_redis_connection_from_pool()
                try:
                  avatar_path = f"{user_id}/medium.webp"
                  async with AsyncSessionLocal() as db:
                    user_service = UserService(db, redis_instance)
                    await user_service.service_update_user(
                        user_id=UUID(user_id), 
                        user_update_data=UpdateAvatarUrl(avatar_url=avatar_path)
                    )
                finally:
                  await redis_instance.close()
                
            task_async_loop_manager.run_async(update_user_avatar())
            
        else:
            return process_res.error
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        if os.path.exists(local_tmp_path): os.remove(local_tmp_path)