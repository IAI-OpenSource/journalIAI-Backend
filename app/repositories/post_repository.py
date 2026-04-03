## Ce fichier contient le repository de la table posts (et post_media / post_views).
## Vous y trouverez les requêtes base de données.

import base64
import logging
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, List, Any
from uuid import UUID

from sqlalchemy import insert, select, update, func, Select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload, with_loader_criteria
from fastapi import  status
from app.db.models.post import Post
from app.db.models.post_media import PostMedia
from app.db.models.post_views import PostViews
from app.repositories import CRUDResult
from app.schemas.post_schemas import CreatePost, UpdatePost
from app.globals.messages import Messages
from .repositories_utils import RepositoriesUtils
from ..db.models.club import Club
from ..db.models.event import Event
from ..db.models.user import User

logger = logging.getLogger(__name__)

# Nombre de posts retournés par page dans le feed
DEFAULT_PAGE_SIZE = 10


def _encode_cursor(created_at: datetime, post_id: UUID) -> str:
    """Encode un curseur opaque à partir de created_at et id.

    Format : base64({ "created_at": "ISO8601", "id": "uuid" })    """
    payload = {
        "created_at": created_at.isoformat(),
        "id": str(post_id),
    }
    
    raw = json.dumps(payload, separators=(",", ":"))
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    """Décode un curseur en (created_at, post_id).

    Raises:
        ValueError: Si le curseur est malformé.
    """
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        data = json.loads(raw)
        return datetime.fromisoformat(data["created_at"]), UUID(data["id"])
    except Exception:
        raise ValueError("Curseur de pagination invalide.")


@dataclass
class PostRepository:

    db: AsyncSession

    # Posts
    @staticmethod
    def _get_posts_base_query(
        filter_deleted_media: bool = True,
    ) -> Select:
        """
        Squelette de base pour récupérer unr requete qui recup des posts avec toutes leurs infos utiles.

        Args:
            filter_deleted_media: Si True, exclut les médias soft-deleted via
                                  with_loader_criteria (actif par défaut).

        Returns:
            Select: Statement SQLAlchemy prêt à recevoir des .where() / .limit() etc.
        """
        media_options: List[Any] = [selectinload(Post.medias)]
        if filter_deleted_media:
            media_options.append(
                with_loader_criteria(PostMedia, PostMedia.deleted_at.is_(None))
            )

        return (
            select(Post)
            .options(
                joinedload(Post.author).load_only(
                    User.id,
                    User.username,
                    User.first_name,
                    User.last_name,
                    User.avatar_url,
                    User.role,
                    User.executive_role
                ),

                joinedload(Post.club).load_only(
                    Club.id,
                    Club.name,
                    Club.slug,
                    Club.logo_url,
                ),
                joinedload(Post.event).load_only(
                    Event.id,
                    Event.title,
                    Event.slug,
                    Event.start_date,
                    Event.end_date,
                    Event.status,
                ),
                *media_options,
            )
        )

    async def insert_post(
        self,
        author_id: UUID,
        academic_year_id: UUID,
        post_data: CreatePost,
    ) -> CRUDResult[Post]:
        """Crée un nouveau post en base de données.

        Args:
            author_id (UUID): ID de l'auteur, injecté depuis le token JWT.
            academic_year_id (UUID): Année académique active, injectée côté serveur.
            post_data (CreatePost): Données validées du post.

        Returns:
            CRUDResult[Post]: Le post créé ou une erreur.
        """
        try:
            stmt = (
                insert(Post)
                .values(
                    author_id=author_id,
                    academic_year_id=academic_year_id,
                )
                .returning(Post)
            )

            result = await self.db.execute(stmt)
            post = result.scalar_one()
            await self.db.commit()

            logger.info("Post créé avec succès ! id=%s", post.id)
            return CRUDResult.crud_success(post, status.HTTP_201_CREATED)

        except IntegrityError as ie:
            return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, Post)

        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)

    async def save_many_post_media(
        self, post_medias: List[PostMedia], in_transaction: bool
    ) -> CRUDResult[str]:
        """
        Enregistre une liste de medias liés à un post dans la bd
        Args:
            post_medias: Une liste d'objets PostMedia contenant les informations des medias à enregistrer
            in_transaction: Un booléen qui indique si la session doit être commit à la fin de l'opération.
             Utile pour les cas où on veut faire plusieurs opérations en une transaction

        Returns:
            Un objet CRUDResult contenant la liste des medias de post créés ou une erreur en cas d'échec.
        """
        try:
            self.db.add_all(post_medias)
            await self.db.flush()

            if in_transaction:
                logger.warning("Medias de post insert mais pas commit en Base, MODE TRANSACTION")
            else:
                await self.db.commit()
                logger.info("Commit: Medias de post sauvegarder définitivement en Base")

            return CRUDResult.crud_success('ok', status_code=status.HTTP_201_CREATED)
        except Exception as err:
            return await RepositoriesUtils.traiter_errors_en_global(
                exception=err, session=self.db, logger=logger, model_bd=PostMedia
            )

    async def save_post(
        self, post_object: Post, in_transaction: bool
    ) -> CRUDResult[Post]:
        """
        Enregistre un post dans la bd pour un user précis
        Args:

            post_object: L'objet post à inserer dans la bd
            in_transaction: Un booléen qui indique si la session doit être commit à la fin de
                l'opération. Utile pour les cas où on veut faire plusieurs opérations en une transaction
                et qu'on veut contrôler quand faire le commit

        Returns:
            Un objet CRUDResult contenant le post créé ou une erreur en cas d'échec.
        """
        try:
            self.db.add(post_object)

            await self.db.flush()

            await self.db.refresh(post_object)

            if in_transaction:
                logger.warning("Post insert mais pas commit en Base, MODE TRANSACTION")
            else:
                await self.db.commit()
                logger.info("Commit: Post sauvegarder définitivement en Base")

            return CRUDResult.crud_success(post_object, status_code=status.HTTP_201_CREATED)
        except Exception as err:
            return await RepositoriesUtils.traiter_errors_en_global(
                exception=err, session=self.db,logger=logger, model_bd=Post
            )

    async def get_post_by_id(self, post_id: UUID) -> CRUDResult[Post]:
        """Récupère un post par son ID avec ses médias et toutes les infos nécessaires pour l'affichage.

        Args:
            post_id (UUID): ID du post.

        Returns:
            CRUDResult[Post]: Le post trouvé ou une erreur 404.
        """
        try:
            requete = self._get_posts_base_query()
            requete = requete.where(
                Post.id == post_id, Post.is_published == True
            )

            result = await self.db.execute(requete)
            post = result.scalar_one_or_none()

            if post is None:
                logger.info("Post non trouvé id=%s", post_id)
                return CRUDResult.crud_error(
                    Messages.POST_NOT_FOUND,
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            

            logger.info("Post récupéré avec succès ! id=%s", post_id)
            return CRUDResult.crud_success(post, status.HTTP_200_OK)

        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)

    async def get_feed(
        self,
        academic_year_id: UUID,
        seen_post_ids: list[UUID],
        user_id: Optional[UUID],
        classe_id: Optional[UUID] = None,
        cursor: Optional[str] = None,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> CRUDResult[dict]:
        """Récupère un feed de posts paginé par curseur
        Args:
            user_id: Id de l'utilisateur
            seen_post_ids: Posts vu récupérés via Redis (pas encore dans bd)
            academic_year_id (UUID): Filtre sur l'année académique.
            cursor (Optional[str]): Curseur opaque de la page précédente.
            page_size (int): Nombre de posts par page.
            classe_id (UUID): La classe à laquelle appartient l'utilisateur (filtrage des posts ciblés classe_id ou non ciblés).

        Returns:
            CRUDResult[dict]: Feed paginé ou une erreur.
        """
        try:
            requete = self._get_posts_base_query()
            requete = requete.where(
                    Post.academic_year_id == academic_year_id,
                    Post.deleted_at.is_(None),
                    Post.is_published.is_(True),
                ).outerjoin(
                    PostViews,
                    (PostViews.post_id == Post.id) & (PostViews.user_id == user_id)
                ).where(
                    PostViews.post_id.is_(None)
                ).order_by(
                Post.created_at.desc(), Post.id.desc()
            ).limit(page_size + 1)  # +1 pour détecter has_more

            # Limiter les posts aux posts ciblant la classe de l'utilisateur ou sans cible de classe
            if classe_id:
                requete = requete.where(
                    Post.target_classe_id.in_([None, classe_id])
                )
            
            if seen_post_ids:
                ids_to_exclude = seen_post_ids[:50]
                requete = requete.where(Post.id.not_in(ids_to_exclude))

            if cursor:
                cursor_created_at, cursor_id = _decode_cursor(cursor)
                requete = requete.where(
                    (Post.created_at < cursor_created_at)
                    | (
                        (Post.created_at == cursor_created_at)
                        & (Post.id < cursor_id)
                    )
                )

            result = await self.db.execute(requete)

            # .unique() est obligatoire dès qu'on utilise joinedload
            # pour dédupliquer les lignes produites par les LEFT JOIN
            posts = result.unique().scalars().all()

            has_more = len(posts) > page_size
            items = list(posts[:page_size])

            next_cursor = None
            if has_more and items:
                last = items[-1]
                next_cursor = _encode_cursor(last.created_at, last.id)

            logger.info(
                "Feed récupéré : %d posts, has_more=%s", len(items), has_more
            )
            return CRUDResult.crud_success(
                {"items": items, "next_cursor": next_cursor, "has_more": has_more},
                status.HTTP_200_OK,
            )

        except ValueError as ve:
            # Curseur malformé
            return CRUDResult.crud_error(str(ve), status_code=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(e, self.db, logger, Post)

    async def update_post(
        self, post_id: UUID, author_id: UUID, update_data: UpdatePost
    ) -> CRUDResult[Post]:
        """Met à jour un post (PATCH sémantique - uniquement les champs fournis).

        Args:
            post_id (UUID): ID du post à modifier.
            author_id (UUID): Vérifie que c'est bien l'auteur qui modifie.
            update_data (UpdatePost): Champs à mettre à jour.

        Returns:
            CRUDResult[Post]: Le post mis à jour ou une erreur.
        """
        try:
            # Exclure les champs None (PATCH : on ne touche qu'aux champs envoyés)
            values = update_data.model_dump(exclude_none=True)

            if not values:
                return CRUDResult.crud_error(
                    "Aucune donnée à mettre à jour.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            stmt = (
                update(Post)
                .where(
                    Post.id == post_id,
                    Post.author_id == author_id,
                    Post.deleted_at.is_(None),
                )
                .values(**values)
                .returning(Post)
            )

            result = await self.db.execute(stmt)
            post = result.scalar_one_or_none()

            if post is None:
                logger.info("Post non trouvé ou non autorisé id=%s", post_id)
                return CRUDResult.crud_error(
                    Messages.POST_NOT_FOUND,
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            await self.db.commit()
            logger.info("Post mis à jour avec succès ! id=%s", post_id)
            return CRUDResult.crud_success(post, status.HTTP_200_OK)

        except IntegrityError as ie:
            return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, Post)

        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)

    async def soft_delete_post(
        self, post_id: UUID, author_id: UUID
    ) -> CRUDResult[None]:
        """Suppression douce d'un post (soft delete via deleted_at).

        Args:
            post_id (UUID): ID du post à supprimer.
            author_id (UUID): Vérifie que c'est bien l'auteur qui supprime.

        Returns:
            CRUDResult[None]: Succès ou erreur.
        """
        try:
            stmt = (
                update(Post)
                .where(
                    Post.id == post_id,
                    Post.author_id == author_id,
                    Post.deleted_at.is_(None),
                )
                .values(deleted_at=datetime.now(timezone.utc))
                .returning(Post.id)
            )

            result = await self.db.execute(stmt)
            deleted_id = result.scalar_one_or_none()

            if deleted_id is None:
                logger.info("Post non trouvé ou non autorisé id=%s", post_id)
                return CRUDResult.crud_error(
                    Messages.POST_NOT_FOUND,
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            await self.db.commit()
            logger.info("Post supprimé (soft delete) avec succès ! id=%s", post_id)
            return CRUDResult.crud_success(None, status.HTTP_200_OK)

        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)

    async def count_new_posts_since(
            self,
            academic_year_id: UUID,
            since: datetime,
        ) -> CRUDResult[int]:
            """Compte les posts créés depuis un timestamp (polling badge 60s).
    
            Requête ultra-légère COUNT(*) utilisant l'index created_at.
            Temps de réponse cible < 10ms (spec §7.3 Performance).
            """
            try:
                stmt = (
                    select(func.count(Post.id))
                    .where(
                        Post.academic_year_id == academic_year_id,
                        Post.deleted_at.is_(None),
                        Post.is_published.is_(True),
                        Post.created_at > since,
                    )
                )
                result = await self.db.execute(stmt)
                count = result.scalar_one()
                return CRUDResult.crud_success(count, status.HTTP_200_OK)
            except Exception as e:
                return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)