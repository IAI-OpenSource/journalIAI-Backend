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
    USER_ALREADY_EXISTS = "Un utilisateur avec cet email existe déjà."
    PASSWORD_TOO_WEAK = "Le mot de passe doit contenir au moins 8 caractères, une majuscule, une minuscule et un chiffre."
    INVALID_EMAIL_FORMAT = "Format d'email invalide."
    ACCOUNT_CREATED_SUCCESSFULLY = "Compte créé avec succès."
    LOGIN_SUCCESSFUL = "Connexion réussie."
    LOGOUT_SUCCESSFUL = "Déconnexion réussie."
    PROFILE_UPDATED_SUCCESSFULLY = "Profil mis à jour avec succès."
    INVALID_SESSION = "Session invalide"