# RodiumAI — Module 03, Assignment 3

Script Python interactif qui enchaîne trois actions sur l'API RodiumAI : conversation, génération d'image et génération vidéo. Après chaque action, vous pouvez revenir à l'étape précédente, refaire l'étape actuelle ou avancer.

## Prérequis

- Python 3.8 ou plus récent
- Une clé API RodiumAI

## Installation

```bash
git clone https://github.com/justin2119/rodiumai-bootcamp-module03-assignment3.git
cd rodiumai-bootcamp-module03-assignment3
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell : .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Le projet utilise uniquement la bibliothèque standard Python et `requests` (aucun SDK RodiumAI).

## Configuration de la clé

Linux/macOS :

```bash
export RODIUM_API_KEY="votre_cle_api"
```

Windows PowerShell :

```powershell
$env:RODIUM_API_KEY="votre_cle_api"
```

Le fichier `.env.example` est fourni comme aide-mémoire. Pour éviter toute dépendance supplémentaire, le script ne lit pas les fichiers `.env` automatiquement. Si la variable d'environnement n'est pas définie, il vous demandera la clé au lancement.

## Lancement

```bash
python main.py
```

Le script utilise `https://api.rodiumai.io/v1/` et envoie l'authentification avec un jeton Bearer. Les résultats sont enregistrés dans `outputs/` : `image_generee.png` et `video_generee.mp4`.

## Étapes

1. **Chat** — saisissez une question ; la réponse et `cost_rodi` sont affichés lorsque cette donnée est présente dans la réponse de l'API.
2. **Image** — saisissez une description ; le contenu `b64_json` est décodé en PNG, avec prise en charge d'une URL en solution de repli.
3. **Vidéo** — saisissez une description ; le script enregistre une vidéo retournée en URL ou base64. Pour une réponse asynchrone avec identifiant, il vérifie la ressource vidéo jusqu'à 10 minutes.

Les appels d'images et de vidéos utilisent les champs de requête `prompt`. La forme exacte des réponses et la prise en charge du polling dépendent de la configuration de l'API RodiumAI ; les erreurs HTTP et les réponses non prises en charge sont affichées pour faciliter le diagnostic.
