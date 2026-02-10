# Github Copilot Instructions for Git Commits

Les messages de commit doivent être en Français clairs, concis et suivre une structure cohérente pour faciliter la compréhension de l’historique du projet. Voici les instructions pour rédiger des messages de commit efficaces :
1. Structure du message de commit
   - Le message de commit doit être composé d’un titre et d’une description optionnelle.
   - Le titre doit être court (50 caractères maximum) et résumer l’intention du commit.
   - La description peut être plus détaillée et expliquer le pourquoi du changement, les étapes suivies, ou tout autre contexte pertinent.
   - Exemple de structure :
   ```
   feat: Ajouter une nouvelle fonctionnalité de recherche
    - Permet aux utilisateurs de rechercher des articles par mots-clés.
    ```
2. Types de commit
   - Utilisez des types de commit pour catégoriser les changements. Voici quelques types couramment utilisés :
     - feat: pour les nouvelles fonctionnalités
     - fix: pour les corrections de bugs
     - docs: pour les modifications de documentation
     - style: pour les changements de formatage ou de style de code
     - refactor: pour les changements de code qui n’ajoutent pas de fonctionnalités ni ne corrigent de bugs
     - test: pour les ajouts ou modifications de tests
     - chore: pour les tâches de maintenance ou les changements qui n’affectent pas le code de production
3. Rédaction du message de commit
   - Soyez précis et évitez les messages vagues comme "mise à jour" ou "correction".
   - Expliquez le pourquoi du changement, pas seulement le quoi.
   - Si le commit résout un problème spécifique, mentionnez-le en utilisant des références (ex: "fix: corrige le bug #123").
   - Bien faire le titre du commit (ex: "Ajout d'une nouvelle fonctionnalité" au lieu de "Ajouté une nouvelle fonctionnalité").
4. Exemples de messages de commit
   - feat: Ajout d'une nouvelle fonctionnalité de recherche
   - fix: Correction d'un bug dans la validation des formulaires
   - docs: Mise à jour de la documentation pour la nouvelle API
   - style: Reformatage du code selon les normes PEP8
   - refactor: Refactorisation du module de gestion des utilisateurs pour améliorer la lisibilité
   - test: Ajout de tests unitaires pour la nouvelle fonctionnalité de recherche
   - chore: Mise à jour des dépendances du projet