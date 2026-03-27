def add_all_tasks():
    """
    Permet d'importer tous les tasks pour que celery puisse les découvrir et les exécuter.
    """
    from app.worker.tasks.audit_task import create_audit_log
    from app.worker.tasks.video_process_task import process_video_task
    from app.worker.tasks.image_process_task import process_image_task
    from app.worker.tasks.excel_task import import_students_task
