# Politique de synchronisation et de validité — prototype

> **Statut : hypothèses d'ingénierie, non exigences normatives.**
> Les valeurs ci-dessous servent à tester les comportements attendus du simulateur.
> Elles ne constituent pas une preuve de conformité ni une recommandation prête
> à déployer dans un bâtiment occupé.

## Références

- NIST SP 800-53 rév. 5, AC-2(3) : les délais de désactivation sont
  définis par l'organisation; pas de cadence universelle imposée.
  https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final
- NIST SP 800-53 rév. 5, PE-3 : vérifier les autorisations d'accès physique.
- SIA OSDP / IEC 60839-11-5 : standard pertinent pour la liaison ultérieure
  contrôleur de porte / périphériques; **ne** définit **pas** ces durées.
  https://www.securityindustry.org/2024/10/31/security-industry-association-releases-version-2-2-2-of-sia-open-supervised-device-protocol-standard/

## Paramètres initiaux

Fichier machine-lisible : `configuration/politique-synchronisation.json`.

| Paramètre | Valeur | Interprétation |
|---|---:|---|
| intervalle_synchronisation_s | 300 s | Nouveau cycle périodique |
| alerte_retard_s | 900 s | Émettre une alerte après 15 minutes sans synchronisation réussie |
| validite_cache_standard_s | 3600 s | Au-delà de 60 minutes, refuser de **nouvelles entrées** |
| validite_cache_sensible_s | 0 s | En cas de perte de liaison, ne pas accorder d'entrée hors ligne |
| connexion_timeout_s | 5 s | Limite par tentative de connexion |
| nouvel_essai_initial_s | 30 s | Premier réessai |
| nouvel_essai_max_s | 300 s | Plafond du retour exponentiel |
| expiration_autorisation | selon les données | Ne pas dépasser `date_fin` même en mode déconnecté |

## Machines à états

1. **Jamais synchronisé** : refuser; les fixtures SQLite locales du prototype
   ne doivent pas être considérées comme des données validées par le central.
2. **Synchronisé et sain** : décisions selon les autorisations actives,
   l'échéance individuelle et la version de la politique.
3. **Connexion perdue** : continuer pour les portes standard uniquement
   tant que le dernier instant de synchronisation *authentifiée et validée*
   date de moins de 3600 s.
4. **Cache périmé** : refuser les nouvelles entrées, alerter, conserver
   les données pour audit et nouvelle synchronisation.
5. **Porte sensible** : refuser toute entrée hors ligne (valeur zéro par défaut).
6. **Retour de connexion** : télécharger un instantané complet avec numéro
   de version croissant, vérifier sa signature/provenance, appliquer en une
   transaction SQLite, puis actualiser l'horodatage uniquement après
   validation et validation de transaction.

Une réponse HTTP réussie, un heartbeat ou un fichier reçu ne suffit pas à
rafraîchir la durée de validité : seule une *synchronisation complète et
authentifiée* y autorise. Rejeter les versions antérieures (rollback).
Le calcul de fraîcheur doit gérer les redémarrages et les changements d'horloge.

## Sécurité physique et limites

- Les réglages fail-secure des portes **n'interdisent pas la sortie libre**;
  les mécanismes de sortie, alimentation et déverrouillage incendie
  relèvent du code du bâtiment applicable et d'une analyse propre aux lieux.
- Les portes sensibles ne sont pas toutes nécessairement fail-secure :
  déterminer les exigences de vie-sécurité avec les responsables compétents.
- Le cache SQLite actuel contient des fixtures statiques et ne reçoit
  **aucune synchronisation**. Il ne doit pas être présenté comme frais.
- La politique de renouvellement des droits ne remplace pas un mécanisme
  d'urgence pour révoquer un badge perdu ni la procédure manuelle sur site.
- La liaison PostgreSQL/PostgREST reste sur boucle locale en attendant
  un tunnel authentifié/chiffré et une authentification du service local.
- Pour des données réelles : séparer secrets et code, limiter les droits,
  consigner les événements, vérifier l'horloge et tester les pannes.

## Première liaison réalisée dans le dépôt (non encore validée sur machines)

Le Raspberry Pi peut demander ponctuellement un instantané fictif par SSH :

```bash
bash scripts/synchroniser-serveur-local.sh UTILISATEUR@ORDINATEUR
```

La commande SSH s'exécute sur l'hôte Raspberry Pi et utilise sa configuration
de clés et `known_hosts`. Elle appelle `curl` sur l'interface
`127.0.0.1:3000` **de l'ordinateur distant**. La sortie JSON passe sur
l'entrée standard d'un conteneur sans réseau qui importe la base en transaction.
Aucune clé SSH n'est montée dans le conteneur. L'heure centrale est contrôlée,
mais cette première version dépend de la synchronisation des horloges système.

Le poste distant utilise encore un compte SSH ordinaire et l'API exporte des
données fictives sous le rôle anonyme **sur boucle locale seulement** : il
s'agit d'un laboratoire, pas d'une architecture de production. Pour la suite :
compte SSH restreint à une commande, autorisation fine par bâtiment, signature
d'instantanés, numéros de version monotones transactionnels et journal d'audit.

Le cache synchronisé est enregistré dans `autorisations-synchronisees.sqlite3`, distinct du fichier de fixtures `autorisations.sqlite3` ; les tests initiaux ne peuvent donc pas réintroduire des droits révoqués dans le cache synchronisé.\n\nLa commande `verifier-sync` du prototype C++ refuse au-delà de 3600 secondes,
sans instantané ou si l'horloge recule. La valeur est pour l'instant codée dans
le prototype en C++ et **doit encore être pilotée à partir du fichier JSON**
avant de qualifier le paramétrage de centralisé.

Le prototype n'implémente **pas encore** la cadence automatique de 300 secondes,
les alertes ni les profils distincts pour portes sensibles. Les dates
individuelles `date_debut` et `date_fin` sont maintenant vérifiées en mode
synchronisé. Les autorisations fixes du mode de test `verifier` demeurent
séparées des autorisations validées via `verifier-sync`.
