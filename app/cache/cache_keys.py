from typing import Optional

from app.cache.availables import AvailableCacheKeys


class CacheKey:
    """Classe représentant une clé de cache avec des placeholders pour les valeurs dynamiques,
     permettant de formater la clé avec les valeurs appropriées lors de son utilisation."""

    def __init__(self, key: AvailableCacheKeys, number_of_placeholders: int, **kwargs: int | str) -> None:
        """
        Constructeur de la classe CacheKey, qui initialise une clé de cache avec un nombre spécifié de placeholders
        pour les valeurs dynamiques.
        Args:
            key: La clé de cache à utiliser, définie dans AvailableCacheKeys, qui peut contenir des placeholders pour les valeurs dynamiques
            number_of_placeholders: Le nombre de placeholders présents dans la clé de cache, indiquant combien de valeurs dynamiques doivent être fournies lors du formatage de la clé
        """
        self.key = key
        self.number_of_placeholders = number_of_placeholders
        self._args: Optional[dict[str, str|int]] = kwargs.copy() if kwargs is not None else {}

    def set_arguments(self, **kwargs: int | str) -> "CacheKey":
        """
        Définit les arguments à utiliser pour formater la clé de cache, en vérifiant que le nombre d'arguments fournis correspond au nombre de placeholders attendus
        Args:
            **kwargs: Les arguments à utiliser pour formater la clé de cache, où les clés correspondent aux noms des placeholders dans la clé
        Returns:
            Une nouvelle instance de CacheKey avec les arguments définis, prête à être utilisée pour formater la clé de cache lors de son utilisation dans les opérations de cache
        """
        if len(kwargs) != self.number_of_placeholders:
            raise ValueError(f"Nombre d'arguments fourni ({len(kwargs)}) ne correspond pas au nombre "
                             f"de placeholders attendu ({self.number_of_placeholders}) pour la clé {self.key}")

        return CacheKey(self.key, self.number_of_placeholders, **kwargs)

    @property
    def args(self) -> dict[str, str | int]:
        return self._args