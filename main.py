#!/usr/bin/env python3
"""Parcours interactif Chat → Image → Vidéo pour l'API RodiumAI.
Dépendance externe unique : requests. La clé API est lue depuis RODIUM_API_KEY.
"""

import base64
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import requests

BASE_URL = "https://api.rodiumai.io/v1/"
TIMEOUT = 60
OUTPUT_DIR = Path("outputs")


def api_key():
    key = os.getenv("RODIUM_API_KEY", "").strip()
    if not key:
        key = input("Clé API RodiumAI (ou définissez RODIUM_API_KEY) : ").strip()
    if not key:
        raise ValueError("La clé API ne peut pas être vide.")
    return key


def post_json(endpoint, payload):
    response = requests.post(
        urljoin(BASE_URL, endpoint),
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        json=payload,
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def download(url, destination):
    response = requests.get(url, headers={"Authorization": f"Bearer {API_KEY}"}, stream=True, timeout=120)
    response.raise_for_status()
    with destination.open("wb") as output:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                output.write(chunk)


def find_value(obj, key):
    """Recherche récursive d'une valeur dans les réponses imbriquées."""
    if isinstance(obj, dict):
        if key in obj and obj[key] is not None:
            return obj[key]
        for value in obj.values():
            found = find_value(value, key)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = find_value(value, key)
            if found is not None:
                return found
    return None


def chat_step():
    prompt = input("Votre question : ").strip()
    if not prompt:
        print("La question est vide ; aucune requête envoyée.")
        return
    result = post_json("chat/completions", {"messages": [{"role": "user", "content": prompt}]})
    answer = find_value(result, "content")
    if isinstance(answer, list):
        answer = "".join(part.get("text", "") for part in answer if isinstance(part, dict))
    print("\nRéponse :\n" + (str(answer) if answer is not None else json.dumps(result, ensure_ascii=False, indent=2)))
    cost = find_value(result, "cost_rodi")
    print(f"\nCoût RodiumAI (cost_rodi) : {cost if cost is not None else 'non fourni dans la réponse'}")


def image_step():
    prompt = input("Description de l'image à générer : ").strip()
    if not prompt:
        print("Description vide ; aucune requête envoyée.")
        return
    result = post_json("images/generations", {"prompt": prompt})
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    image_b64 = find_value(result, "b64_json")
    if image_b64:
        # Certaines API ajoutent un préfixe data:image/...;base64,
        image_b64 = image_b64.split(",", 1)[-1]
        path = OUTPUT_DIR / "image_generee.png"
        path.write_bytes(base64.b64decode(image_b64))
    else:
        image_url = find_value(result, "url")
        if not image_url:
            raise ValueError("Réponse image sans b64_json ni URL : " + json.dumps(result, ensure_ascii=False))
        path = OUTPUT_DIR / "image_generee.png"
        download(image_url, path)
    print(f"Image enregistrée : {path}")


def video_step():
    prompt = input("Description de la courte vidéo à générer : ").strip()
    if not prompt:
        print("Description vide ; aucune requête envoyée.")
        return
    result = post_json("videos/generations", {"prompt": prompt})
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / "video_generee.mp4"
    # Réponses possibles : URL immédiate, données base64 ou identifiant d'une tâche asynchrone.
    video_url = find_value(result, "url") or find_value(result, "video_url")
    video_b64 = find_value(result, "b64_json") or find_value(result, "video_base64")
    task_id = find_value(result, "task_id") or find_value(result, "id")
    if video_b64:
        path.write_bytes(base64.b64decode(video_b64.split(",", 1)[-1]))
    elif video_url:
        download(video_url, path)
    elif task_id:
        # Interroge la ressource de tâche si la génération est asynchrone.
        # Arrêt après environ 10 minutes ; l'API peut retourner l'URL ou la vidéo finalisée.
        for _ in range(60):
            time.sleep(10)
            response = requests.get(
                urljoin(BASE_URL, f"videos/{task_id}"),
                headers={"Authorization": f"Bearer {API_KEY}"}, timeout=TIMEOUT,
            )
            response.raise_for_status()
            status_data = response.json()
            video_url = find_value(status_data, "url") or find_value(status_data, "video_url")
            video_b64 = find_value(status_data, "b64_json") or find_value(status_data, "video_base64")
            status = str(find_value(status_data, "status") or "").lower()
            if video_b64:
                path.write_bytes(base64.b64decode(video_b64.split(",", 1)[-1]))
                break
            if video_url:
                download(video_url, path)
                break
            if status in {"failed", "error", "cancelled", "canceled"}:
                raise RuntimeError("La génération vidéo a échoué : " + json.dumps(status_data, ensure_ascii=False))
        else:
            raise TimeoutError("La génération vidéo n'est pas terminée après 10 minutes.")
    else:
        raise ValueError("Réponse vidéo sans URL, base64 ou identifiant de tâche : " + json.dumps(result, ensure_ascii=False))
    print(f"Vidéo enregistrée : {path}")


STEPS = [
    ("Chat", chat_step),
    ("Image", image_step),
    ("Vidéo", video_step),
]


def navigation(step):
    """Retourne -1 (précédent), 0 (refaire) ou +1 (suivant/terminer)."""
    print("\nQue souhaitez-vous faire ?")
    if step > 0:
        print("1. Revenir à l'étape précédente")
    print("2. Refaire l'étape actuelle")
    print("3. Passer à l'étape suivante" + (" (terminer)" if step == len(STEPS) - 1 else ""))
    while True:
        choice = input("Votre choix : ").strip()
        if choice == "1" and step > 0:
            return -1
        if choice == "2":
            return 0
        if choice == "3":
            return 1
        print("Choix invalide. Saisissez un numéro proposé.")


def main():
    global API_KEY
    try:
        API_KEY = api_key()
        step = 0
        while step < len(STEPS):
            name, action = STEPS[step]
            print(f"\n{'=' * 12} Étape {step + 1}/3 : {name} {'=' * 12}")
            try:
                action()
            except requests.HTTPError as exc:
                detail = exc.response.text[:2000] if exc.response is not None else str(exc)
                print(f"Erreur HTTP : {detail}")
            except (requests.RequestException, ValueError, RuntimeError, TimeoutError) as exc:
                print(f"Erreur pendant l'étape : {exc}")
            move = navigation(step)
            if move == 1:
                step += 1
            elif move == -1:
                step -= 1
        print("Parcours terminé. Au revoir !")
    except (KeyboardInterrupt, EOFError):
        print("\nProgramme interrompu.")
        return 130
    except (ValueError, requests.RequestException) as exc:
        print(f"Impossible de démarrer : {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
