#
def add_all_tasks() :
    """
    Permet d'importer tous les tasks pour que celery puisse les découvrir et les exécuter
    Donc quand on ajoute une nouvelle tâche, il suffit de l'importer dans cette fonction pour qu'elle soit prise en compte par celery
    Si vous oubliez c'est mort
    Returns:
        Que dalle

    """
    from app.worker.tasks.audit_task import create_audit_log
    from app.worker.tasks.excel_task import import_students_task


