from dataclasses import dataclass


@dataclass
class WorkersTaskNames:
    """
    Classe pour centraliser les noms des tâches Celery utilisées dans l'application pour éviter les erreurs de frappe
    et faciliter la maintenance. Chaque nom de tâche est défini comme une constante de classe.
    """

    SAVE_AUDIT_LOG: str = "audit_log.create"

    PROCESS_VIDEO: str = "video.process_video"
