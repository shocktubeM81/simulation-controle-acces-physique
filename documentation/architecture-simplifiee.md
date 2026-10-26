# Version simplifiée du banc

Le Raspberry Pi est le contrôleur. Il acquiert les UID du MFRC522, consulte le
cache synchronisé et prend la décision d'autorisation. Il reçoit aussi les appuis
BOOT, tient les journaux et affiche les événements dans sa console.

L'EliteBook G6 conserve le rôle de serveur central (PostgreSQL et export des
autorisations). Il sert également à compiler le programme de l'ESP32.

L'ESP32-C6 est une interface déportée en USB : bouton BOOT et écran. Il ne conserve
pas une copie des autorisations et ne décide pas de l'accès RFID. La confirmation
d'un appui signifie qu'il a été enregistré par le Pi, sans ouverture physique.

```text
EliteBook G6 — serveur central
             |
             | synchronisation des autorisations
             v
Raspberry Pi — contrôleur et cache local
       |                       |
       | SPI                   | USB bidirectionnel
       v                       v
    MFRC522             ESP32-C6 — écran et BOOT
```

Le serveur local n'est pas une machine distincte dans cette version. Ses fonctions
de cache et de synchronisation sont regroupées sur le contrôleur Pi. Les noms
historiques `serveur-local/` et `compose.local.yaml` sont conservés dans le code.

Un EliteBook G1 pourra ultérieurement héberger un serveur local distinct. Il
faudra alors définir les échanges avec le Pi et les règles en cas de perte de
liaison; cette séparation n'est pas encore implémentée.

Le retour RFID sur USB est un affichage : vert pour `AUTORISE`, rouge pour
`REFUSE`, orange pour une erreur technique, pendant trois secondes. Les erreurs
du journal gardent la priorité orange. Aucun UID ne quitte le Pi pour cet
affichage et aucune commande de serrure n'est envoyée.
