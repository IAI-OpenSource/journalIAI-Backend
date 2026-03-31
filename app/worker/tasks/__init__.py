def add_all_tasks():
    """
    Permet d'importer tous les tasks pour que celery puisse les découvrir et les exécuter.
    """
    from app.worker.tasks.audit_task import create_audit_log
    from app.worker.tasks.excel_task import import_students_task
    from app.worker.tasks.many_media_process import process_media_upload_task
