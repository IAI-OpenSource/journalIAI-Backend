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

GET_POST_ROUTE_DESCRIPTION: str = ("Récupère un post par son ID, le résultat inclut les informations du post ainsi que"
                                   " les médias associés (s'il y en a) et les informations de vue pour l'utilisateur"
                                   " courant (si connecté)")

STORY_INTENT_ROUTE_DESCRIPTION: str = """Endpoint pour générer un intent d'upload de média pour une story, 
en fournissant les informations nécessaires.


# **Petits détails subtils sur la route :**

Dans le schema d'entrée si `only_for_a_class` est `true` alors la story est marqué comme une
story de classe (pour que cet argument puisse etre `true` il faudraitt que l'utilisateur ourant soit un délégué
de classe. Si `club_id` est fourni alors la story est marqué comme une story de club.
Si ces deux options ne sont pas vérifiés alors la story est consiférée comme une simple story utilisateur
"""

STORY_FEED_ROUTE_DESCRIPTION: str = """
Récupère le feed paginé de groupes de stories.

# **Petits détails subtils sur la route :**

Les stories sont regroupées par groupe, implicitement un groupe c'est une bulle style Instagram qui peut contenir une
ou plusieurs stories. Les groupes sont triés par date de mise à jour (plus récents en premier), actu y'a trois types de
groupes : 

- `USER_GROUP` : groupe de stories d'un utilisateur, visible par tous les utilisateurs
- `CLUB_GROUP` : groupe de stories d'un club, visible par tous les utilisateurs
- `CLASSE_GROUP` : groupe de stories d'une classe, visible seulement par les utilisateurs de cette classe

Y'a d'autres trucs aussi, il faut checker le schéma, s'il y'a zone d'ombre **DM** !!!
"""