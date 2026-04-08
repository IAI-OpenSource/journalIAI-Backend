
from uuid import UUID

from app.services.registration_service import RegistrationService
from app.worker.tasks.async_loop_manager import task_async_loop_manager
from app.db.session import AsyncSessionLocal 
from app.worker.celery_app import celery_app
from app.worker.tasks.workers_task_names import WorkersTaskNames


from uuid import UUID
from celery.utils.log import get_task_logger # Plus propre que print pour les workers

logger = get_task_logger(__name__)

@celery_app.task(bind=True, name=WorkersTaskNames.IMPORT_DATA_FROM_EXCEL)
def import_students_task(self, file_base64: str, classe_id: str): 
    """Tâche Celery avec remontée d'état pour le front-end"""
    
    async def process():
        # Conversion sécurisée de l'ID de classe
        c_id = UUID(classe_id) if isinstance(classe_id, str) else classe_id
        
        async with AsyncSessionLocal() as db:
            try:
                service = RegistrationService(db)
                return await service.service_imports_reg_data(
                    file_base=file_base64, 
                    classe_id=c_id
                )
            except Exception as e:
                logger.error(f"Erreur interne service : {e}")
                raise e

    try:
        logger.info(f"Lancement de l'importation pour la classe {classe_id}")
        
        # Exécution de la boucle async
        result = task_async_loop_manager.run_async(process())
        
        # --- GESTION DU RÉSULTAT ---
        if result.is_error():
            # On met à jour l'état pour que le front puisse lire l'erreur
            self.update_state(
                state='FAILURE',
                meta={
                    'exc_type': 'ImportError',
                    'exc_message': [result.error],
                    'custom_message': result.error # Ton message user-friendly
                }
            )
            # On raise pour que Celery marque la tâche comme "FAILED"
            raise Exception(result.error)

        logger.info(f"Importation réussie : {result.data.message}")
        
        # Ce retour sera stocké dans le backend (Redis) et accessible via task.result
        return result.data.message

    except Exception as e:
        logger.error(f"Échec critique de la tâche : {e}")
        raise e