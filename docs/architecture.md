# Décisions de conception

Ce document explique les choix structurants du projet, dans l'esprit d'une page Confluence
d'équipe data : le contexte, la décision, et ce qu'elle implique.

## 1. Deux bases Snowflake : RAW et ANALYTICS
**Décision.** Les données brutes vivent dans `RAW` (un schéma par source) et ne sont écrites que par
le rôle `LOADER`. dbt lit `RAW` et écrit `ANALYTICS` avec le rôle `TRANSFORMER`. Metabase lit `ANALYTICS` avec le rôle `REPORTER`.
**Pourquoi.** On peut toujours rejouer les transformations depuis la donnée d'origine (principe ELT),
et l'outil de BI ne voit jamais la donnée brute non nettoyée. Les droits sont simples à auditer.

## 2. Trois couches dbt
- **staging** : un modèle par table source. Uniquement du renommage, du typage, du dédoublonnage et
  le filtre des suppressions logiques. Aucune jointure. Tout ce qui est propre à un format partenaire
  (centimes texte, dates texte, formats longs, prélèvement à M+1) est neutralisé ici.
- **intermediate** : unification des trois partenaires et règles métier réutilisables (frais
  théoriques, apports nets, droits des offres, historique des profils).
- **marts** : tables exposées, rangées par domaine métier (`finance`, `clients`, `service_client`).

**Pourquoi.** Quand un partenaire change de format, une seule vue de staging est à modifier. Les
règles métier ne sont écrites qu'une fois.

## 3. Une date d'arrêté plutôt que `current_date`
`int_date_arrete` = dernière valorisation reçue. Les calculs « à date » (encours actuel, ancienneté,
rétention, échéance des offres) s'y réfèrent.
**Pourquoi.** Un calcul doit donner le même résultat s'il est relancé demain sur les mêmes données.
C'est indispensable pour justifier un chiffre a posteriori dans un environnement régulé.

## 4. L'encours est un stock
Dans MetricFlow, les mesures d'encours portent une `non_additive_dimension` (dernier jour de la
période). Interroger l'encours « par mois » renvoie l'encours de fin de mois, jamais une somme de
jours. Même chose pour le nombre de clients avec encours.

## 5. Frais théoriques recalculés selon la règle contractuelle
Frais du jour = encours UC de la veille × taux / 365, sur tous les jours calendaires ; week-ends
complétés par la dernière valorisation ; part en fonds euros exclue. La comparaison avec les frais
prélevés porte sur 100 % des contrats chaque mois, avec une tolérance paramétrée
(`rapprochement_frais_tolerance_pct`) et un seuil d'un euro, pour ne pas noyer la finance dans des
écarts d'arrondi.

## 6. Offres promotionnelles : règle versionnée, testée, rapprochée
Les paliers sont dans un seed (`offres_paliers.csv`), mis à jour à chaque nouvelle offre. Le calcul
(`int_offres_droits`) suit les conditions générales :
- palier au versement initial net ;
- premier mois entier suivant la souscription ;
- plafond global ;
- extinction du droit à la première rupture de condition.

Deux unit tests figent la règle. Le rapprochement avec les paiements saisis à la main
(`finance_offres_rapprochement`) transforme un contrôle manuel en liste d'actions.

## 7. Portabilité Snowflake / DuckDB
Le même code tourne sur Snowflake (cible) et sur DuckDB (CI, développement hors ligne). On utilise
pour cela :
- les macros croisées de dbt (`dbt.dateadd`, `dbt.datediff`, `dbt.date_spine`) ;
- `adapter.dispatch` quand la syntaxe diffère (`last_value(x) ignore nulls`) ;
- pas de fonctions propres à un seul moteur dans les modèles.

**Pourquoi.** Chaque PR est vérifiée gratuitement en CI, et un recruteur ou un nouvel arrivant peut
exécuter le projet en cinq minutes sans compte.

## 8. Sécurité
- Authentification par paire de clés RSA pour les utilisateurs de service (pas de mot de passe).
- Aucun secret dans le repo : profil dbt et scripts lisent les variables d'environnement, et
  `keys/` et `.env` sont ignorés par git.
- Plafond de crédits Snowflake (resource monitor) et entrepôts XS en arrêt automatique.
