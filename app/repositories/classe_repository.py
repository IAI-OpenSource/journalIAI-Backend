from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.classe import Classe
from app.repositories import CRUDResult
from app.repositories.repositories_utils import RepositoriesUtils
from app.globals.messages import Messages as msg
import logging

logger = logging.getLogger(__name__)

@dataclass
class ClasseRepository:
    """Repository pour les opérations sur les classes
    """
    db: AsyncSession

    async def get_classe_by_id(self, classe_id: UUID) -> CRUDResult[Classe]:
        """Récupère une classe par son identifiant
        
        Args:
            classe_id: L'identifiant de la classe à récupérer
        
        Returns:
            CRUDResult: Le résultat de l'opération de récupération de la classe
        """
        try :
            result = await self.db.execute(select(Classe).where(Classe.id == classe_id , Classe.deleted_at.is_(None)))
            classe = result.scalar_one_or_none()

            if classe is None:
                logger.info(f"Classe with id {classe_id} not found")
                return CRUDResult.crud_error(msg.CLASSE_NOT_FOUND, 404)
            
            logger.info(f"Classe with id {classe_id} retrieved successfully")
            return CRUDResult.crud_success(classe, 200)
        except IntegrityError as e:
            return await RepositoriesUtils.traiter_integrity_error(e, self.db, logger, Classe)
        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)
        
    async def get_classe_by_prefix_sufix_year(self, classe_prefix: str, classe_suffix: str, academic_year_id: UUID) -> CRUDResult[Classe]:
        """Récupère une classe par son préfixe, suffixe et année académique
        
        Args:
            classe_prefix: Le préfixe de la classe à récupérer
            classe_suffix: Le suffixe de la classe à récupérer
            academic_year_id: L'identifiant de l'année académique à laquelle appartient la classe
        
        Returns:
            CRUDResult: Le résultat de l'opération de récupération de la classe
        """
        try :
            result = await self.db.execute(select(Classe).where(
                Classe.classe_prefix == classe_prefix,
                Classe.classe_suffix == classe_suffix,
                Classe.academic_year_id == academic_year_id,
                Classe.deleted_at.is_(None)
            ))
            classe = result.scalar_one_or_none()

            if classe is None:
                logger.info(f"Classe with prefix {classe_prefix}, suffix {classe_suffix} and academic year id {academic_year_id} not found")
                return CRUDResult.crud_error(msg.CLASSE_NOT_FOUND, 404)
            
            logger.info(f"Classe with prefix {classe_prefix}, suffix {classe_suffix} and academic year id {academic_year_id} retrieved successfully")
            return CRUDResult.crud_success(classe, 200)
        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)
        
        
    async def update_classe(self, classe:Classe, **fields)-> CRUDResult[Classe]:
        """Met à jour une classe
        
        Args:
            classe: La classe à mettre à jour
            fields: Les champs à mettre à jour avec leurs nouvelles valeurs
        
        Returns:
            CRUDResult: Le résultat de l'opération de mise à jour de la classe
        """
        try :
            for field, value in fields.items():
                setattr(classe, field, value)
            await self.db.commit()
            await self.db.refresh(classe)

            logger.info(f"Classe with id {classe.id} updated successfully")
            return CRUDResult.crud_success(classe, 200)
        except IntegrityError as e:
            return await RepositoriesUtils.traiter_integrity_error(e, self.db, logger, Classe)
        except Exception as e:
            await self.db.rollback()
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)
        
    async def create_classe(self, classe: Classe) -> CRUDResult[Classe]:
        """Crée une classe
        
        Args:
            classe: La classe à créer
        
        Returns:
            CRUDResult: Le résultat de l'opération de création de la classe
        """
        try :
            self.db.add(classe)
            await self.db.commit()
            await self.db.refresh(classe)

            logger.info(f"Classe with id {classe.id} created successfully")
            return CRUDResult.crud_success(classe, 201)
        except IntegrityError as e:
            return await RepositoriesUtils.traiter_integrity_error(e, self.db, logger, Classe)
        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)
        
    async def delete_classe(self, classe: Classe) -> CRUDResult[Classe]:
        """Supprime une classe (soft delete)
        
        Args:
            classe: La classe à supprimer
        
        Returns:
            CRUDResult: Le résultat de l'opération de suppression de la classe
        """
        try :
            classe.deleted_at = datetime.now(timezone.utc)
            await self.db.commit()
            await self.db.refresh(classe)
            logger.info(f"Classe with id {classe.id} deleted successfully")
            return CRUDResult.crud_success(classe, 200)
        except IntegrityError as e:
            return await RepositoriesUtils.traiter_integrity_error(e, self.db, logger, Classe)
        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)
        
    async def get_all_classes(self, page: int, page_size: int) -> CRUDResult[tuple]:
        """Récupère toutes les classes
        args:
            page: Le numéro de la page à récupérer
            page_size: Le nombre d'éléments par page
        Returns:
            CRUDResult: Le résultat de l'opération de récupération de toutes les classes
        """
        try:
            base_query = select(Classe).where(Classe.deleted_at.is_(None))
            count_result = await self.db.execute(select(func.count()).select_from(base_query.subquery()))
            total = count_result.scalar_one()
            result = await self.db.execute(base_query.offset((page - 1) * page_size).limit(page_size))
            classes = result.scalars().all()
        
            return CRUDResult.crud_success((classes, total), 200)
        except IntegrityError as e:
            return await RepositoriesUtils.traiter_integrity_error(e, self.db, logger, Classe)
        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)