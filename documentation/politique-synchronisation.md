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
- Le cache SQLite **statique de diagnostic** contient des fixtures locales; le fichier `autorisations-synchronisees.sqlite3` est distinct et reçoit les instantanés SSH.
- La politique de renouvellement des droits ne remplace pas un mécanisme
  d'urgence pour révoquer un badge perdu ni la procédure manuelle sur site.
- L'API PostgreSQL/PostgREST reste sur boucle locale; le Raspberry Pi obtient l'export via un compte SSH à commande forcée.
- Pour des données réelles : séparer secrets et code, limiter les droits,
  consigner les événements, vérifier l'horloge et tester les pannes.

## Synchronisation manuelle (diagnostic historique)

Le Raspberry Pi peut demander ponctuellement un instantané fictif par SSH :

```bash
sudo systemctl start controle-acces-synchronisation.service
```

La commande SSH s'exécute sur l'hôte Raspberry Pi et utilise sa configuration
de clés et `known_hosts`. Elle appelle `curl` sur l'interface
`127.0.0.1:3000` **de l'ordinateur distant**. La sortie JSON passe sur
l'entrée standard d'un conteneur sans réseau qui importe la base en transaction.
Aucune clé SSH n'est montée dans le conteneur. L'heure centrale est contrôlée,
mais cette première version dépend de la synchronisation des horloges système.

Le compte distant `controle-export` exécute exclusivement la commande d'export SSH. L'API exporte encore des données fictives sous un rôle anonyme accessible seulement sur boucle locale. Pour la suite : autorisations fines par bâtiment, intégrité des instantanés, versions monotones transactionnelles et audit.

Le cache synchronisé est enregistré dans `autorisations-synchronisees.sqlite3`, distinct du fichier de fixtures `autorisations.sqlite3`; les tests initiaux ne peuvent donc pas réintroduire des droits révoqués dans le cache synchronisé.

La commande `verifier-sync` du prototype C++ refuse au-delà de 3600 secondes,
sans instantané ou si l'horloge recule. La valeur est pour l'instant codée dans
le prototype en C++ et **doit encore être pilotée à partir du fichier JSON**
avant de qualifier le paramétrage de centralisé.

Le timer de synchronisation fonctionne selon un intervalle de cinq minutes après le cycle précédent. La surveillance indépendante peut classifier le cache en `CACHE_NORMAL`, `CACHE_RETARD` (≥ 900 secondes) ou `CACHE_EXPIRE` (≥ 3600 secondes) et journalise le résultat via `systemd`. **Aucune notification externe n'est encore envoyée**. Les profils distincts pour les portes sensibles ne sont pas implémentés. Les dates
individuelles `date_debut` et `date_fin` sont maintenant vérifiées en mode
synchronisé. Les autorisations fixes du mode de test `verifier` demeurent
séparées des autorisations validées via `verifier-sync`.

## Automatisation avec systemd et clé restreinte (octobre 2026)

Ce laboratoire fournit :
- `scripts/installer-pi.sh` : une **nouvelle** clé SSH sans
  phrase secrète, pour le service seulement; les permissions locales doivent
  rester strictes et la clé ne doit jamais être publiée.
- `scripts/installer-central.sh export` : sur l'ordinateur,
  compte `controle-export` et `authorized_keys` avec `restrict,command=...`.
  OpenSSH interdit alors shell interactif, forwarding et commandes arbitraires
  **pour cette clé**. Le compte ne doit pas recevoir d'autres clés.
- `scripts/installer-pi.sh configurer` : installe les unités sans les
  activer; une synchronisation valide est obligatoire avant activation.
- `systemd/controle-acces-synchronisation.timer` : lancement après démarrage
  puis cinq minutes après la fin du cycle précédent. Il ne garantit pas une
  heure civile exacte ni une révocation en cinq minutes en cas de panne.
- `systemd/controle-acces-synchronisation.service` : journal via
  `journalctl -u controle-acces-synchronisation.service`.

Le service est lancé par le gestionnaire systemd avec privilèges root pour
accéder à Docker, alors que la commande SSH est exécutée comme utilisateur
non privilégié. **Limite du prototype :** le dépôt Compose est modifiable
par son propriétaire; un service root lançant Docker à partir de ce dépôt
n'est pas adapté à une installation de production. Pour la production,
installer un manifeste Compose vérifié, immuable et administré par root, ou
utiliser Docker rootless avec une politique d'autorisations adaptée.

La commande SSH forcée ne confère pas à elle seule une autorisation au niveau
des données : l'API d'export reste anonyme sur boucle locale et retourne
toutes les autorisations fictives. Une politique par bâtiment est requise
pour les données réelles.

**L'ancienne clé `id_ed25519_controle_acces` a été révoquée du compte personnel lors du nettoyage d'octobre 2026.** La clé dédiée `id_ed25519_controle_sync` reste nécessaire à `controle-export`.

## Surveillance installée automatiquement

Sur le Raspberry Pi, après mise à jour du dépôt, la commande habituelle :

```bash
bash scripts/installer-pi.sh
```

reconstruit l'image ARM64, effectue les tests simulés des seuils et
met à jour les deux services périodiques. Si le minuteur de synchronisation
existe et est actif, le nouveau minuteur est automatiquement activé.

Le contrôle de fraîcheur s'exécute chaque minute et lit le volume SQLite
en **lecture seule**. Il ne modifie ni la base, ni les autorisations, ni
l'heure système. Il n'interrompt pas les tentatives de synchronisation.
Pour vérifier les seuils sans panne réelle :

```bash
bash scripts/verifier.sh seuils
```

Afficher les états récents :

```bash
sudo journalctl -u controle-acces-surveillance.service -n 30 --no-pager
systemctl list-timers --all controle-acces-surveillance.timer
```

Pour une simulation de panne réseau **non intrusive**, désactiver
provisoirement et uniquement le minuteur de synchronisation :

```bash
sudo systemctl stop controle-acces-synchronisation.timer
```

Cela laisse le dernier cache intact; après 15 minutes, le moniteur
journalise `CACHE_RETARD`; après 60 minutes, `CACHE_EXPIRE`.
Réactiver ensuite le minuteur :

```bash
sudo systemctl start controle-acces-synchronisation.timer
sudo systemctl start controle-acces-synchronisation.service
```

**Attention :** arrêter le minuteur n'empêche pas un service ponctuel déjà
en cours. L'arrêt est strictement une expérience de laboratoire. Ne
pas désactiver le réseau complet du Raspberry Pi, qui pourrait aussi
interrompre sa connexion SSH d'administration.

Le moniteur produit un état dans `journald` mais ne configure
pas encore de notifications par courriel, téléphone ou supervision distante.
Le refus d'accès par le moteur C++ reste un contrôle **indépendant** de
la supervision : le minuteur ne doit jamais être une condition nécessaire
pour que le système refuse un cache périmé.
