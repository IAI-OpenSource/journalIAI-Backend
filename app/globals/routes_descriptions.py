# Fichier pour centraliser les descriptions longues de certaines routes

MEDIA_INTENT_ROUTE_DESCRIPTION: str = """
Endpoint pour générer un intent d'upload de média pour un post, en fournissant les informations nécessaires
pour initier des uploads de médias. L'endpoint valide les données d'entrée, génère des URLs d'uploads
pré-signée pour chaque fichier demandé, c'est sur ces Urls que vous allez upload les fichiers média du post
"""

MEDIA_INTENT_CONFIRM_ROUTE_DESCRIPTION: str = """
Route pour confirmé l'upload du post média, vous ferrez une requete
sur cette route après avoir uploadé totalement les fichiers sur les urls délivrés précedemment
"""

GET_FEED_ROUTE_DESCRIPTION: str = """Retourne une page du feed.

Les posts déjà vus par cet utilisateur sont automatiquement exclus
grâce au cache Redis (SET user:{id}:seen_posts).

- Première page : cursor absent
- Page suivante : passer next_cursor reçu dans la réponse précédente
- Pull-to-refresh : appeler sans cursor (efface le contexte de pagination)
"""

CREATE_TEXT_POST_ROUTE_DESCRIPTION: str ="""Crée un nouveau post Textuel, sans médias. Pour les posts avec médias c'est 
pas ici
"""
