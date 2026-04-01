## Ce fichier contient le repository de la table posts (et post_media / post_views).
## Vous y trouverez les requêtes base de données.

import base64
import logging
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID

from sqlalchemy import insert, select, update, func,text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import  status
from app.db.models.post import Post
from app.db.models.post_media import PostMedia
from app.db.models.post_views import PostViews
from app.schemas.post_schemas import CreatePost, UpdatePost, ConfirmMediaUpload
from . import CRUDResult
from app.globals.messages import Messages
from .repositories_utils import RepositoriesUtils


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
                    **post_data.model_dump(),
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
        Enregistre une liste de media liés à un post dans la bd
        Args:
            post_medias: Une liste d'objets PostMedia contenant les informations des medias à enregistrer
            in_transaction: Un booléen qui indique si la session doit être commit à la fin de l'opération.
             Utile pour les cas où on veut faire plusieurs opérations en une transaction

        Returns:
            Un objet CRUDResult contenant la liste des media de post créés ou une erreur en cas d'échec.
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
        """Récupère un post par son ID avec ses médias (selectinload).

        Args:
            post_id (UUID): ID du post.

        Returns:
            CRUDResult[Post]: Le post trouvé ou une erreur 404.
        """
        try:
            stmt = (
                select(Post)
                .where(Post.id == post_id, Post.deleted_at.is_(None))
                .options(selectinload(Post.media))
            )

            result = await self.db.execute(stmt)
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
        seen_post_ids: list[str],
        cursor: Optional[str] = None,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> CRUDResult[dict]:
        """Récupère un feed de posts paginé par curseur (cursor-based pagination).

        Utilise l'index idx_posts_feed_pagination (created_at DESC, id DESC).
        Retourne un dict avec les clés : items, next_cursor, has_more.

        Args:
            seen_post_ids:
            academic_year_id (UUID): Filtre sur l'année académique.
            cursor (Optional[str]): Curseur opaque de la page précédente.
            page_size (int): Nombre de posts par page.

        Returns:
            CRUDResult[dict]: Feed paginé ou une erreur.
        """
        try:
            stmt = (
                select(Post)
                .where(
                    Post.academic_year_id == academic_year_id,
                    Post.deleted_at.is_(None),
                    Post.is_published.is_(True),
                )
                .options(selectinload(Post.media))
                .order_by(Post.created_at.desc(), Post.id.desc())
                .limit(page_size + 1)  # +1 pour détecter has_more
            )
            
            # Exclusion posts vus (spec §4 Étape 4B)
            # Si liste vide → condition ignorée (spec §9.1)
            if seen_post_ids:
                # Tronquer à 1000 pour éviter clause WHERE trop lourde (spec §9.5)
                ids_to_exclude = seen_post_ids[:1000]
                uuid_ids = [UUID(sid) for sid in ids_to_exclude]
                stmt = stmt.where(Post.id.not_in(uuid_ids))

            # Appliquer le curseur si présent
            if cursor:
                cursor_created_at, cursor_id = _decode_cursor(cursor)
                stmt = stmt.where(
                    (Post.created_at < cursor_created_at)
                    | (
                        (Post.created_at == cursor_created_at)
                        & (Post.id < cursor_id)
                    )
                )

            result = await self.db.execute(stmt)
            posts = result.scalars().all()

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
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)

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

# Fallback PostgreSQL si Redis crash

    async def get_seen_post_ids_from_db(
            self, user_id: UUID
        ) -> CRUDResult[list[str]]:
            """Récupère les posts vus depuis PostgreSQL (fallback Redis crash).
    
            Si Redis est down, on lit post_views depuis PostgreSQL
            pour les 7 derniers jours. Données potentiellement incomplètes
            (snapshot fait la nuit) mais le feed continue de fonctionner.
            """
            try:
                stmt = (
                    select(PostViews.post_id)
                    .where(
                        PostViews.user_id == user_id,
                        PostViews.viewed_at >= text("NOW() - INTERVAL '7 days'"),
                    )
                )
                result = await self.db.execute(stmt)
                post_ids = [str(row[0]) for row in result.fetchall()]
    
                logger.warning(
                    "Fallback PostgreSQL seen_posts user=%s count=%d",
                    user_id, len(post_ids),
                )
                return CRUDResult.crud_success(post_ids, status.HTTP_200_OK)
    
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



    # PostMedia

    async def insert_post_media(
        self, post_id: UUID, media_data: ConfirmMediaUpload
    ) -> CRUDResult[PostMedia]:
        """Crée une entrée PostMedia après confirmation d'upload MinIO.

        is_processed est False par défaut — le worker de traitement
        génèrera le thumbnail et passera is_processed à True.

        Args:
            post_id (UUID): ID du post auquel rattacher le média.
            media_data (ConfirmMediaUpload): Données de confirmation d'upload.

        Returns:
            CRUDResult[PostMedia]: Le média créé ou une erreur.
        """
        try:
            stmt = (
                insert(PostMedia)
                .values(
                    post_id=post_id,
                    media_type=media_data.media_type,
                    media_url=media_data.object_key,
                    file_size=media_data.file_size,
                    width=media_data.width,
                    height=media_data.height,
                    duration=media_data.duration,
                    display_order=media_data.display_order,
                )
                .returning(PostMedia)
            )

            result = await self.db.execute(stmt)
            media = result.scalar_one()
            await self.db.commit()

            logger.info("PostMedia créé avec succès ! id=%s", media.id)
            return CRUDResult.crud_success(media, status.HTTP_201_CREATED)

        except IntegrityError as ie:
            return await RepositoriesUtils.traiter_integrity_error(
                ie, self.db, logger, PostMedia
            )

        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)

    async def mark_media_as_processed(
        self, media_id: UUID, thumbnail_url: str
    ) -> CRUDResult[PostMedia]:
        """Marque un média comme traité et enregistre l'URL du thumbnail.

        Appelé par le worker après génération du thumbnail MinIO.

        Args:
            media_id (UUID): ID du média traité.
            thumbnail_url (str): Clé objet MinIO du thumbnail généré.

        Returns:
            CRUDResult[PostMedia]: Le média mis à jour ou une erreur.
        """
        try:
            stmt = (
                update(PostMedia)
                .where(PostMedia.id == media_id, PostMedia.deleted_at.is_(None))
                .values(is_processed=True, thumbnail_url=thumbnail_url)
                .returning(PostMedia)
            )

            result = await self.db.execute(stmt)
            media = result.scalar_one_or_none()

            if media is None:
                return CRUDResult.crud_error(
                    Messages.MEDIA_NOT_FOUND,
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            await self.db.commit()
            logger.info("PostMedia marqué comme traité ! id=%s", media_id)
            return CRUDResult.crud_success(media, status.HTTP_200_OK)

        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)

    # PostViews

    async def insert_post_view(
        self, post_id: UUID, user_id: UUID
    ) -> CRUDResult[None]:
        """Enregistre la vue d'un post par un utilisateur.

        La clé primaire composite (post_id, user_id) garantit l'unicité —
        une deuxième vue du même utilisateur déclenche une IntegrityError
        gérée silencieusement (idempotent).

        Args:
            post_id (UUID): ID du post vu.
            user_id (UUID): ID de l'utilisateur qui a vu le post.

        Returns:
            CRUDResult[None]: Succès (même si déjà vu) ou erreur inattendue.
        """
        try:
            stmt = insert(PostViews).values(post_id=post_id, user_id=user_id)
            await self.db.execute(stmt)
            await self.db.commit()

            logger.info("Vue enregistrée post_id=%s user_id=%s", post_id, user_id)
            return CRUDResult.crud_success(None, status.HTTP_201_CREATED)

        except IntegrityError:
            # Post déjà vu par cet utilisateur — comportement idempotent attendu
            await self.db.rollback()
            logger.debug(
                "Vue déjà enregistrée (idempotent) post_id=%s user_id=%s",
                post_id,
                user_id,
            )
            return CRUDResult.crud_success(None, status.HTTP_200_OK)

        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)

    async def batch_insert_post_views(
        self, user_id: UUID, post_ids: list[UUID]
    ) -> CRUDResult[int]:
        """Insert batch de vues pour le snapshot Redis → PostgreSQL (spec §8.2).
 
        ON CONFLICT DO NOTHING assure l'idempotence si déjà snapé.
        """
        if not post_ids:
            return CRUDResult.crud_success(0, status.HTTP_200_OK)
        try:
            rows = [{"user_id": user_id, "post_id": pid} for pid in post_ids]
            stmt = (
                insert(PostViews)
                .values(rows)
                .on_conflict_do_nothing(index_elements=["post_id", "user_id"])
            )
            result = await self.db.execute(stmt)
            await self.db.commit()
            return CRUDResult.crud_success(result.rowcount, status.HTTP_200_OK)
        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)