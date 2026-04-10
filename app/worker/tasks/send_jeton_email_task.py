
from uuid import UUID

from app.core.config import URL_INSCRIPTION
from app.integrations.fastApi_email.email_manager import EmailServiceManager
from app.services.registration_service import RegistrationService
from app.worker.tasks.async_loop_manager import task_async_loop_manager
from app.db.session import AsyncSessionLocal 
from app.worker.celery_app import celery_app
from app.worker.tasks.workers_task_names import WorkersTaskNames
from app.integrations.fastApi_email.fastapi_mail_config import fm


from uuid import UUID
from celery.utils.log import get_task_logger 

logger = get_task_logger(__name__)

@celery_app.task(bind=True, name=WorkersTaskNames.SEND_JETON_EMAIL)
def send_jetons_email_orchestrator(self, classe_id: str): 
    """Récupère les étudiants et distribue les envois"""
    
    async def get_students():
        c_id = UUID(classe_id) if isinstance(classe_id, str) else classe_id
        async with AsyncSessionLocal() as db:
            service = RegistrationService(db)
            return await service.service_get_all_jetons_by_classe(classe_id=c_id)

    result = task_async_loop_manager.run_async(get_students())

    if result.is_error():
        self.update_state(
            state='FAILURE',
            meta={
                'exc_type': 'ImportError',
                'exc_message': result.error,
                'custom_message': result.error 
            }
        )
        raise RuntimeError(result.error)

    # --- DISTRIBUTION DES ENVOIS ---
    # Au lieu d'envoyer ici, on lance une sous-tâche par étudiant
    for receiver in result.data:
        # On prépare les data pour la sous-tâche
        celery_app.send_task(
            WorkersTaskNames.SINGLE_EMAIL_SEND, 
            args=[
              receiver.email,
              receiver.last_name,
              receiver.first_name,
              receiver.jeton,
              
            ]
        )

    return f"Distribution terminée pour {len(result.data)} étudiants"
  
  

## la sous tache pour chaque envoi par étudiant
@celery_app.task(name=WorkersTaskNames.SINGLE_EMAIL_SEND)
def send_single_email_task(email, last_name, first_name, jeton):
    """Gère l'envoi d'un seul email de manière isolée"""
    
    email_manager = EmailServiceManager(fast_mail=fm)
   
    async def do_send():
        await email_manager.send_jetons_email(
            url_inscription=URL_INSCRIPTION,
            email=email,
            last_name=last_name,
            first_name=first_name,
            jeton=jeton
        )

    task_async_loop_manager.run_async(do_send())
    return f"Email envoyé à {email}"