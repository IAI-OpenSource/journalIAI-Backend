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
    USER_NOT_IN_CLUB = "L'utilisateur n'est pas membre du club."
    USER_CANNOT_POST_IN_CLASSE = "Vous n'avez pas les droits pour poster dans cette classe"
    USER_CANNOT_POST = "Vous n'avez pas les droits pour poster"
    USER_CANNOT_MODIFY_STORY = "Vous n'avez pas les droits pour modifier cette story."
    USER_CANNOT_POST_IN_CLUB = "Vous n'avez pas les droits pour poster dans ce club"
    ACTIVE_ACADEMIC_YEAR_NOT_FOUND = "Impossible de trouver l'année académique active, vérifier si une année académique ctive existe"
    CLUB_NOT_FOUND = "Club non trouvé."
    ACADEMIC_YEAR_NOT_FOUND = "Année académique non trouvée."
    CLASSE_NOT_FOUND = "Classe non trouvée."
    CLUB_ALREADY_EXISTS = "Le club existe déjà."
    CLUB_DELETED_SUCCESSFULLY = "Club supprimé avec succès."
    CLUB_UPDATED_SUCCESSFULLY = "Club mis à jour avec succès."
    ACADEMIC_YEAR_ALREADY_EXISTS = "Cette année académique existe déjà."
    ACADEMIC_YEAR_CREATED_SUCCESSFULLY = "Année académique créée avec succès."
    ACADEMIC_YEAR_UPDATED_SUCCESSFULLY = "Année académique mise à jour avec succès."
    ACADEMIC_YEAR_DELETED_SUCCESSFULLY = "Année académique supprimée avec succès."
    CLASSE_ALREADY_EXISTS = "Cette classe existe déjà pour l'année académique en cours."
    CLASSE_CREATED_SUCCESSFULLY = "Classe créée avec succès."
    CLASSE_UPDATED_SUCCESSFULLY = "Classe mise à jour avec succès."
    CLASSE_DELETED_SUCCESSFULLY = "Classe supprimée avec succès." 
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
    DELETE_FAILED = "Erreur lors de la suppression"
    LOGIN_NOT_FOUND = "Utilisateur ou Mot de passe incorrect"
    USER_UPDATED = "Utilisateur mis à jour avec succès"

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
    MEDIA_NOT_FOUND = "Media non trouvé."
    POST_NOT_FOUND = "Post non trouvé."
    STORY_GROUP_NOT_FOUND = "Groupe de story non trouvé"


    ERROR_UPLOAD_URL_GENERATION = "Erreur Inconnue lors de la génération des URL d'upload"
    CLUB_MEMBER_SERVICE = "Service Club Member"
    ALREADY_EXISTS = "Le memebre existe deja"
    MEMBER_DELETE_SUCCESS = "Membre supprimer avec sucsess"
    VIDEO_UPLOAD_INTENT_SAVED = "Intent d'upload video enregistré avec succès"
    ERROR_MEDIA_UPLOAD_INTENT_NOT_FOUND = "Intent d'upload média expirée ou inexistant"
    ERROR_LAUNCHING_MEDIA_PROCESSING_TASK = "Erreur lors du lancement de la tâche de traitement des médias"

    DELETED_USER = "Utilisateur déjà supprimé" 
    USER_FOUNDED = "Utilisateur récupérer avec succès !"
    
    ERROR_FILE_NOT_UPLOADED = "Le fichier {file_name} n'a pas été complètement uploadé ou est innacessible"
    ERROR_FILE_TOO_LARGE = "Le fichier dépasse la taille maximale autorisée de 100Mo."
    # Messages des noms des services 
    INSERT_SESSSION = "Service: Insertion Session"
    DELETE_SESSION = "Service: Suppression Session"
    READ_SESSION = "Service: Lecture d'une Session"
    UNKNOWN_SERVICE = "Service Inconnu"
    REGISTRATION_JETON = "Régistration de jeton"
    READ_REGISTRATION = "Lecture régistration jeton"
    UNAUTHORIZED_JETON = "Ce Jeton est invalide"
    USER_SERVICE = "Service Utilisateur"
    CLUB_SERVICE = "Service Club"
    POST_SERVICE = "Service Post"
    ACADEMIC_YEAR_SERVICE = "Service Année Académique"
    CLASSE_SERVICE = "Service Classe"
    STORY_SERVICE = "Service Story"
    
    
    ## Message pour le cache
    CACHE_USER_NOT_FOUND = "Utilisateur non Touvé dans le cache"
    CACHE_SESSION_NOT_FOUND = "Session non trouvé dans le cache"
    

    ## Message envoi de mail
    MAIL_SERVICE = "Service email"
    MAIL_ERROR = "Erreur de Connection pour l'envoi du mail"
    
    #OTP service
    OTP_SERVICE = "Service OTP"

    # Email comité
    COMITE_ETUDIANT_EMAIL = "comiteetudiantjournaliaitogo@gmail.com"