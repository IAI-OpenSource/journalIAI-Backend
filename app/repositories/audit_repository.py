from asyncio import Semaphore

from app.db.session import AsyncSessionLocal
from app.globals.messages import Messages
from uuid import UUID

from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit_log import AuditLog
from app.db.models.enums import TypeActions
from app.repositories import CRUDResult
from logging import getLogger

from app.repositories.repositoriesutils import RepositoriesUtils
from app.worker.celery_app import celery_app
from app.worker.workers_task_names import WorkersTaskNames

logger = getLogger(__name__)

class AuditRepository:
    """Classe de repository pour gérer les opérations liées aux audits."""

    write_semaphore = Semaphore(50)  # Semaphore pour gérer beaucoup d'écritures concurrentes

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save_audit_log(self, user_id: UUID, readable_message: str, action: TypeActions, destination_entity_type: str, destination_entity_id: UUID) -> CRUDResult[AuditLog]:
        """
        Enregistre un log d'audit dans la base de données.
        Args:
            user_id: Id de l'utilisateur qui a effectué l'action
            readable_message: Message lisible décrivant l'action effectuée
            action: Type d'action (création, modification, suppression, etc.)
            destination_entity_type: Type de l'entité cible de l'action (ex: "User", "Post", etc.)
            destination_entity_id: Id de l'entité cible de l'action
        Returns:
            Un objet CRUDResult contenant le log d'audit créé ou une erreur en cas d'échec.
        """
        try:
            requete = insert(AuditLog).values(
                user_id=user_id,
                readable_message=readable_message,
                action=action,
                destination_entity_type=destination_entity_type,
                destination_entity_id=destination_entity_id
            ).returning(AuditLog)       # On utilise .returning() pour récupérer l'instance créée directement depuis la requête d'insertion sans avoir à faire un refresh après commit

            resultat = await self.session.execute(requete)
            audit_log = resultat.scalar_one()
            await self.session.commit()

            return CRUDResult.crud_success(audit_log, 200)

        except IntegrityError as ie:
            message = await RepositoriesUtils.traiter_integrity_error(ie, self.session, logger, AuditLog)
            return CRUDResult.crud_error(message, 400)
        except Exception as e:
            print(f"Exception non gérée : {e}")
            await RepositoriesUtils.traiter_exception(e, self.session, logger)
            return CRUDResult.crud_error(Messages.INTERNAL_SERVER_ERROR, 500)

    @classmethod
    async def save_action_in_audit(cls, user_id: UUID, readable_message: str, action: TypeActions, destination_entity_type: str, destination_entity_id: UUID) -> None:
        """
        Méthode de classe pour enregistrer une action dans l'audit sans avoir à instancier le repository.
        Cette méthode crée une session temporaire pour effectuer l'opération d'enregistrement du log d'audit.
        Args:
            user_id: Id de l'utilisateur qui a effectué l'action
            readable_message: Message lisible décrivant l'action effectuée
            action: Type d'action (création, modification, suppression, etc.)
            destination_entity_type: Type de l'entité cible de l'action (ex: "User", "Post", etc.)
            destination_entity_id: Id de l'entité cible de l'action
        Returns:
            Que dalle, c'est une méthode utilitaire pour enregistrer une action dans l'audit
        """
        async with cls.write_semaphore:
            nouvel_audit_log = AuditLog(
                user_id=user_id,
                readable_message=readable_message,
                action=action,
                destination_entity_type=destination_entity_type,
                destination_entity_id=destination_entity_id
            )
            try:
                async with AsyncSessionLocal() as session:
                        session.add(nouvel_audit_log)
                        await session.commit()
            except IntegrityError as ie:
                await RepositoriesUtils.traiter_integrity_error(ie, session, logger, AuditLog)
            except Exception as e:
                await RepositoriesUtils.traiter_exception(e, session, logger)
    @classmethod
    def save_creation_action_in_audit(cls, user_id: UUID, readable_message: str, destination_entity_type: str, destination_entity_id: UUID) -> None:
        """
        Méthode utilitaire pour enregistrer une action de création dans l'audit
        Args:
            user_id: Id de l'utilisateur qui a effectué l'action
            readable_message: Message lisible décrivant l'action effectuée
            destination_entity_type: Type de l'entité cible de l'action (ex: "User", "Post", etc.)
            destination_entity_id: Id de l'entité cible de l'action
        Returns:
            Que dalle, c'est une méthode utilitaire pour enregistrer une action de création dans l'audit
        """

        celery_app.send_task(
            WorkersTaskNames.SAVE_AUDIT_LOG,
            kwargs={
                "user_id": user_id,
                "readable_message": readable_message,
                "action": TypeActions.CREATION,
                "destination_entity_type": destination_entity_type,
                "destination_entity_id": destination_entity_id,
            },
        )

    @classmethod
    def save_modification_action_in_audit(cls, user_id: UUID, readable_message: str, destination_entity_type: str, destination_entity_id: UUID) -> None:
        """
        Méthode utilitaire pour enregistrer une action de modification dans l'audit
        Args:
            user_id: Id de l'utilisateur qui a effectué l'action
            readable_message: Message lisible décrivant l'action effectuée
            destination_entity_type: Type de l'entité cible de l'action (ex: "User", "Post", etc.)
            destination_entity_id: Id de l'entité cible de l'action
        Returns:
            Que dalle, c'est une méthode utilitaire pour enregistrer une action de modification dans l'audit
        """
        celery_app.send_task(
            WorkersTaskNames.SAVE_AUDIT_LOG,
            kwargs={
                "user_id": user_id,
                "readable_message": readable_message,
                "action": TypeActions.MODIFICATION,
                "destination_entity_type": destination_entity_type,
                "destination_entity_id": destination_entity_id,
            }
        )

    @classmethod
    def save_deletion_action_in_audit(cls, user_id: UUID, readable_message: str, destination_entity_type: str, destination_entity_id: UUID) -> None:
        """
        Méthode utilitaire pour enregistrer une action de suppression dans l'audit
        Args:
            user_id: Id de l'utilisateur qui a effectué l'action
            readable_message: Message lisible décrivant l'action effectuée
            destination_entity_type: Type de l'entité cible de l'action (ex: "User", "Post", etc.)
            destination_entity_id: Id de l'entité cible de l'action
        Returns:
            Que dalle, c'est une méthode utilitaire pour enregistrer une action de suppression dans l'audit
        """

        celery_app.send_task(
            WorkersTaskNames.SAVE_AUDIT_LOG,
            kwargs={
                "user_id": user_id,
                "readable_message": readable_message,
                "action": TypeActions.SUPPRESSION,
                "destination_entity_type": destination_entity_type,
                "destination_entity_id": destination_entity_id,
            }
        )

    @classmethod
    def save_accession_action_in_audit(cls, user_id: UUID, readable_message: str, destination_entity_type: str, destination_entity_id: UUID) -> None:
        """
        Méthode utilitaire pour enregistrer une action d'accession sensible dans l'audit
        Args:
            user_id: Id de l'utilisateur qui a effectué l'action
            readable_message: Message lisible décrivant l'action effectuée
            destination_entity_type: Type de l'entité cible de l'action (ex: "User", "Post", etc.)
            destination_entity_id: Id de l'entité cible de l'action
        Returns:
            Que dalle, c'est une méthode utilitaire pour enregistrer une action d'accession dans l'audit
        """

        celery_app.send_task(
            WorkersTaskNames.SAVE_AUDIT_LOG,
            kwargs={
                "user_id": user_id,
                "readable_message": readable_message,
                "action": TypeActions.ACCESSION,
                "destination_entity_type": destination_entity_type,
                "destination_entity_id": destination_entity_id,
            }
        )


