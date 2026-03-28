from abc import ABC
from typing import TypeVar, Generic, Optional

T = TypeVar("T")

# Sentinel pour distinguer "data=None volontaire" (ex: delete 200)
# de "aucun argument fourni" — on ne peut pas utiliser None pour les deux cas
_MISSING = object()


class GlobalAppResult(Generic[T], ABC):
    """
    Classe Générique + Abstraite pour typer les réponses d'opérations dans tout le système.

    Elle encapsule soit une donnée de succès (data), soit un message d'erreur (error).
    data=None est autorisé sur un succès (ex: DELETE sans corps de réponse).
    """

    def __init__(self, data: Optional[T] = _MISSING, error: Optional[str] = None):
        if data is not _MISSING and error is not None:
            raise ValueError(
                "Une réponse ne peut pas contenir à la fois des données et une erreur."
            )
        if data is _MISSING and error is None:
            raise ValueError(
                "Une réponse doit contenir soit des données (même None), soit une erreur."
            )

        # _is_success est True dès qu'on a fourni data= explicitement,
        # même si sa valeur est None (cas DELETE / 204)
        self._is_success: bool = data is not _MISSING
        self._data: Optional[T] = None if data is _MISSING else data
        self._error: Optional[str] = error

    def is_success(self) -> bool:
        """Retourne True si la réponse est un succès (data fourni explicitement)."""
        return self._is_success

    def is_error(self) -> bool:
        """Retourne True si la réponse est une erreur."""
        return self._error is not None

    @property
    def data(self) -> Optional[T]:
        """
        Retourne les données de succès (peut être None pour un succès sans corps).
        Raises:
            RuntimeError: Si la réponse est une erreur.
        """
        if not self._is_success:
            raise RuntimeError(
                "Tentative d'accéder aux données sur une réponse d'erreur."
            )
        return self._data

    @property
    def error(self) -> str:
        """
        Retourne le message d'erreur.
        Raises:
            RuntimeError: Si la réponse est un succès.
        """
        if self._error is None:
            raise RuntimeError(
                "Tentative d'accéder à l'erreur sur une réponse de succès."
            )
        return self._error