# Principes de sécurité de l'architecture

Le projet est un banc d'essai pédagogique, **pas** un système de verrouillage prêt à l'emploi.

## Sécurité fondée sur une conception vérifiable

La sécurité ne repose pas sur le secret du code, des ports ou du fonctionnement. Le dépôt peut être public; seuls les secrets d'authentification doivent rester confidentiels. Les mécanismes de défense doivent être documentés, auditables et fondés sur des protocoles éprouvés.

## Défenses appliquées dès le déploiement

- PostgreSQL n'expose **aucun port** sur l'hôte; il est raccordé seulement au réseau Docker privé `interne`.
- PostgREST est raccordé au réseau privé pour joindre PostgreSQL et au réseau `acces_local` pour publier son API exclusivement sur `127.0.0.1:3000`. Cette double connexion est volontaire; elle ne donne pas à PostgreSQL de port publié.
- L'API est publiée **uniquement sur 127.0.0.1:3000**; aucun appareil distant n'y accède à ce stade.
- L'API expose les fonctions `api.verifier_acces` et `api.exporter_autorisations` (instantané fictif), mais pas les tables.
- Les comptes de base de données sont séparés; le compte de connexion PostgREST n'est pas superutilisateur.
- Les secrets sont générés localement, ignorés par Git et jamais consignés dans les journaux.
- Les conteneurs Raspberry Pi sont non privilégiés, et l'import SQLite et la surveillance ne disposent d'aucun accès réseau.
- Les données PostgreSQL persistent dans un volume explicite; arrêter les conteneurs ne supprime pas la base.

## Limites explicites

L'endpoint HTTP expérimental ne réalise **pas d'authentification du client**. Son exposition au réseau est donc interdite. Le serveur C++ sur TCP 5050 n'est qu'un outil de diagnostic **sans authentification ni chiffrement**; il ne doit jamais commander une serrure.

Le Raspberry Pi utilise désormais une clé SSH dédiée au compte `controle-export`, dont la commande est forcée côté ordinateur central. Ce transport authentifié et chiffré ne constitue toutefois pas une politique d'autorisation par équipement : l'export retourne toutes les données fictives. Restent à développer les droits granulaires, l'audit, la révocation avancée et la gestion des incidents.

## Sécurité physique et sûreté

La logique en cas de panne (accès refusé/autorisé, déverrouillage d'urgence, évacuation) doit être définie suivant les exigences applicables. L'intégrité de la base ou la disponibilité d'un conteneur ne remplace pas une conception physique conforme.

## Exploitation

- Épingler les versions d'images et planifier les mises à jour de sécurité.
- Ne jamais monter `/var/run/docker.sock` dans les services du projet.
- Ne pas utiliser `privileged: true`.
- Éviter de publier les ports PostgreSQL ou Docker.
- Tester les stratégies de sauvegarde/restauration avant toute simulation de panne.
- Analyser les changements au code et aux dépendances avant déploiement.

Références : [Docker Compose — secrets](https://docs.docker.com/compose/how-tos/use-secrets/), [PostgREST — configuration](https://docs.postgrest.org/en/stable/references/configuration.html).

## Limites de l'automatisation

La synchronisation et la surveillance sont déclenchées par `systemd` sur le Raspberry Pi. Les services lancent Docker avec les droits root à partir d'un dépôt modifiable par l'utilisateur : cette installation est destinée **uniquement au laboratoire**. L'automatisation ne rend pas le code prêt pour la production. Les alertes de cache expiré sont journalisées localement, sans notification externe.
