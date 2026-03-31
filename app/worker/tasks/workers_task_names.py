from dataclasses import dataclass


@dataclass
class WorkersTaskNames:
    """
    Classe pour centraliser les noms des tâches Celery utilisées dans l'application pour éviter les erreurs de frappe
    et faciliter la maintenance. Chaque nom de tâche est défini comme une constante de classe.
    """

    SAVE_AUDIT_LOG: str = "audit_log.create"

    PROCESS_MEDIAS_UPLOAD: str = "uploads.process_medias_upload"

    IMPORT_DATA_FROM_EXCEL: str = "regstration.import_from_excel"

