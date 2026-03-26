from logging import getLogger

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.enums import PostType, MediaType
from app.db.models.post import Post
from app.db.models.post_media import PostMedia
from app.repositories import CRUDResult
from app.repositories.repositories_utils import RepositoriesUtils
from fastapi import status

logger = getLogger(__name__)


class PostVideoRepository:

    def __init__(self, bd_session : AsyncSession):
        self.bd_session = bd_session


    async def save_post_video(
        self, post_object: Post, in_transaction: bool
    ) -> CRUDResult[Post]:
        """
        Enregistre un post de type vidéo dans la bd  pour un user précis
        Args:

            post_object: L'objet post à inserer dans la bd
            in_transaction: Un booléen qui indique si la session doit être commit à la fin de
                l'opération. Utile pour les cas où on veut faire plusieurs opérations en une transaction
                et qu'on veut contrôler quand faire le commit

        Returns:
            Un objet CRUDResult contenant le post créé ou une erreur en cas d'échec.
        """
        try:
            post_object.post_type = PostType.VIDEO

            requete = insert(Post).values(**post_object).returning(Post)

            result = await self.bd_session.execute(requete)

            post = result.scalar_one()

            if in_transaction:
                logger.warning("Post vidéo insert mais pas commit en Base, MODE TRANSACTION")
            else:
                await self.bd_session.commit()
                logger.info("Commit: Post vidéo sauvegarder définitivement en Base")

            return CRUDResult.crud_success(post, status_code=status.HTTP_201_CREATED)
        except Exception as err:
            return await RepositoriesUtils.traiter_errors_en_global(
                exception=err, session=self.bd_session,logger=logger, model_bd=Post
            )

    async def save_post_media_video(
        self, post_video_media: PostMedia, in_transaction: bool
    ) -> CRUDResult[PostMedia]:
        """
        Enregistre un media de type vidéo lié à un post dans la bd
        Args:
            post_video_media: L'objet PostMedia contenant les informations du media vidéo à enregistrer
            in_transaction: Un booléen qui indique si la session doit être commit à la fin de l'opération.
             Utile pour les cas où on veut faire plusieurs opérations en une transaction

        Returns:
            Un objet CRUDResult contenant le media de post créé ou une erreur en cas d'échec.
        """
        try:
            post_video_media.media_type = MediaType.VIDEO
            requete = insert(PostMedia).values(**post_video_media).returning(PostMedia)

            result = await self.bd_session.execute(requete)

            post_media = result.scalar_one()

            if in_transaction:
                logger.warning("Media de post vidéo insert mais pas commit en Base, MODE TRANSACTION")
            else:
                await self.bd_session.commit()
                logger.info("Commit: Media de post vidéo sauvegarder définitivement en Base")

            return CRUDResult.crud_success(post_media, status_code=status.HTTP_201_CREATED)
        except Exception as err:
            return await RepositoriesUtils.traiter_errors_en_global(
                exception=err, session=self.bd_session, logger=logger, model_bd=PostMedia
            )




