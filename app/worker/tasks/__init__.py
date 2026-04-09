def add_all_tasks():
    """
    Permet d'importer tous les tasks pour que celery puisse les découvrir et les exécuter.
    """
    from app.worker.tasks.audit_task import create_audit_log
    from app.worker.tasks.excel_task import import_students_task
    from app.worker.tasks.post_many_media_process_task import process_media_upload_task
    from app.worker.tasks.daily_synchronize_post_views_task import synchronize_post_view
    from app.worker.tasks.send_jeton_email_task import send_jetons_email_orchestrator
    from app.worker.tasks.send_jeton_email_task import send_single_email_task
    from app.worker.tasks.story_media_process_task import process_story_upload_task
