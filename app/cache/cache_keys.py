from typing import Optional

from app.cache.availables import AvailableCacheKeys


class CacheKey:
    """Classe représentant une clé de cache avec des placeholders pour les valeurs dynamiques,
     permettant de formater la clé avec les valeurs appropriées lors de son utilisation."""

    __keys: list[str] = []
    __can_instantiate = False
    def __init__(self, key: AvailableCacheKeys, number_of_placeholders: int, **kwargs: int | str) -> None:
        """NE JAMAIS UTILISER SVP; Constructeur privé de la classe CacheKey, qui initialise une instance avec une clé de cache spécifique,
         un nombre de placeholders et des arguments pour formater la clé"""
        if not CacheKey.__can_instantiate:
            raise PermissionError("Le constructeur de CacheKey est privé, veuillez utiliser la méthode de classe new_key pour créer une instance de CacheKey.")

        self.key = key
        self.number_of_placeholders = number_of_placeholders
        self._args: Optional[dict[str, str|int]] = kwargs.copy() if kwargs is not None else {}

    @classmethod
    def new_key(cls, key: AvailableCacheKeys, number_of_placeholders: int) -> "CacheKey":
        """
        Méthode de classe pour créer une nouvelle instance de CacheKey avec une clé de cache spécifique et un nombre de placeholders
        Args:
            key: La clé de cache à utiliser, définie dans AvailableCacheKeys, qui peut contenir des placeholders pour les valeurs dynamiques
            number_of_placeholders: Le nombre de placeholders présents dans la clé de cache, indiquant combien de valeurs dynamiques doivent être fournies lors du formatage de la clé
        Raises:
            ValueError: Si la clé de cache spécifiée a déjà été utilisée pour créer une instance de CacheKey, afin d'assurer l'unicité des clés de cache et éviter les conflits dans le cache
        Returns:
            Une nouvelle instance de CacheKey avec la clé et le nombre de placeholders spécifiés, prête à être utilisée pour formater la clé de cache lors de son utilisation dans les opérations de cache
        """
        if key.value in cls.__keys:
            raise ValueError(f"La clé de cache {key} a déjà été utilisée, veuillez choisir une clé unique pour éviter les conflits dans le cache.")

        cls.__keys.append(key.value)

        cls.__can_instantiate = True
        instance = cls(key, number_of_placeholders)
        cls.__can_instantiate = False
        return instance

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