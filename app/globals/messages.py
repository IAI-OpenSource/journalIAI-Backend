# Ce fichier contient les messages d'erreur et de succès utilisés dans l'application
# Cela permet de centraliser la gestion des messages et de faciliter leur maintenance.

class Messages:
    # Messages d'erreur généraux
    INTERNAL_SERVER_ERROR = "Une erreur interne est survenue. Veuillez réessayer plus tard."
    NOT_FOUND = "Ressource non trouvée."
    UNAUTHORIZED = "Non autorisé. Veuillez vous connecter."
    FORBIDDEN = "Accès interdit. Vous n'avez pas les permissions nécessaires."
    BAD_REQUEST = "Requête invalide. Veuillez vérifier les données envoyées."

    # Messages spécifiques
    USER_NOT_FOUND = "Utilisateur non trouvé."
    INVALID_CREDENTIALS = "Identifiants invalides."
    DELETED_USER = "Compte Utilisateur est supprimé"
    USER_ALREADY_EXISTS = "Un utilisateur avec cet email existe déjà."
    PSWD_TOO_WEAK = "Le mot de passe doit contenir au moins 8 caractères, une majuscule, une minuscule et un chiffre."
    INVALID_EMAIL_FORMAT = "Format d'email invalide."
    ACCOUNT_CREATED_SUCCESSFULLY = "Compte créé avec succès."
    LOGIN_SUCCESSFUL = "Connexion réussie."
    LOGOUT_SUCCESSFUL = "Déconnexion réussie."
    PROFILE_UPDATED_SUCCESSFULLY = "Profil mis à jour avec succès."
    INVALID_SESSION = "Session invalide"

    EVENT_SERVICE = "Service Events"
    EVENT_NOT_FOUND = "Event non trouvé."
    DELETED_EVENT = "Event est supprimé"
    EVENTS_NOT_FOUND = "Aucun event trouver" #Si il y a aucun event en cours 
    EVENT_DELETE_FAILED = "Erreur lors de la suppression de l'événement"
    EVENT_PAGINATION_ERROR = "Erreur validation events paginés"
    EVENT_DELETE_SUCCESS = "Event supprimé avec succès"
    EVENT_UPDATE_SUCCES = "Event mis a jour avec succès"
    EVENT_CREATE_SUCCES = "Event créé avec succès"
    EVENT_ALREADY_EXISTS = 'Evenement deja existant'

    ERROR_UPLOAD_URL_GENERATION = "Erreur lors de la génération de l'URL d'upload"
    VIDEO_UPLOAD_INTENT_SAVED = "Intent d'upload video enregistré avec succès"
    ERROR_MEDIA_UPLOAD_INTENT_NOT_FOUND = "Intent d'upload média expirée ou inexistant"
    
    # Messages des noms des services 
    INSERT_SESSSION = "Service: Insertion Session"
    DELETE_SESSION = "Service: Suppression Session"
    READ_SESSION = "Service: Lecture d'une Session"
    UNKNOWN_SERVICE = "Service Inconnu"
    REGISTRATION_JETON = "Régistration de jeton"
    READ_REGISTRATION = "Lecture régistration jeton"
    UNAUTHORIZED_JETON = "Ce Jeton est invalide"
    USER_SERVICE = "Service Utilisateur"
    
    
    ## Message pour le cache
    CACHE_USER_NOT_FOUND = "Utilisateur non Touvé dans le cache"
    CACHE_SESSION_NOT_FOUND = "Session non trouvé dans le cache"
    READ_REGISTRATION = "Lecture régistration jeton"
