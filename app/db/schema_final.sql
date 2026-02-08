-- ============================================================================
-- SCHEMA POSTGRESQL - MINI FACEBOOK UNIVERSITAIRE (IAI-TOGO)
-- VERSION 2.0 - AVEC MODIFICATIONS
-- ============================================================================
-- Optimisé pour: Soft-delete, Cursor-based pagination, Scalabilité
-- ============================================================================

-- Extension pour UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Extension pour les fonctions de recherche full-text
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================================================
-- ENUMS ET TYPES
-- ============================================================================

CREATE TYPE user_role AS ENUM (
    'STUDENT',              -- Étudiant standard
    'CLUB_LEADER',          -- Chef de club
    'DELEGATE',             -- Délégué de classe
    'GENERAL_DELEGATE',     -- Délégué général
    'SECRETAIRE_GENERAL',   -- Secrétaire général
    'EXECUTIVE_MEMBER',     -- Membre du bureau exécutif
    'MODERATOR',            -- Modérateur
    'ADMIN',                -- Administrateur système
    'SPECTATOR'             -- Spectateur (accès limité)
);

CREATE TYPE classe_type AS ENUM (
    'TC1',                  -- Tronc Commun 1
    'TC2',                  -- Tronc Commun 2
    'GLSI_3',               -- Génie Logiciel et Systèmes Informatiques 3
    'ASR_3',                -- Administration Systèmes et Réseaux 3
    'MTWI_3'                -- Multimédia, Technologies Web et Images 3
);

CREATE TYPE club_members_type AS ENUM (
    'LEAD',                 -- Leader du club
    'CO_LEAD',              -- Co-leader du club
    'EXECUTIVE_MEMBER',     -- Membre du bureau exécutif
    'SIMPLE_MEMBER'         -- Membre simple
);

CREATE TYPE post_type AS ENUM (
    'TEXT',                 -- Texte simple
    'IMAGE',                -- Image unique
    'VIDEO',                -- Vidéo unique
    'CAROUSSEL'             -- Carrousel (multiple images/vidéos)
);

CREATE TYPE media_type AS ENUM (
    'IMAGE',
    'VIDEO'
);

CREATE TYPE moderation_action_type AS ENUM (
    'DELETE_POST',
    'DELETE_COMMENT',
    'WARN_USER',
    'SUSPEND_USER',
    'RESTORE_POST',
    'RESTORE_COMMENT'
);

CREATE TYPE event_status AS ENUM (
    'DRAFT',
    'PUBLISHED',
    'ONGOING',
    'COMPLETED',
    'CANCELLED'
);

-- ============================================================================
-- TABLE: registration_jeton
-- Jetons d'inscription pré-générés pour les étudiants
-- ============================================================================
CREATE TABLE registration_jeton (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    jeton VARCHAR(255) NOT NULL,

    -- Informations de l'étudiant
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    role user_role NOT NULL DEFAULT 'STUDENT',
    classe classe_type NOT NULL,

    -- Suivi d'utilisation
    used_at TIMESTAMPTZ,
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Contraintes
    CONSTRAINT uq_registration_jeton_jeton UNIQUE (jeton)
);

-- Index pour recherche rapide par jeton
CREATE INDEX idx_registration_jeton_jeton ON registration_jeton(jeton)
    WHERE used_at IS NULL;

-- Index pour jetons non utilisés (pour stats)
CREATE INDEX idx_registration_jeton_unused ON registration_jeton(used_at)
    WHERE used_at IS NULL;

-- Index pour jetons par classe
CREATE INDEX idx_registration_jeton_classe ON registration_jeton(classe, added_at DESC);

COMMENT ON TABLE registration_jeton IS 'Jetons pré-générés pour l''inscription des étudiants';
COMMENT ON COLUMN registration_jeton.jeton IS 'Code unique fourni à l''étudiant pour s''inscrire';
COMMENT ON COLUMN registration_jeton.used_at IS 'Date d''utilisation du jeton (NULL si non utilisé)';

-- ============================================================================
-- TABLE: users
-- Tous les utilisateurs de la plateforme
-- ============================================================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL,
    username VARCHAR(50) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,

    -- Informations personnelles
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    bio TEXT,
    avatar_url VARCHAR(500),           -- URL MinIO
    classe classe_type NOT NULL,

    -- Rôle et permissions
    role user_role NOT NULL DEFAULT 'STUDENT',
    can_post BOOLEAN NOT NULL DEFAULT FALSE,

    -- MFA (Google Authenticator)
    mfa_secret VARCHAR(255),
    mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE,

    -- Métadonnées
    access_jeton UUID,                 -- Référence au jeton d'inscription utilisé
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    -- Soft delete
    deleted_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMPTZ,

    -- Contraintes
    CONSTRAINT uq_users_email UNIQUE (email),
    CONSTRAINT uq_users_username UNIQUE (username),
    CONSTRAINT fk_users_access_jeton FOREIGN KEY (access_jeton)
        REFERENCES registration_jeton(id) ON DELETE SET NULL,
    CONSTRAINT chk_users_bio_length CHECK (
        bio IS NULL OR LENGTH(bio) <= 500
    )
);

-- Index pour pagination cursor-based et recherche
CREATE INDEX idx_users_created_at_id ON users(created_at DESC, id)
    WHERE deleted_at IS NULL;

CREATE INDEX idx_users_email ON users(email)
    WHERE deleted_at IS NULL;

CREATE INDEX idx_users_username ON users(username)
    WHERE deleted_at IS NULL;

CREATE INDEX idx_users_role ON users(role)
    WHERE deleted_at IS NULL;

CREATE INDEX idx_users_can_post ON users(can_post)
    WHERE deleted_at IS NULL AND can_post = TRUE;

CREATE INDEX idx_users_classe ON users(classe)
    WHERE deleted_at IS NULL;

CREATE INDEX idx_users_access_jeton ON users(access_jeton)
    WHERE access_jeton IS NOT NULL;

-- Index pour soft delete
CREATE INDEX idx_users_deleted_at ON users(deleted_at)
    WHERE deleted_at IS NOT NULL;

COMMENT ON TABLE users IS 'Utilisateurs de la plateforme (étudiants, modérateurs, etc.)';
COMMENT ON COLUMN users.username IS 'Nom d''utilisateur unique (3-50 caractères alphanumériques)';
COMMENT ON COLUMN users.classe IS 'Classe de l''étudiant (TC1, TC2, GLSI_3, etc.)';
COMMENT ON COLUMN users.access_jeton IS 'Jeton d''inscription utilisé pour créer ce compte';

-- ============================================================================
-- TABLE: clubs
-- Clubs et associations de l'université
-- ============================================================================
CREATE TABLE clubs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    slug VARCHAR(200) NOT NULL,
    description TEXT,
    logo_url VARCHAR(500),             -- URL MinIO
    cover_url VARCHAR(500),            -- URL MinIO

    -- Métadonnées
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    member_count INTEGER NOT NULL DEFAULT 0,

    -- Soft delete
    deleted_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Contraintes
    CONSTRAINT uq_clubs_slug UNIQUE (slug),
    CONSTRAINT chk_clubs_member_count CHECK (member_count >= 0)
);

CREATE INDEX idx_clubs_created_at_id ON clubs(created_at DESC, id)
    WHERE deleted_at IS NULL;

CREATE INDEX idx_clubs_slug ON clubs(slug)
    WHERE deleted_at IS NULL;

CREATE INDEX idx_clubs_is_active ON clubs(is_active)
    WHERE deleted_at IS NULL AND is_active = TRUE;

CREATE INDEX idx_clubs_deleted_at ON clubs(deleted_at)
    WHERE deleted_at IS NOT NULL;

COMMENT ON TABLE clubs IS 'Clubs et associations universitaires';

-- ============================================================================
-- TABLE: club_members
-- Relation entre utilisateurs et clubs
-- ============================================================================
CREATE TABLE club_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    club_id UUID NOT NULL,
    user_id UUID NOT NULL,

    -- Rôle dans le club
    role_in_club club_members_type NOT NULL DEFAULT 'SIMPLE_MEMBER',

    -- Soft delete
    deleted_at TIMESTAMPTZ,

    -- Timestamps
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Contraintes
    CONSTRAINT fk_club_members_club FOREIGN KEY (club_id)
        REFERENCES clubs(id) ON DELETE CASCADE,
    CONSTRAINT fk_club_members_user FOREIGN KEY (user_id)
        REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT uq_club_members_club_user UNIQUE (club_id, user_id)
);

CREATE INDEX idx_club_members_club_id ON club_members(club_id)
    WHERE deleted_at IS NULL;

CREATE INDEX idx_club_members_user_id ON club_members(user_id)
    WHERE deleted_at IS NULL;

CREATE INDEX idx_club_members_role_in_club ON club_members(club_id, role_in_club)
    WHERE deleted_at IS NULL AND role_in_club IN ('LEAD', 'CO_LEAD');

CREATE INDEX idx_club_members_deleted_at ON club_members(deleted_at)
    WHERE deleted_at IS NOT NULL;

COMMENT ON TABLE club_members IS 'Relation entre utilisateurs et clubs';
COMMENT ON COLUMN club_members.role_in_club IS 'Rôle du membre dans le club (LEAD, CO_LEAD, EXECUTIVE_MEMBER, SIMPLE_MEMBER)';

-- ============================================================================
-- TABLE: events
-- Événements universitaires
-- ============================================================================
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL,
    description TEXT,

    -- Détails de l'événement
    location VARCHAR(255),
    start_date TIMESTAMPTZ NOT NULL,
    end_date TIMESTAMPTZ,

     -- Hiérarchie (récursif pour sous-événements)
    parent_event_id UUID,            -- NULL = Evenements racine

    -- Médias
    cover_image_url VARCHAR(500),      -- URL MinIO

    -- Organisation
    organizer_club_id UUID,            -- Peut être organisé par un club
    status event_status NOT NULL DEFAULT 'DRAFT',

    -- Soft delete
    deleted_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at TIMESTAMPTZ,

    -- Contraintes
    CONSTRAINT fk_events_organizer_club FOREIGN KEY (organizer_club_id)
        REFERENCES clubs(id) ON DELETE SET NULL,
    CONSTRAINT uq_events_slug UNIQUE (slug),
    CONSTRAINT fk_events_parent_event FOREIGN KEY (parent_event_id)
        REFERENCES events(id) ON DELETE CASCADE,
    CONSTRAINT chk_events_dates CHECK (
        end_date IS NULL OR end_date >= start_date
    )
);

CREATE INDEX idx_events_created_at_id ON events(created_at DESC, id)
    WHERE deleted_at IS NULL;

CREATE INDEX idx_events_start_date ON events(start_date)
    WHERE deleted_at IS NULL;

CREATE INDEX idx_events_status ON events(status)
    WHERE deleted_at IS NULL;

CREATE INDEX idx_events_organizer_club_id ON events(organizer_club_id)
    WHERE deleted_at IS NULL AND organizer_club_id IS NOT NULL;

CREATE INDEX idx_events_slug ON events(slug)
    WHERE deleted_at IS NULL;

CREATE INDEX idx_events_deleted_at ON events(deleted_at)
    WHERE deleted_at IS NOT NULL;

COMMENT ON TABLE events IS 'Événements universitaires';

-- ============================================================================
-- TABLE: posts
-- Publications sur la plateforme
-- OPTIMISÉ POUR CURSOR-BASED PAGINATION
-- ============================================================================
CREATE TABLE posts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    author_id UUID NOT NULL,

    -- Contenu
    content TEXT,
    post_type post_type NOT NULL DEFAULT 'TEXT',

    -- Relations optionnelles
    event_id UUID,                     -- Post lié à un événement
    club_id UUID,                      -- Post au nom d'un club

    -- Métriques (dénormalisées pour performance)
    like_count INTEGER NOT NULL DEFAULT 0,
    comment_count INTEGER NOT NULL DEFAULT 0,

    -- Visibilité
    is_pinned BOOLEAN NOT NULL DEFAULT FALSE,
    is_published BOOLEAN NOT NULL DEFAULT TRUE,

    -- Soft delete
    deleted_at TIMESTAMPTZ,

    -- Timestamps (CRUCIAL pour cursor pagination)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at TIMESTAMPTZ,

    -- Contraintes
    CONSTRAINT fk_posts_author FOREIGN KEY (author_id)
        REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_posts_event FOREIGN KEY (event_id)
        REFERENCES events(id) ON DELETE SET NULL,
    CONSTRAINT fk_posts_club FOREIGN KEY (club_id)
        REFERENCES clubs(id) ON DELETE SET NULL,
    CONSTRAINT chk_posts_metrics CHECK (
        like_count >= 0 AND comment_count >= 0
    ),
    CONSTRAINT chk_posts_content_required CHECK (
        content IS NOT NULL OR post_type != 'TEXT'
    ),
    CONSTRAINT chk_posts_content_length CHECK (
        content IS NULL OR LENGTH(content) <= 10000
    )
);

-- INDEX STRATÉGIQUES pour cursor-based pagination
-- Feed principal: posts récents non supprimés
CREATE INDEX idx_posts_feed_pagination ON posts(created_at DESC, id DESC)
    WHERE deleted_at IS NULL AND is_published = TRUE;

-- Posts épinglés en premier
CREATE INDEX idx_posts_pinned_feed ON posts(is_pinned DESC, created_at DESC, id DESC)
    WHERE deleted_at IS NULL AND is_published = TRUE;

-- Posts par auteur (profil utilisateur)
CREATE INDEX idx_posts_by_author ON posts(author_id, created_at DESC, id DESC)
    WHERE deleted_at IS NULL;

-- Posts par club
CREATE INDEX idx_posts_by_club ON posts(club_id, created_at DESC, id DESC)
    WHERE deleted_at IS NULL AND club_id IS NOT NULL;

-- Posts par événement
CREATE INDEX idx_posts_by_event ON posts(event_id, created_at DESC, id DESC)
    WHERE deleted_at IS NULL AND event_id IS NOT NULL;

-- Posts populaires (tri par likes)
CREATE INDEX idx_posts_popular ON posts(like_count DESC, created_at DESC, id DESC)
    WHERE deleted_at IS NULL AND is_published = TRUE;

-- Soft delete
CREATE INDEX idx_posts_deleted_at ON posts(deleted_at)
    WHERE deleted_at IS NOT NULL;

COMMENT ON TABLE posts IS 'Publications sur la plateforme - optimisé pour cursor pagination';
COMMENT ON COLUMN posts.post_type IS 'Type de post: TEXT, IMAGE, VIDEO, ou CAROUSSEL';

-- ============================================================================
-- TABLE: post_media
-- Médias associés aux posts (images, vidéos)
-- ============================================================================
CREATE TABLE post_media (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id UUID NOT NULL,

    -- Détails du média
    media_type media_type NOT NULL,
    media_url VARCHAR(500) NOT NULL,   -- URL MinIO (fichier original)
    thumbnail_url VARCHAR(500),        -- URL MinIO (miniature)

    -- Métadonnées
    file_size BIGINT,                  -- En octets
    width INTEGER,
    height INTEGER,
    duration INTEGER,                  -- Pour vidéos (en secondes)

    -- Ordre d'affichage
    display_order INTEGER NOT NULL DEFAULT 0,

    -- Processing status
    is_processed BOOLEAN NOT NULL DEFAULT FALSE,

    -- Soft delete
    deleted_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Contraintes
    CONSTRAINT fk_post_media_post FOREIGN KEY (post_id)
        REFERENCES posts(id) ON DELETE CASCADE,
    CONSTRAINT chk_post_media_file_size CHECK (
        file_size IS NULL OR file_size > 0
    ),
    CONSTRAINT chk_post_media_dimensions CHECK (
        (width IS NULL AND height IS NULL) OR
        (width > 0 AND height > 0)
    ),
    CONSTRAINT chk_post_media_duration CHECK (
        (media_type = 'VIDEO' AND (duration IS NULL OR duration > 0)) OR
        (media_type = 'IMAGE' AND duration IS NULL)
    ),
    CONSTRAINT chk_post_media_display_order CHECK (
        display_order >= 0
    )
);

CREATE INDEX idx_post_media_post_id ON post_media(post_id, display_order)
    WHERE deleted_at IS NULL;

CREATE INDEX idx_post_media_is_processed ON post_media(is_processed)
    WHERE deleted_at IS NULL AND is_processed = FALSE;

CREATE INDEX idx_post_media_deleted_at ON post_media(deleted_at)
    WHERE deleted_at IS NOT NULL;

COMMENT ON TABLE post_media IS 'Médias associés aux posts (images, vidéos)';
COMMENT ON COLUMN post_media.is_processed IS 'FALSE tant que Celery n''a pas traité le média';

-- ============================================================================
-- TABLE: comments
-- Commentaires et réponses (structure récursive)
-- OPTIMISÉ POUR CURSOR-BASED PAGINATION
-- ============================================================================
CREATE TABLE comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id UUID NOT NULL,
    author_id UUID NOT NULL,

    -- Hiérarchie (récursif pour réponses)
    parent_comment_id UUID,            -- NULL = commentaire racine

    -- Contenu
    content TEXT NOT NULL,

    -- Métriques
    like_count INTEGER NOT NULL DEFAULT 0,
    reply_count INTEGER NOT NULL DEFAULT 0,

    -- Soft delete
    deleted_at TIMESTAMPTZ,

    -- Timestamps (CRUCIAL pour cursor pagination)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Contraintes
    CONSTRAINT fk_comments_post FOREIGN KEY (post_id)
        REFERENCES posts(id) ON DELETE CASCADE,
    CONSTRAINT fk_comments_author FOREIGN KEY (author_id)
        REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_comments_parent FOREIGN KEY (parent_comment_id)
        REFERENCES comments(id) ON DELETE CASCADE,
    CONSTRAINT chk_comments_content_length CHECK (
        LENGTH(content) <= 2000
    ),
    CONSTRAINT chk_comments_metrics CHECK (
        like_count >= 0 AND reply_count >= 0
    ),
    CONSTRAINT chk_comments_no_self_parent CHECK (
        parent_comment_id IS NULL OR parent_comment_id != id
    )
);

-- INDEX pour cursor-based pagination
-- Commentaires racines d'un post (tri chronologique)
CREATE INDEX idx_comments_post_root ON comments(post_id, created_at ASC, id ASC)
    WHERE deleted_at IS NULL AND parent_comment_id IS NULL;

-- Réponses à un commentaire
CREATE INDEX idx_comments_replies ON comments(parent_comment_id, created_at ASC, id ASC)
    WHERE deleted_at IS NULL AND parent_comment_id IS NOT NULL;

-- Commentaires par auteur
CREATE INDEX idx_comments_by_author ON comments(author_id, created_at DESC, id DESC)
    WHERE deleted_at IS NULL;

-- Index pour compter les commentaires d'un post (performance)
CREATE INDEX idx_comments_post_count ON comments(post_id)
    WHERE deleted_at IS NULL;

-- Soft delete
CREATE INDEX idx_comments_deleted_at ON comments(deleted_at)
    WHERE deleted_at IS NOT NULL;

COMMENT ON TABLE comments IS 'Commentaires et réponses (structure récursive)';

-- ============================================================================
-- TABLE: likes
-- Likes sur posts et commentaires
-- ============================================================================
CREATE TABLE likes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,

    -- Polymorphique: post OU comment
    post_id UUID,
    comment_id UUID,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Contraintes
    CONSTRAINT fk_likes_user FOREIGN KEY (user_id)
        REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_likes_post FOREIGN KEY (post_id)
        REFERENCES posts(id) ON DELETE CASCADE,
    CONSTRAINT fk_likes_comment FOREIGN KEY (comment_id)
        REFERENCES comments(id) ON DELETE CASCADE,
    CONSTRAINT chk_likes_target CHECK (
        (post_id IS NOT NULL AND comment_id IS NULL) OR
        (post_id IS NULL AND comment_id IS NOT NULL)
    ),
    CONSTRAINT uq_likes_user_post UNIQUE (user_id, post_id),
    CONSTRAINT uq_likes_user_comment UNIQUE (user_id, comment_id)
);

-- Index pour vérifier si un utilisateur a liké
CREATE INDEX idx_likes_user_post ON likes(user_id, post_id)
    WHERE post_id IS NOT NULL;

CREATE INDEX idx_likes_user_comment ON likes(user_id, comment_id)
    WHERE comment_id IS NOT NULL;

-- Index pour compter les likes
CREATE INDEX idx_likes_post_id ON likes(post_id)
    WHERE post_id IS NOT NULL;

CREATE INDEX idx_likes_comment_id ON likes(comment_id)
    WHERE comment_id IS NOT NULL;

-- Index pour pagination des likes d'un post/comment
CREATE INDEX idx_likes_post_pagination ON likes(post_id, created_at DESC, id DESC)
    WHERE post_id IS NOT NULL;

CREATE INDEX idx_likes_comment_pagination ON likes(comment_id, created_at DESC, id DESC)
    WHERE comment_id IS NOT NULL;

COMMENT ON TABLE likes IS 'Système de likes polymorphique (posts et comments)';

-- ============================================================================
-- TABLE: moderation_logs
-- Logs des actions de modération
-- ============================================================================
CREATE TABLE moderation_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    moderator_id UUID NOT NULL,

    -- Action et cible
    action moderation_action_type NOT NULL,
    target_type VARCHAR(50) NOT NULL,  -- 'post', 'comment', 'user'
    target_id UUID NOT NULL,

    -- Détails
    reason TEXT NOT NULL,
    moderation_metadata JSONB,                    -- Données supplémentaires

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Contraintes
    CONSTRAINT fk_moderation_logs_moderator FOREIGN KEY (moderator_id)
        REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_moderation_logs_moderator ON moderation_logs(moderator_id, created_at DESC);
CREATE INDEX idx_moderation_logs_target ON moderation_logs(target_type, target_id, created_at DESC);
CREATE INDEX idx_moderation_logs_created_at ON moderation_logs(created_at DESC);

COMMENT ON TABLE moderation_logs IS 'Historique des actions de modération';

-- ============================================================================
-- TABLE: notifications
-- Système de notifications
-- ============================================================================
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,

    -- Type et contenu
    type VARCHAR(50) NOT NULL,         -- 'comment', 'like', 'mention', 'event', etc.
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,

    -- Lien vers la ressource
    resource_type VARCHAR(50),         -- 'post', 'comment', 'event', etc.
    resource_id UUID,

    -- État
    is_read BOOLEAN NOT NULL DEFAULT FALSE,

    -- Soft delete
    deleted_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    read_at TIMESTAMPTZ,

    -- Contraintes
    CONSTRAINT fk_notifications_user FOREIGN KEY (user_id)
        REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT chk_notifications_title_not_empty CHECK (
        LENGTH(TRIM(title)) > 0
    ),
    CONSTRAINT chk_notifications_message_not_empty CHECK (
        LENGTH(TRIM(message)) > 0
    ),
    CONSTRAINT chk_notifications_read_at CHECK (
        (is_read = FALSE AND read_at IS NULL) OR
        (is_read = TRUE AND read_at IS NOT NULL)
    )
);

-- Index pour récupérer les notifications non lues
CREATE INDEX idx_notifications_user_unread ON notifications(user_id, is_read, created_at DESC)
    WHERE deleted_at IS NULL AND is_read = FALSE;

-- Index pour pagination des notifications
CREATE INDEX idx_notifications_user_pagination ON notifications(user_id, created_at DESC, id DESC)
    WHERE deleted_at IS NULL;

-- Soft delete
CREATE INDEX idx_notifications_deleted_at ON notifications(deleted_at)
    WHERE deleted_at IS NOT NULL;

COMMENT ON TABLE notifications IS 'Système de notifications';

-- ============================================================================
-- TABLE: sessions
-- Sessions utilisateurs (pour gestion de l'authentification)
-- ============================================================================
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,

    -- Détails de session
    token_hash VARCHAR(255) NOT NULL,
    refresh_token_hash VARCHAR(255),

    -- Métadonnées
    ip_address INET,
    user_agent TEXT,

    -- Expiration
    expires_at TIMESTAMPTZ NOT NULL,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_activity_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Contraintes
    CONSTRAINT fk_sessions_user FOREIGN KEY (user_id)
        REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT uq_sessions_token_hash UNIQUE (token_hash),
    CONSTRAINT chk_sessions_expires_after_creation CHECK (
        expires_at > created_at
    )
);

CREATE INDEX idx_sessions_user_id ON sessions(user_id, last_activity_at DESC);
CREATE INDEX idx_sessions_token_hash ON sessions(token_hash);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at)
    WHERE expires_at > NOW();

COMMENT ON TABLE sessions IS 'Sessions utilisateurs (authentification)';

-- ============================================================================
-- TABLE: audit_logs
-- Logs d'audit pour traçabilité
-- ============================================================================
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID,

    -- Action
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID,

    -- Données
    old_values JSONB,
    new_values JSONB,

    -- Métadonnées
    ip_address INET,
    user_agent TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Contraintes
    CONSTRAINT fk_audit_logs_user FOREIGN KEY (user_id)
        REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id, created_at DESC);
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id, created_at DESC);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);

COMMENT ON TABLE audit_logs IS 'Logs d''audit pour traçabilité';
-- ============================================================================
-- FIN DU SCHÉMA
-- ============================================================================