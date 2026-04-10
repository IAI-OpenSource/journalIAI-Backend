# 📊 Analyse de performance du feed de stories

## 🔍 Requêtes analysées

### Requête 1 : Feed des groupes de stories
**Cas 1 (Avec user_classe_id):**
```sql
SELECT sg.* FROM story_groups sg
WHERE sg.expires_at >= NOW()
  AND (
    sg.group_type = 'USER_GROUP'
    OR sg.group_type = 'CLUB_GROUP'
    OR (sg.group_type = 'CLASSE_GROUP' AND sg.target_classe_id = $user_classe_id)
  )
ORDER BY sg.updated_at DESC, sg.id DESC
LIMIT 11
```

**Cas 2 (Sans user_classe_id):**
```sql
SELECT sg.* FROM story_groups sg
WHERE sg.expires_at >= NOW()
  AND (sg.group_type = 'USER_GROUP' OR sg.group_type = 'CLUB_GROUP')
ORDER BY sg.updated_at DESC, sg.id DESC
LIMIT 11
```

### Requête 2 : Récupération des vues utilisateur
```sql
SELECT sv.story_id FROM story_views sv
WHERE sv.story_id = ANY($story_ids)
  AND sv.user_id = $user_id
```

---

## ⚠️ Problèmes identifiés (AVANT)

### StoryGroups
| Problème | Impact | Gravité |
|----------|--------|---------|
| `IDX_STORY_GROUPS_FEED` ne couvre pas `group_type` et `expires_at` | PostgreSQL doit filtrer en CPU après avoir lu l'index | 🔴 Haute |
| Pas d'index composite (expires_at, group_type, updated_at) | Impossible d'utiliser l'index pour le filtrage ET le tri en même temps | 🔴 Haute |
| Pas d'index spécifique pour recherche `target_classe_id` | Les requêtes avec `CLASSE_GROUP` font un full table scan | 🟠 Moyenne |

### StoryViews
| Problème | Impact | Gravité |
|----------|--------|---------|
| `user_id` n'est pas dans l'index `IDX_STORY_VIEWS_FEED_PAGINATION` | Index seek sur `story_id`, puis filtre CPU pour `user_id` | 🟡 Basse |

---

## ✅ Solutions implémentées (APRÈS)

### 1. Index optimisé pour le feed principal
**Nom:** `IDX_STORY_GROUPS_FEED_OPTIMIZED`
```sql
CREATE INDEX idx_story_groups_feed_optimized 
ON story_groups(group_type, expires_at DESC, updated_at DESC, id DESC)
WHERE is_active = TRUE;
```

**Avantages:**
- ✅ PostgreSQL peut filtrer par `group_type` et `expires_at` dans l'index
- ✅ Le tri par `updated_at DESC, id DESC` est déjà dans l'ordre de l'index
- ✅ Couvre les 3 cas (USER_GROUP, CLUB_GROUP, CLASSE_GROUP) en un seul index

**Plan d'exécution optimisé:**
```
Index Scan using idx_story_groups_feed_optimized
  Filter: ((group_type = 'USER_GROUP') OR (group_type = 'CLUB_GROUP') OR ...)
```

### 2. Index spécifique pour CLASSE_GROUP
**Nom:** `IDX_STORY_GROUPS_CLASSE_PAGINATION`
```sql
CREATE INDEX idx_story_groups_classe_pagination
ON story_groups(target_classe_id, expires_at DESC, updated_at DESC, id DESC)
WHERE is_active = TRUE AND group_type = 'CLASSE_GROUP';
```

**Avantages:**
- ✅ Recherche directe par `target_classe_id`
- ✅ Utilise les index partialisés PostgreSQL (déjà filtrés par `group_type`)
- ✅ Élimine le filtre OR pour le cas CLASSE_GROUP

**Plan d'exécution optimisé:**
```
Index Scan using idx_story_groups_classe_pagination
  Index Cond: ((target_classe_id = $1) AND (expires_at >= NOW()))
```

### 3. Index full-covering pour vues
**Nom:** `IDX_STORY_VIEWS_USER_LOOKUP`
```sql
CREATE INDEX idx_story_views_user_lookup
ON story_views(story_id, user_id, viewed_at DESC);
```

**Avantages:**
- ✅ Full covering index - pas besoin d'accéder à la table
- ✅ PostgreSQL récupère directement `story_id` dans l'index
- ✅ Réduit les I/O disque

### 4. Index inverse pour analytics
**Nom:** `IDX_STORY_VIEWS_BY_USER_STORY`
```sql
CREATE INDEX idx_story_views_by_user_story
ON story_views(user_id, story_id);
```

**Avantages:**
- ✅ Utile pour requêtes futures (toutes les vues d'un utilisateur)
- ✅ Peut aider avec les agrégations

---

## 📈 Gains de performance attendus

| Métrique | Avant | Après | Gain |
|----------|-------|-------|------|
| I/O pour feed (10 groupes) | ~5-8 bloc DB | ~2-3 bloc DB | **50-60%** ↓ |
| Temps requête feed | ~50-100ms | ~10-30ms | **50-70%** ↓ |
| Temps requête vues | ~20-40ms | ~5-15ms | **50-75%** ↓ |
| CPU du planner | Haut (filtrage post-index) | Bas (filtrage in-index) | **30-40%** ↓ |

---

## 🚀 Déploiement

1. **Appliquer la migration Alembic:**
   ```bash
   alembic upgrade head
   ```

2. **Vérifier les index créés:**
   ```sql
   SELECT indexname, indexdef 
   FROM pg_indexes 
   WHERE tablename IN ('story_groups', 'story_views');
   ```

3. **Analyser les plans d'exécution (optionnel):**
   ```sql
   EXPLAIN ANALYZE
   SELECT * FROM story_groups
   WHERE expires_at >= NOW()
     AND (group_type = 'USER_GROUP' OR group_type = 'CLUB_GROUP')
   ORDER BY updated_at DESC, id DESC
   LIMIT 11;
   ```

---

## 📝 Notes techniques

### Pourquoi pas d'index sur `is_active`?
- `is_active` est un booléen avec très peu de valeurs (TRUE/FALSE)
- Le ratio sélectivité est mauvais pour l'optimiseur
- Les indexes partialisés `WHERE is_active = TRUE` sont meilleurs

### Pourquoi composite plutôt que multi-colonnes?
- Les index composites permettent à PostgreSQL de filtrer ET de trier en un seul pass
- Élimine les sorts externes qui sont très coûteux

### Taille estimée des nouveaux index
- `idx_story_groups_feed_optimized`: ~50-100MB (si 1M de groups)
- `idx_story_groups_classe_pagination`: ~10-20MB (filtered index)
- `idx_story_views_user_lookup`: ~100-200MB (si 10M de views)
- **Total:** ~200-300MB d'espace supplémentaire

---

## ✨ Recommandations futures

1. **Monitoring**: Utiliser `pg_stat_user_indexes` pour vérifier l'utilisation
2. **VACUUM ANALYZE**: Exécuter après la migration pour mettre à jour les stats
3. **Partitioning**: Si >100M de rows en story_views, considérer une partitioning par date
4. **Caching**: Le Redis cache pour les vues est une bonne idée, garder l'implémentation

