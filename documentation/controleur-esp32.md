# Contrôleur de secteur ESP32 — conception initiale

**Statut : spécification de travail, interface non encore implémentée.**

## Objectif

Simuler un contrôleur de secteur ESP32 desservant **une ou deux portes**, avec un Raspberry Pi comme serveur local et PostgreSQL/PostgREST sur l'ordinateur central. Les identifiants et les décisions sont fictifs. Aucune serrure réelle n'est raccordée.

## Répartition des fonctions

| Équipement | Responsabilité |
|---|---|
| Ordinateur central | Gestion des personnes, identifiants et autorisations; export SSH restreint |
| Raspberry Pi | Cache SQLite synchronisé, contrôle de fraîcheur, calcul de la décision, interface IP vers le contrôleur |
| ESP32 | Acquisition des entrées, transmission de la demande, signalisation et commande d'un actionneur de démonstration |

Le Raspberry Pi reste la **source de décision** : aucune copie de la base SQLite ni aucune règle d'autorisation ne sont embarquées dans l'ESP32.

## Transport et alimentation

- **Prototype** : Wi-Fi intégré à la carte ESP32, alimentation USB indépendante.
- **Variante étudiée** : Ethernet avec PoE, lorsque le matériel sera disponible.
- La décision et les messages applicatifs doivent rester indépendants du transport IP choisi.
- Les entrées/sorties de porte sont locales au contrôleur de secteur; jusqu'à deux instances de porte sont prévues.

## Contrat applicatif envisagé (v1)

Une première interface HTTP avec JSON est envisagée pour la simulation. **Cette section spécifie un format à tester, elle ne décrit pas un service existant.**

Demande de décision :

```http
POST /api/v1/acces/verifier
Content-Type: application/json
```

```json
{
  "version": 1,
  "controleur": "SECTEUR-01",
  "porte": "Laboratoire",
  "identifiant": "FICTIF-0001"
}
```

Réponse en cas de traitement valide :

```json
{
  "version": 1,
  "decision": "AUTORISE"
}
```

L'alternative de décision est `REFUSE`. Une erreur de transport, une réponse illisible, un dépassement de délai ou une absence de cache valide doivent produire un **refus de nouvelle commande d'ouverture**, sans réutilisation automatique d'une autorisation antérieure.

## Sécurité et sûreté

- Ne pas ouvrir le service de décision sur Internet.
- Identifier et authentifier chaque contrôleur; ne jamais fonder l'autorisation sur sa seule adresse IP ou sur le SSID Wi-Fi.
- Protéger les communications et leurs identifiants contre l'écoute, la modification et la réutilisation. L'interface HTTP ci-dessus ne doit pas commander un verrou réel sans mécanisme de sécurité adapté.
- Le contrôleur est installé du côté protégé; aucun lecteur accessible au public ne doit pouvoir commander directement la sortie d'ouverture.
- Les scénarios d'évacuation, de panne d'alimentation et de sécurité incendie exigent une conception physique indépendante du prototype logiciel.

## Ordre de réalisation

1. **API locale du Raspberry Pi** : adapter le moteur C++ pour retourner une décision exploitable sans analyser sa sortie standard; ajouter un point d'entrée réseau et des tests locaux.
2. **Essai sans microcontrôleur** : simuler une demande et un refus depuis un ordinateur, puis vérifier la non-régression de la synchronisation et des minuteurs.
3. **ESP32 en Wi-Fi** : implémenter le client réseau, les délais et la signalisation par DEL; une porte fictive, puis deux.
4. **Comparaison** : mesurer latence, disponibilité, rétablissement et alimentation; envisager Ethernet/PoE comme variante.

## Conventions de code

- C++20 et CMake côté serveur local; modules aux responsabilités distinctes (base SQLite, politique de décision, transport réseau).
- Le programme embarqué séparera connexion réseau, échanges applicatifs et gestion des portes.
- Commenter les **invariants et choix de conception**, non les opérations évidentes.
- Conserver les cinq scripts Shell actuels : les tests du futur service seront intégrés à `scripts/verifier.sh`.

## Point restant à préciser

Le modèle exact de la carte ESP32 et les GPIO disponibles détermineront l'environnement de compilation et les périphériques de démonstration. Ne pas choisir les broches avant d'avoir identifié la carte.
