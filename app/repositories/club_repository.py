from dataclasses import dataclass
import logging
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.db.models.club import Club
from app.repositories import CRUDResult
from datetime import datetime, timezone
from app.globals.messages import Messages as msg
from app.repositories.repositories_utils import RepositoriesUtils

logger = logging.getLogger(__name__)

@dataclass
class ClubRepository:
    """Repository pour les opérations sur les clubs
    """
    db: AsyncSession

    async def get_club_by_id(self, club_id: UUID) -> CRUDResult[Club]:
        """Récupère un club par son identifiant
        
        Args:
            club_id: L'identifiant du club à récupérer
        
        Returns:
            CRUDResult: Le résultat de l'opération de récupération du club
        """
        try :
            result = await self.db.execute(select(Club).where(Club.id == club_id , Club.deleted_at.is_(None)))
            club = result.scalar_one_or_none()

            if club is None:
                logger.info(f"Club with id {club_id} not found")
                return CRUDResult.crud_error(msg.CLUB_NOT_FOUND, 404)
            
            logger.info(f"Club with id {club_id} retrieved successfully")
            return CRUDResult.crud_success(club, 200)
        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)

    async def get_club_by_slug(self, slug: str) -> CRUDResult[Club]:
        """Récupère un club par son slug
        
        Args:
            slug: Le slug du club à récupérer
        
        Returns:
            CRUDResult: Le résultat de l'opération de récupération du club
        """
        try :
            result = await self.db.execute(select(Club).where(Club.slug == slug , Club.deleted_at.is_(None)))
            club = result.scalar_one_or_none()

            if club is None:
                logger.info(f"Club with slug {slug} not found")
                return CRUDResult.crud_error(msg.CLUB_NOT_FOUND, 404)
            
            logger.info(f"Club with slug {slug} retrieved successfully")
            return CRUDResult.crud_success(club, 200)

        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)


    async def get_all_clubs(self, page :int =1, page_size: int = 20, is_active : bool = False ) -> CRUDResult[Club]:
        """Récupère tous les clubs avec pagination et filtrage par statut actif/inactif
        
        Args:
            page: Le numéro de page à récupérer (par défaut 1)
            page_size: Le nombre de clubs par page (par défaut 20)
            is_active: Filtrer les clubs actifs ou inactifs (par défaut False, tous les clubs)
        
        Returns:
            CRUDResult: Le résultat de l'opération de récupération des clubs
        """
        try :
            base_query = select(Club).where(Club.deleted_at.is_(None))
            if is_active:
               base_query = base_query.where(Club.is_active == True)

            count_result = await self.db.execute(select(func.count()).select_from(base_query.subquery()))
            total = count_result.scalar_one()
           
            offset = (page - 1) * page_size
            result = await self.db.execute(base_query.offset(offset).limit(page_size))
            clubs = list(result.scalars().all())
            logger.info(f"Retrieved {len(clubs)} clubs (page {page}/{(total + page_size - 1) // page_size})")
            return CRUDResult.crud_success((clubs,total), 200)
        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)



    async def create_club(self, club : Club) -> CRUDResult[Club]:
        """insert un club déja crée dans la base de donnée 
        
        Argzs :
            club : le club déja crée 
        Returns :
            CRUDResult :Le resultat de l'opération de creation du club
        """

        try :
            self.db.add(club)
            await self.db.commit()
            await self.db.refresh(club)
            logger.info(f"Club with name {club.name} created successfully")
            return CRUDResult.crud_success(club, 201)
        except IntegrityError as e :
            return await RepositoriesUtils.traiter_integrity_error(e, self.db, logger, Club)
        except Exception as e :
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)
        
        
    async def update_club(self, club: Club, **fields) -> CRUDResult[Club]:
        """Met à jour un club existant dans la base de données
        
        Args:
            club: Le club à mettre à jour (doit être déjà attaché à la session)
            fields: Les champs à mettre à jour avec leurs nouvelles valeurs
        Returns:
            CRUDResult: Le résultat de l'opération de mise à jour du club
        """
        try :
            for field, value in fields.items():
                setattr(club, field, value)
            await self.db.commit()
            await self.db.refresh(club)
            return CRUDResult.crud_success(club, 200)
        except IntegrityError as e :
            return await RepositoriesUtils.traiter_integrity_error(e, self.db, logger, Club)
        except Exception as e :
            await self.db.rollback()
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)
        
    async def soft_delete_club(self, club: Club) -> CRUDResult:
        """Supprime logiquement un club (met à jour deleted_at)
        
        Args:
            club: Le club à supprimer logiquement
        
        Returns:
            CRUDResult: Le résultat de l'opération de suppression logique du club
        """
        try :
            club.deleted_at = datetime.now(timezone.utc)
            await self.db.commit()
            await self.db.refresh(club)
            return CRUDResult.crud_success(club, 200)
        except IntegrityError as e :
            return await RepositoriesUtils.traiter_integrity_error(e, self.db, logger, Club)
        except Exception as e :
            await self.db.rollback()
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)
    