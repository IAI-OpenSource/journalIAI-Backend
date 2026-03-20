
from celery import shared_task
from app.services.registration_service import RegistrationService
from app.worker.tasks.async_loop_manager import task_async_loop_manager


@shared_task
def import_students_task(file_base64: str, classe_id: int, service: RegistrationService):
  """Tache celery pour lire le fichier excel

  Args:
      file_base64 (str): On prend le contenu lu depuis la route en base64 str
      classe_id (int): On prend aussi le id de la classe envoyer
  """
  
  task_async_loop_manager.run_async(
    service.service_imports_reg_data(
    file_base=file_base64, 
    classe_id=classe_id
    ) 
  )


