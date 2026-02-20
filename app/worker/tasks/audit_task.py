from uuid import UUID

from app.db.models.enums import TypeActions
from celery import shared_task
from app.repositories.audit_repository import AuditRepository
from app.worker.tasks.async_loop_manager import task_async_loop_manager
from app.worker.tasks.workers_task_names import WorkersTaskNames


@shared_task(name=WorkersTaskNames.SAVE_AUDIT_LOG)
def create_audit_log(user_id: UUID, readable_message: str, action: TypeActions, destination_entity_type: str, destination_entity_id: UUID) -> None:
    """
    Tâche Celery pour créer un log d'audit
    Args:
        user_id: Id de l'utilisateur qui a effectué l'action
        readable_message: Message lisible décrivant l'action effectuée
        action: Type d'action (création, modification, suppression)
        destination_entity_type: Type de l'entité cible de l'action (ex: "User", "Post", etc.)
        destination_entity_id: Id de l'entité cible de l'action
    Returns:
        Que dalle, c'est une tâche pour créer un log d'audit
    """

    task_async_loop_manager.run_async(
        AuditRepository.save_action_in_audit(
            user_id=user_id,
            readable_message=readable_message,
            action=action,
            destination_entity_type=destination_entity_type,
            destination_entity_id=destination_entity_id,
        )
    )
