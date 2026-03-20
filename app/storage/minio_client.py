from urllib.parse import urlparse

from minio import Minio

from app.core.config import MINIO_SERVER_URL, MINIO_USER, MINIO_PASSWORD, MINIO_PUBLIC_URL


class MinioClientFactory:
    # Client privé backend only pour les operations internes serveur vers serveurs qui ne retournent rien aux clients
    _private_client: Minio | None = None

    # Client de générations de données pour les clients, comme les URLs pré-signées, qui ne doivent pas être utilisés pour les opérations internes du serveur
    _public_client: Minio | None = None

    @classmethod
    def get_backend_client(cls) -> Minio:
        """
        Retourne une instance singleton du client Minio pour interagir avec le serveur de stockage
        Utilisez cette methode pour recuperer un client Minio pour les requetes internes qui ne retournent pas de
        données au client, si vous voulez créer une url ou des trucs dans le genre vous devez utiliser
        """
        if cls._private_client is None:
            endpoint = MINIO_SERVER_URL.replace("http://", "").replace("https://", "").rstrip("/")
            cls._private_client = Minio(endpoint=endpoint, access_key=MINIO_USER, secret_key=MINIO_PASSWORD, secure=False)
        return cls._private_client

    @classmethod
    def get_public_client(cls) -> Minio:
        """
        Retourne une instance singleton du client Minio pour interagir avec le serveur de stockage, mais configuré pour
        générer des URLs pré-signées compatibles avec le endpoint public
        Utilisez cette methode pour recuperer un client Minio pour les requetes qui génèrent des données à retourner au
        client, comme les URLs pré-signées, afin d'assurer que les URLs générées sont compatibles avec le endpoint public même si le endpoint de connexion est différent
        """
        if cls._public_client is None:
            parsed_public = urlparse(MINIO_PUBLIC_URL)
            cls._public_client = Minio(
                parsed_public.netloc,
                access_key=MINIO_USER,
                secret_key=MINIO_PASSWORD,
                secure=parsed_public.scheme == "https",
                region="us-east-1"        # Petit hack pour forcer le client à accepter les URLs pré-signées avec un endpoint différent du endpoint de connexion
            )
        return cls._public_client