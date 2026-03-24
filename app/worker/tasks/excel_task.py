
from uuid import UUID

from app.services.registration_service import RegistrationService
from app.worker.tasks.async_loop_manager import task_async_loop_manager
from app.db.session import AsyncSessionLocal 
from app.worker.celery_app import celery_app
from app.worker.tasks.workers_task_names import WorkersTaskNames


@celery_app.task(name=WorkersTaskNames.IMPORT_DATA_FROM_EXCEL)
def import_students_task(file_base64: str, classe_id: UUID): 
    """Tache celery pour lire le fichier excel"""
    
    async def process():
      async with AsyncSessionLocal() as db:
        try:
          service = RegistrationService(db)
          # On attend la fin du service
          return await service.service_imports_reg_data(
              file_base=file_base64, 
              classe_id=classe_id
          )
        except Exception as e:
          print(f"DEBUG: Erreur dans le service d'importation : {e}")
          raise e
    try:
      print(f"DEBUG: Lancement de la tâche pour la classe {classe_id}")
      
      result = task_async_loop_manager.run_async(process())
      
      print(f"DEBUG: Tâche terminée avec: {result.data}")
      return "Importation terminée" 
        
    except Exception as e:
      print(f"DEBUG: Échec de la tâche Celery : {e}")
      raise e


