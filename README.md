# Exercice 2 — RodiumAI, Module 03 Assignment 3

Script Python interactif qui enchaîne une requête Chat, une génération d'image et une génération vidéo avec l'API RodiumAI.
Il affiche les erreurs API détaillées et enregistre les médias créés dans `outputs/`.

## Prérequis et installation

Python 3.8 ou plus récent est requis. Clonez le dépôt, créez un environnement virtuel et installez la dépendance :

```bash
git clone https://github.com/justin2119/rodiumai-bootcamp-module03-assignment3.git
cd rodiumai-bootcamp-module03-assignment3
python -m venv .venv
# macOS/Linux : source .venv/bin/activate
# Windows PowerShell : .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Configuration `.env`

Copiez `.env.example` sous le nom `.env` et remplacez la valeur de démonstration par votre clé RodiumAI. Le script charge `.env` sans bibliothèque additionnelle. Ne partagez jamais votre clé.

```bash
# macOS/Linux
cp .env.example .env
# Windows PowerShell
Copy-Item .env.example .env
```

Le fichier `.env` est ignoré par Git. Le fichier `.env.example` contient uniquement la ligne `RODIUMAI_API_KEY=rd_sk_votre_cle`.

Optionnel : si votre compte/API exige le choix explicite d'un modèle d'image ou de vidéo, définissez les identifiants de modèles image-capable/video-capable indiqués dans le catalogue RodiumAI. Sans ces variables, le script envoie uniquement `prompt` (et `response_format: b64_json` pour l'image), afin de laisser le routage par défaut de l'API agir.

```bash
RODIUMAI_IMAGE_MODEL="identifiant-modele-image" RODIUMAI_VIDEO_MODEL="identifiant-modele-video" python main.py
```

## Exécution

```bash
python main.py
```

À la fin de chaque étape : 1) revenir à l'étape précédente, 2) refaire l'étape actuelle, ou 3) passer à la suivante. Les résultats sont `outputs/output_image.png` et `outputs/output_video.mp4`.

## Vérification et captures curl demandées

Ces commandes servent aux deux captures d'écran requises (wallet et chat). Elles utilisent la clé du fichier `.env` dans un terminal Bash :

```bash
set -a; . ./.env; set +a
curl -i https://api.rodiumai.io/v1/wallet \
  -H "Authorization: Bearer $RODIUMAI_API_KEY"
```

Capturez la commande et sa réponse wallet. Pour le chat :

```bash
curl -i https://api.rodiumai.io/v1/chat/completions \
  -H "Authorization: Bearer $RODIUMAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Bonjour, réponds en une phrase."}]}'
```

Ajoutez les deux captures curl, le lien GitHub (https://github.com/justin2119/rodiumai-bootcamp-module03-assignment3) à votre PDF, ainsi que trois captures d'exécution (Chat, Image montrant le PNG créé et Vidéo montrant le MP4 créé).

## Dépannage génération image/vidéo

`main.py` affiche le payload envoyé, la méthode/URL et le statut HTTP. En cas d'erreur, il imprime le corps retourné par l'API, et si une réponse réussit mais ne contient aucun champ image/vidéo attendu, il affiche le JSON brut. Cela aide à distinguer clé/droits (401/403), solde (402), modèle ou paramètres (400/422), limite (429) et erreur fournisseur (5xx). Les structures usuelles sont prises en charge : champs imbriqués ou `data[]`, `b64_json`, `url`/`image_url`/`video_url`, identifiants de tâche et polling (`poll_url`/`status_url` ou `/v1/videos/{id}`). Le polling dure au plus 10 minutes.

Référence API : https://www.rodiumai.io/docs/api/overview (image et vidéo : `POST /v1/images/generations`, `POST /v1/videos/generations`; wallet : `GET /v1/wallet`). Les modèles et détails de réponse peuvent varier selon le catalogue et le compte. Si l'API renvoie une erreur de validation, consultez la réponse brute, puis indiquez explicitement les variables `RODIUMAI_IMAGE_MODEL` ou `RODIUMAI_VIDEO_MODEL` appropriées.
