MEDIA_INTENT_ROUTE_SUMMARY: str = """
Endpoint pour générer un intent d'upload de média pour un post, en fournissant les informations nécessaires
pour initier des uploads de médias. L'endpoint valide les données d'entrée, génère des URLs d'uploads
pré-signée pour chaque fichier demandé, c'est sur ces Urls que vous allez upload les fichiers média du post
"""

MEDIA_INTENT_CONFIRM_ROUTE_SUMMARY: str = """
Route pour confirmé l'upload du post média, vous ferrez une requete
sur cette route après avoir uploadé totalement les fichiers sur les urls délivrés précedemment
"""