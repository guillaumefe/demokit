#!/usr/bin/env python3

import os
import sys
import subprocess
import socket
import json
import time
from pathlib import Path
from typing import Optional, List, Dict
import http.server
import threading
import click
import urllib.request

class Color:
    GREEN = '\033[1;32m'
    RED = '\033[1;31m'
    NC = '\033[0m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[1;34m'
    CYAN = '\033[1;36m'

# Dictionnaire associant le nom d'une app à son port
INTERNAL_SERVICES = {}
# Répertoire contenant index.html, catalog.template.html et catalog.html
STATIC_FILES_PATH = Path(__file__).parent

def check_docker_scout():
    """
    Vérifie que la commande 'docker scout' fonctionne.
    Si ce n'est pas le cas, affiche un message indiquant à l'utilisateur
    comment activer Docker Scout (exécuter 'docker scout enable' ou mettre à jour Docker Desktop).
    """
    try:
        result = subprocess.run(["docker", "scout", "--version"],
                                capture_output=True, text=True, check=True)
        print(f"{Color.GREEN}Docker Scout activé (version : {result.stdout.strip()}){Color.NC}")
    except subprocess.CalledProcessError:
        print(f"{Color.RED}Docker Scout n'est pas activé.{Color.NC}")
        print(f"{Color.YELLOW}Pour activer Docker Scout, exécutez : 'docker scout enable'{Color.NC}")
        print(f"{Color.YELLOW}ou mettez à jour Docker Desktop vers la dernière version.{Color.NC}")

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """ Serveur HTTP qui gère les fichiers statiques et le reverse proxy. """
    def do_GET(self):
        # Gestion des fichiers statiques : index.html et catalog.html
        requested_file = self.path.lstrip("/")
        if requested_file in ["", "index.html", "catalog.html"]:
            # Si rien n'est précisé, on sert index.html
            file_name = "index.html" if requested_file in ["", "index.html"] else "catalog.html"
            file_path = STATIC_FILES_PATH / file_name
            if file_path.is_file():
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
                return
            else:
                self.send_error(404, "Page non trouvée")
                return

        # Reverse Proxy : redirige les requêtes vers les apps (URL de type /app_name/...)
        parts = self.path.split("/")
        if len(parts) > 1:
            app_name = parts[1]
            if app_name in INTERNAL_SERVICES:
                target_port = INTERNAL_SERVICES[app_name]
                # Conserver le reste de l'URL après /app_name/
                suffix = self.path[len(f"/{app_name}"):]
                url = f"http://localhost:{target_port}{suffix}"
                try:
                    with urllib.request.urlopen(url) as response:
                        self.send_response(response.status)
                        for header in response.headers:
                            self.send_header(header, response.headers[header])
                        self.end_headers()
                        self.wfile.write(response.read())
                    return
                except Exception as e:
                    self.send_error(502, f"Erreur proxy vers {url} : {e}")
                    return
        self.send_error(404, "Page non trouvée")

class DockerManager:
    def is_docker_running(self) -> bool:
        """ Vérifie si Docker est lancé. """
        try:
            subprocess.run(['docker', 'info'], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError:
            return False

    def stop_existing_container(self, app_name: str):
        """ Arrête et supprime un conteneur si déjà existant. """
        try:
            existing_container = subprocess.run(
                ['docker', 'ps', '-q', '-f', f'name={app_name}'],
                stdout=subprocess.PIPE, text=True).stdout.strip()
            if existing_container:
                print(f"{Color.YELLOW}🛑 Un conteneur existant {app_name} a été trouvé. Suppression en cours...{Color.NC}")
                subprocess.run(['docker', 'stop', app_name], check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(['docker', 'rm', '-f', app_name], check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            print(f"{Color.RED}⚠️  Impossible de supprimer {app_name}: {e}{Color.NC}")

    def deploy_container(self, app_dir: Path, app_name: str, port: int, attempt: int = 1) -> bool:
        """ Déploie une application avec jusqu'à 3 tentatives et affiche Docker Scout Quickview. """
        try:
            print(f"\n{Color.YELLOW}➡️  Déploiement de {app_name} sur le port {port} (Tentative {attempt}/3)...{Color.NC}")
            self.stop_existing_container(app_name)
            subprocess.run(['docker', 'build', '-t', app_name, str(app_dir)], check=True)
            subprocess.run([
                'docker', 'run', '-d',
                '--name', app_name,
                '-p', f"{port}:80",
                app_name
            ], check=True)
            print(f"{Color.GREEN}✅ {app_name} déployé avec succès sur /{app_name}/{Color.NC}")
            INTERNAL_SERVICES[app_name] = port

            print(f"{Color.BLUE}🔍 Analyse de {app_name} avec Docker Scout Quickview...{Color.NC}")
            scout_result = subprocess.run(['docker', 'scout', 'quickview', app_name],
                                capture_output=True, text=True)
            if scout_result.returncode != 0:
                print(f"{Color.CYAN}⚠️  Docker Scout Quickview n'est pas activé, analyse ignorée pour {app_name}.{Color.NC}")
            else:
                output = scout_result.stdout.strip()
                if output:
                    print(f"{Color.CYAN}{output}{Color.NC}")
                else:
                    print(f"{Color.CYAN}⚠️  Aucune analyse disponible pour {app_name}.{Color.NC}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"{Color.RED}❌ Erreur lors du déploiement de {app_name} (Tentative {attempt}/3): {e}{Color.NC}")
            time.sleep(5 * attempt)
            return False

class AppManager:
    def __init__(self):
        self.apps_dir = STATIC_FILES_PATH / "apps"
        self.docker_manager = DockerManager()
        self.used_ports = set()
        self.deployed_apps = []
        self.failed_apps = []

    def find_next_available_port(self, start: int = 3000, end: int = 5000) -> Optional[int]:
        for port in range(start, end + 1):
            if port not in self.used_ports:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    if s.connect_ex(('localhost', port)) != 0:
                        return port
        return None

    def deploy_apps(self) -> List[Dict]:
        if not self.apps_dir.exists():
            print(f"{Color.RED}❌ Aucun dossier 'apps' trouvé.{Color.NC}")
            return []

        if not self.docker_manager.is_docker_running():
            print(f"{Color.RED}❌ Docker n'est pas lancé. Veuillez démarrer Docker et réessayer.{Color.NC}")
            sys.exit(1)

        # Déployer les apps et accumuler les échecs pour retry
        for app_info_path in self.apps_dir.rglob('app-info.json'):
            app_dir = app_info_path.parent
            app_name = app_dir.name.lower()
            try:
                with open(app_info_path) as f:
                    app_info = json.load(f)
            except json.JSONDecodeError:
                print(f"{Color.RED}⚠️  Fichier app-info.json invalide dans {app_dir}{Color.NC}")
                continue

            port = self.find_next_available_port()
            if not port:
                print(f"{Color.RED}❌ Pas de port disponible pour {app_name}{Color.NC}")
                continue

            success = self.docker_manager.deploy_container(app_dir, app_name, port)
            if success:
                self.used_ports.add(port)
                self.deployed_apps.append({
                    "id": app_name,
                    "title": app_info.get('title', 'Sans titre'),
                    "description": app_info.get('description', 'Pas de description'),
                    "category": app_info.get('category', 'Autre'),
                    "url": f"/{app_name}/"
                })
            else:
                self.failed_apps.append((app_dir, app_name, port))

        # Retry pour les échecs
        for app_dir, app_name, port in self.failed_apps:
            for attempt in range(2, 4):
                if self.docker_manager.deploy_container(app_dir, app_name, port, attempt):
                    self.deployed_apps.append({
                        "id": app_name,
                        "title": app_name,  # Si app-info n'est pas accessible, on utilise app_name
                        "url": f"/{app_name}/"
                    })
                    break

        # Trier les apps : apps commençant par 'a' d'abord, puis bonus, puis metier
        self.deployed_apps.sort(key=lambda x: (
            0 if x['id'].startswith("a") else 1 if x['id'].startswith("bonus") else 2 if x['id'].startswith("metier") else 3,
            x['id']
        ))
        return self.deployed_apps

    def print_summary(self):
        border = "=" * 40
        print(f"\n{Color.CYAN}{border}")
        print("✅ DÉPLOIEMENT TERMINÉ ✅")
        print(f"{border}{Color.NC}")
        print(f"📌 Serveur accessible à l'URL : {Color.YELLOW}http://localhost{Color.NC}")
        print(f"📄 Catalogue des applications : {Color.YELLOW}http://localhost/catalog.html{Color.NC}\n")
        if self.deployed_apps:
            print(f"{Color.CYAN}🔗 Liste des applications déployées :{Color.NC}")
            # Utiliser l'ordre trié
            for app in self.deployed_apps:
                print(f"  - {Color.YELLOW}{app['title']}{Color.NC} ➝ {Color.BLUE}http://localhost{app['url']}{Color.NC}")
        else:
            print(f"{Color.RED}❌ Aucune application n'a été déployée.{Color.NC}")

    def generate_catalog(self):
        """ Génère catalog.html à partir du template catalog.template.html. """
        template_path = STATIC_FILES_PATH / "catalog.template.html"
        catalog_path = template_path.parent / "catalog.html"


        if not template_path.exists():
            print(f"{Color.RED}❌ Le fichier template {template_path} est introuvable !{Color.NC}")
            return

        try:
            with open(template_path, "r", encoding="utf-8") as template_file:
                template_content = template_file.read()
            vulnerabilities_data = json.dumps(self.deployed_apps, ensure_ascii=False, indent=4)
            output_content = template_content.replace("{{VULNERABILITIES_DATA}}", vulnerabilities_data)
            with open(catalog_path, "w", encoding="utf-8") as output_file:
                output_file.write(output_content)
            print(f"{Color.GREEN}📄 Catalogue généré avec succès : {catalog_path}{Color.NC}")
        except Exception as e:
            print(f"{Color.RED}❌ Erreur lors de la génération du catalogue : {e}{Color.NC}")

@click.command()
def main():

    # Vérification de Docker Scout
    try:
        scout_version = subprocess.run(["docker", "scout", "--version"],
                                     capture_output=True, text=True, check=True)
        print(f"{Color.GREEN}Docker Scout activé (version : {scout_version.stdout.strip()}){Color.NC}")
    except subprocess.CalledProcessError:
        print(f"{Color.RED}Docker Scout ne fonctionne pas correctement.{Color.NC}")
        print(f"{Color.YELLOW}Pour activer Docker Scout, assurez-vous d'avoir la dernière version de Docker Desktop ou utilisez 'docker scout repo enable <repository>' selon votre configuration.{Color.NC}")

    app_manager = AppManager()
    app_manager.deploy_apps()
    app_manager.generate_catalog()
    app_manager.print_summary()

    server_address = ("0.0.0.0", 80)
    with http.server.ThreadingHTTPServer(server_address, CustomHTTPRequestHandler) as httpd:
        print(f"{Color.GREEN}🌍 Serveur proxy démarré{Color.NC}")
        httpd.serve_forever()

if __name__ == '__main__':
    main()

