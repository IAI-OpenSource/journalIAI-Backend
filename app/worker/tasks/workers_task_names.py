from enum import StrEnum


class WorkersTaskNames(StrEnum):
    """
    Classe pour centraliser les noms des tâches Celery utilisées dans l'application pour éviter les erreurs de frappe
    et faciliter la maintenance. Chaque nom de tâche est défini comme une constante de classe.
    """
    SAVE_AUDIT_LOG = "save_audit_log"
    PROCESS_MEDIA  = "process_media"