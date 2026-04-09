"""
Modèles SQLAlchemy pour la base de données.
Basé sur le schéma PostgreSQL schema_final.sql
"""

# Modèles
def add_all_tables():
    from app.db.models.registration_jeton import RegistrationJeton
    from app.db.models.user import User
    from app.db.models.club import Club
    from app.db.models.club_member import ClubMember
    from app.db.models.event import Event
    from app.db.models.post import Post
    from app.db.models.post_media import PostMedia
    from app.db.models.comment import Comment
    from app.db.models.like import Like
    from app.db.models.moderation_log import ModerationLog
    from app.db.models.notification import Notification
    from app.db.models.session import Session
    from app.db.models.audit_log import AuditLog
    from app.db.models.academic_year import AcademicYear
    from app.db.models.classe import Classe
    from app.db.models.post_views import PostViews
    from app.db.models.stories import Story
    from app.db.models.story_views import StoryViews
    from app.db.models.story_groups import StoryGroups

add_all_tables()