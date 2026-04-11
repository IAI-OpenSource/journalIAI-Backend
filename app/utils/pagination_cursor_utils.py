from base64 import urlsafe_b64encode, urlsafe_b64decode
from datetime import datetime
from json import dumps, loads
from uuid import UUID


class PaginationCursorUtils:

    @staticmethod
    def _encode(payload: dict) -> str:
        """
        Encode un dictionnaire de données en une chaîne de caractères utilisable comme curseur de pagination.
        Args:
            payload: Un dictionnaire contenant les données à encoder.

        Returns:
            str: Un encoding base64 du dictionnaire de données.
        """

        raw = dumps(payload, separators=(",", ":"))
        return urlsafe_b64encode(raw.encode()).decode()

    @staticmethod
    def _decode(payload: str) -> dict:
        """
        Decode une chaîne de caractères encodée en un dictionnaire de données.
        Args:
            payload: Une chaîne de caractères encodée représentant les données du curseur.

        Returns:
            dict: Un dictionnaire contenant les données décodées du curseur.
        """

        decoded_bytes = urlsafe_b64decode(payload.encode())
        decoded_str = decoded_bytes.decode()
        return loads(decoded_str)

    @classmethod
    def encode_pagination_cursor(cls, last_item_id: UUID, secondary_dateable_attribute: datetime) -> str:
        """
        Encode un curseur de pagination à partir de l'ID du dernier élément et d'un attribut de date secondaire.
        Args:
            last_item_id: L'ID du dernier élément de la page actuelle.
            secondary_dateable_attribute: Un attribut de date utilisé pour garantir un ordre stable

        Returns:
            str: Un encoding base64 du curseur de pagination.
        """

        payload = {
            "dateable": secondary_dateable_attribute.isoformat(),
            "id": str(last_item_id),
        }

        return cls._encode(payload)

    @classmethod
    def decode_pagination_cursor(cls, payload: str) -> tuple[UUID, datetime]:
        """
        Decode un curseur de pagination encodé pour extraire les données de l'ID et de la date.
        Args:
            payload: Une chaîne de caractères encodée représentant le curseur de pagination.

        Returns:
            tuple[UUID, datetime]: Un tuple contenant l'ID du dernier élément et l'attribut de date décodés du curseur.
        """
        try:
            decoded = cls._decode(payload)


            return UUID(decoded["id"]), datetime.fromisoformat(decoded["dateable"])
        except Exception:
            raise ValueError("Curseur de pagination invalide.")