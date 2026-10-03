#!/usr/bin/env python3
"""Parcours interactif RodiumAI : chat, image et vidéo (sans SDK)."""
import base64
import binascii
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

BASE_URL = "https://api.rodiumai.io/v1/"
TIMEOUT = 90
OUTPUT_DIR = Path("outputs")
API_KEY = ""


def load_local_env():
    """Charge simplement les variables KEY=VALUE d'un .env local, sans dépendance."""
    path = Path(".env")
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def api_headers():
    return {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def response_summary(response):
    try:
        return json.dumps(response.json(), ensure_ascii=False, indent=2)[:12000]
    except ValueError:
        return (response.text or "<corps de réponse vide>")[:12000]


def request_json(method, endpoint, payload=None):
    url = endpoint if endpoint.startswith("http") else urljoin(BASE_URL, endpoint.lstrip("/"))
    response = requests.request(method, url, headers=api_headers(), json=payload, timeout=TIMEOUT)
    print(f"[HTTP] {method} {url} -> {response.status_code}")
    if not response.ok:
        detail = response_summary(response)
        raise RuntimeError(f"Réponse API HTTP {response.status_code}. Détails :\n{detail}\n\nVérifiez la clé, le solde RODI, le modèle et le format du payload.")
    try:
        body = response.json()
    except ValueError:
        raise RuntimeError("L'API a répondu avec un succès HTTP mais pas du JSON. Réponse :\n" + (response.text or "<vide>")[:12000])
    return body


def nested_values(data):
    """Iterate nested dict/list values; includes OpenAI data[] envelopes."""
    yield data
    if isinstance(data, dict):
        for value in data.values():
            yield from nested_values(value)
    elif isinstance(data, list):
        for value in data:
            yield from nested_values(value)


def first_value(data, names):
    for node in nested_values(data):
        if isinstance(node, dict):
            for name in names:
                value = node.get(name)
                if value not in (None, ""):
                    return value
    return None


def show_response(label, result):
    print(f"[DEBUG] Réponse RodiumAI ({label}) :\n{json.dumps(result, ensure_ascii=False, indent=2)[:12000]}")


def save_b64(value, path):
    if isinstance(value, list):
        value = value[0] if value else ""
    if not isinstance(value, str):
        raise ValueError("La valeur base64 retournée n'est pas une chaîne.")
    encoded = value.split(",", 1)[-1] if value.startswith("data:") else value
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"Données base64 invalides : {exc}") from exc
    if not raw:
        raise ValueError("L'API a retourné un contenu base64 vide.")
    path.write_bytes(raw)


def download_file(url, path):
    # Les URLs de stockage peuvent être externes et signées : ne pas y transmettre la clé API.
    absolute = urljoin(BASE_URL, url)
    headers = {"Authorization": f"Bearer {API_KEY}"} if urlparse(absolute).netloc == urlparse(BASE_URL).netloc else {}
    response = requests.get(absolute, headers=headers, stream=True, timeout=180)
    print(f"[HTTP] GET fichier -> {response.status_code} ({absolute})")
    if not response.ok:
        raise RuntimeError(f"Téléchargement impossible (HTTP {response.status_code}) : {(response.text or '')[:4000]}")
    with path.open("wb") as output:
        for chunk in response.iter_content(1024 * 1024):
            if chunk:
                output.write(chunk)
    if path.stat().st_size == 0:
        raise RuntimeError("Le téléchargement a produit un fichier vide.")


def ensure_output_dir():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def chat_step():
    prompt = input("Votre question : ").strip()
    if not prompt:
        print("Question vide, aucun appel effectué.")
        return
    payload = {"messages": [{"role": "user", "content": prompt}]}
    result = request_json("POST", "chat/completions", payload)
    show_response("chat", result)
    answer = first_value(result, ["content", "text"])
    print("Réponse :", answer if answer is not None else "contenu introuvable (voir réponse brute ci-dessus)")
    print("cost_rodi :", first_value(result, ["cost_rodi"]) or "non fourni")


def image_step():
    prompt = input("Description de l'image : ").strip()
    if not prompt:
        print("Description vide, aucun appel effectué.")
        return
    payload = {"prompt": prompt}
    model = os.getenv("RODIUMAI_IMAGE_MODEL", "").strip()
    if model:
        payload["model"] = model
    payload["response_format"] = "b64_json"
    print("[DEBUG] POST /v1/images/generations payload :", json.dumps(payload, ensure_ascii=False))
    result = request_json("POST", "images/generations", payload)
    show_response("image", result)
    ensure_output_dir()
    path = OUTPUT_DIR / "output_image.png"
    encoded = first_value(result, ["b64_json", "image_base64", "base64"])
    image_url = first_value(result, ["url", "image_url", "output_url"])
    if encoded:
        save_b64(encoded, path)
    elif image_url:
        download_file(str(image_url), path)
    else:
        raise RuntimeError("Réponse image réussie, mais aucun b64_json/base64/URL reconnu. Réponse brute ci-dessus. Vérifiez le modèle et response_format.")
    print(f"Image créée : {path.resolve()} ({path.stat().st_size} octets)")


def video_step():
    prompt = input("Description de la vidéo : ").strip()
    if not prompt:
        print("Description vide, aucun appel effectué.")
        return
    payload = {"prompt": prompt}
    model = os.getenv("RODIUMAI_VIDEO_MODEL", "").strip()
    if model:
        payload["model"] = model
    print("[DEBUG] POST /v1/videos/generations payload :", json.dumps(payload, ensure_ascii=False))
    result = request_json("POST", "videos/generations", payload)
    show_response("vidéo, création", result)
    ensure_output_dir()
    path = OUTPUT_DIR / "output_video.mp4"
    deadline = time.monotonic() + 600
    current = result
    while True:
        encoded = first_value(current, ["b64_json", "video_base64", "video_b64", "base64"])
        video_url = first_value(current, ["video_url", "url", "output_url", "download_url"])
        if encoded:
            save_b64(encoded, path)
            break
        if video_url:
            download_file(str(video_url), path)
            break
        status = str(first_value(current, ["status", "state"]) or "").lower()
        if status in {"failed", "error", "cancelled", "canceled"}:
            raise RuntimeError("Génération vidéo échouée. Réponse brute :\n" + json.dumps(current, ensure_ascii=False, indent=2)[:12000])
        task_id = first_value(current, ["task_id", "request_id", "job_id", "id"])
        if not task_id:
            raise RuntimeError("Réponse vidéo sans URL/base64 ni identifiant de tâche reconnu. Réponse brute :\n" + json.dumps(current, ensure_ascii=False, indent=2)[:12000])
        if time.monotonic() >= deadline:
            raise TimeoutError(f"Tâche vidéo {task_id} toujours non terminée après 10 minutes. Dernière réponse :\n" + json.dumps(current, ensure_ascii=False, indent=2)[:12000])
        poll_url = first_value(current, ["poll_url", "status_url", "result_url"])
        if not poll_url:
            # Poll route commonly paired with the generation resource; status and raw response are logged.
            poll_url = f"videos/{task_id}"
        print(f"[DEBUG] Tâche vidéo {task_id}, statut={status or 'inconnu'}; nouvelle vérification dans 10 s via {poll_url}")
        time.sleep(10)
        current = request_json("GET", str(poll_url))
        show_response("vidéo, polling", current)
    print(f"Vidéo créée : {path.resolve()} ({path.stat().st_size} octets)")


STEPS = [("Chat", chat_step), ("Image", image_step), ("Vidéo", video_step)]


def navigation(step):
    print("\n1. Revenir à l'étape précédente" if step > 0 else "")
    print("2. Refaire l'étape actuelle")
    print("3. Passer à l'étape suivante" + (" (terminer)" if step == 2 else ""))
    while True:
        choice = input("Votre choix : ").strip()
        if choice == "1" and step > 0:
            return -1
        if choice == "2":
            return 0
        if choice == "3":
            return 1
        print("Choix invalide.")


def main():
    global API_KEY
    load_local_env()
    API_KEY = os.getenv("RODIUMAI_API_KEY", "").strip()
    if not API_KEY:
        print("RODIUMAI_API_KEY absente : renseignez .env (copie de .env.example) ou la variable d'environnement.", file=sys.stderr)
        return 1
    step = 0
    while step < len(STEPS):
        title, function = STEPS[step]
        print(f"\n===== Étape {step + 1}/3 : {title} =====")
        try:
            function()
        except KeyboardInterrupt:
            print("\nÉtape interrompue.")
        except (requests.RequestException, RuntimeError, ValueError, TimeoutError) as exc:
            print(f"\n[ERREUR] {exc}", file=sys.stderr)
            print("[AIDE] HTTP 401/403 : clé ou droits; 402/insufficient balance : solde; 400/422 : payload/modèle; 429 : quota/limite; 5xx : service amont. Consultez le détail HTTP ci-dessus.")
        move = navigation(step)
        if move == 1:
            step += 1
        elif move == -1:
            step -= 1
    print("Parcours terminé.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
