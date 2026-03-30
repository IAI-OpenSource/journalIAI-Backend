from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.academic_year import AcademicYear
from app.repositories import CRUDResult
from app.repositories.repositories_utils import RepositoriesUtils
from app.globals.messages import Messages as msg
from sqlalchemy import update
import logging

from app.schemas.global_schemas import StringMessage

logger = logging.getLogger(__name__)

@dataclass
class AcademicYearRepository:
    """Repository pour les opérations sur les années académiques
    """
    db: AsyncSession

    async def get_academic_year_by_id(self, academic_year_id: UUID) -> CRUDResult[AcademicYear]:
        """Récupère une année académique par son identifiant
        
        Args:
            academic_year_id: L'identifiant de l'année académique à récupérer
        
        Returns:
            CRUDResult: Le résultat de l'opération de récupération de l'année académique
        """
        try :
            result = await self.db.execute(select(AcademicYear).where(AcademicYear.id == academic_year_id , AcademicYear.deleted_at.is_(None)))
            academic_year = result.scalar_one_or_none()

            if academic_year is None:
                logger.info(f"Academic year with id {academic_year_id} not found")
                return CRUDResult.crud_error(msg.ACADEMIC_YEAR_NOT_FOUND, 404)
            
            logger.info(f"Academic year with id {academic_year_id} retrieved successfully")
            return CRUDResult.crud_success(academic_year, 200)
        except IntegrityError as e:
            return await RepositoriesUtils.traiter_integrity_error(e, self.db, logger, AcademicYear)
        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)
        

    async def get_active_academic_year(self) -> CRUDResult[AcademicYear]:
        """Récupère l'année académique active
        
        Returns:
            CRUDResult: Le résultat de l'opération de récupération de l'année académique active
        """
        try :
            result = await self.db.execute(select(AcademicYear).where(AcademicYear.active == True , AcademicYear.deleted_at.is_(None)))
            academic_year = result.scalar_one_or_none()

            if academic_year is None:
                logger.info("Active academic year not found")
                return CRUDResult.crud_error(msg.ACADEMIC_YEAR_NOT_FOUND, 404)
            
            logger.info(f"Active academic year with id {academic_year.id} retrieved successfully")
            return CRUDResult.crud_success(academic_year, 200)
        except IntegrityError as e:
            return await RepositoriesUtils.traiter_integrity_error(e, self.db, logger, AcademicYear)
        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)
        
    async def get_all_academic_years(self, page: int, page_size: int) -> CRUDResult[list[AcademicYear]]:
        """Récupère toutes les années académiques
        
        Returns:
            CRUDResult: Le résultat de l'opération de récupération de toutes les années académiques
        """
        try :
            count_result = await self.db.execute(select(func.count()).select_from(AcademicYear).where(AcademicYear.deleted_at.is_(None)))
            total = count_result.scalar_one()
            result = await self.db.execute(select(AcademicYear).where(AcademicYear.deleted_at.is_(None)).offset((page - 1) * page_size).limit(page_size).order_by(AcademicYear.created_at.desc()))
            academic_years = result.scalars().all()

            logger.info(f"{len(academic_years)} academic years retrieved successfully")
            return CRUDResult.crud_success((academic_years,total), 200)
        except IntegrityError as e:
            return await RepositoriesUtils.traiter_integrity_error(e, self.db, logger, AcademicYear)
        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)
        
    async def get_academic_year_by_libelle(self, libelle: str) -> CRUDResult[AcademicYear]:
        """Récupère une année académique par son libellé
        
        Args:
            libelle: Le libellé de l'année académique à récupérer (ex: "2025-2026")
        
        Returns:
            CRUDResult: Le résultat de l'opération de récupération de l'année académique
        """
        try :
            result = await self.db.execute(select(AcademicYear).where(AcademicYear.libelle == libelle , AcademicYear.deleted_at.is_(None)))
            academic_year = result.scalar_one_or_none()

            if academic_year is None:
                logger.info(f"Academic year with libelle {libelle} not found")
                return CRUDResult.crud_error(msg.ACADEMIC_YEAR_NOT_FOUND, 404)
            
            logger.info(f"Academic year with libelle {libelle} retrieved successfully")
            return CRUDResult.crud_success(academic_year, 200)
        except IntegrityError as e:
            return await RepositoriesUtils.traiter_integrity_error(e, self.db, logger, AcademicYear)
        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)
        
    async def create_academic_year(self, academic_year: AcademicYear) -> CRUDResult[AcademicYear]:
        """Crée une nouvelle année académique
        
        Args:
            academic_year: L'année académique à créer
        
        Returns:
            CRUDResult: Le résultat de l'opération de création de l'année académique
        """
        try :
            self.db.add(academic_year)
            await self.db.commit()
            await self.db.refresh(academic_year)

            logger.info(f"Academic year with id {academic_year.id} created successfully")
            return CRUDResult.crud_success(academic_year, 201)
        except IntegrityError as e:
            return await RepositoriesUtils.traiter_integrity_error(e, self.db, logger, AcademicYear)
        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)
        
    async def update_academic_year(self, academic_year: AcademicYear, **fields) -> CRUDResult[AcademicYear]:
        """Met à jour une année académique
        
        Args:
            academic_year: L'année académique à mettre à jour
            fields: Les champs à mettre à jour avec leurs nouvelles valeurs
        
        Returns:
            CRUDResult: Le résultat de l'opération de mise à jour de l'année académique
        """
        try :
            for field, value in fields.items():
                setattr(academic_year, field, value)
            await self.db.commit()
            await self.db.refresh(academic_year)

            logger.info(f"Academic year with id {academic_year.id} updated successfully")
            return CRUDResult.crud_success(academic_year, 200)
        except IntegrityError as e:
            return await RepositoriesUtils.traiter_integrity_error(e, self.db, logger, AcademicYear)
        except Exception as e:
            await self.db.rollback()
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)
        
    async def soft_delete_academic_year(self, academic_year: AcademicYear) -> CRUDResult[AcademicYear]:
        """Supprime une année académique (soft delete)
        
        Args:
            academic_year: L'année académique à supprimer
        
        Returns:
            CRUDResult: Le résultat de l'opération de suppression de l'année académique
        """
        try :
            academic_year.deleted_at = datetime.now(timezone.utc)
            await self.db.commit()
            await self.db.refresh(academic_year)

            logger.info(f"Academic year with id {academic_year.id} deleted successfully")
            return CRUDResult.crud_success(academic_year, 200)
        except IntegrityError as e:
            return await RepositoriesUtils.traiter_integrity_error(e, self.db, logger, AcademicYear)
        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)
        
    async def deactivate_academic_year(self) -> CRUDResult[AcademicYear]:
        """Désactive une année académique (la rend inactive)
        
        Returns:
            CRUDResult: Le résultat de l'opération de désactivation de l'année académique
        """
        try :
            stmt = (update(AcademicYear).where(AcademicYear.active == True, AcademicYear.deleted_at.is_(None)).values(active=False))
            await self.db.execute(stmt)
            await self.db.commit()
            logger.info(f"Academic year deactivated successfully")
            return CRUDResult.crud_success("Année académique désactivée avec succès.", 200)
        except IntegrityError as e:
            return await RepositoriesUtils.traiter_integrity_error(e, self.db, logger, AcademicYear)
        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)
        