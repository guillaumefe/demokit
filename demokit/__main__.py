#!/usr/bin/env python3

import os
import sys
import subprocess
import platform
import socket
import json
import shutil
import time
import signal
from pathlib import Path
from typing import Optional, List, Dict
import http.server
import threading
import click
import shutil
import importlib.resources
import importlib.util
import platform

class Color:
    GREEN = '\033[1;32m'
    RED = '\033[1;31m'
    NC = '\033[0m'
    YELLOW = '\033[1;33m'

class NoCacheHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

# Initialisation du dictionnaire des services internes
INTERNAL_SERVICES = {}

class DockerManager:
    def deploy_container(self, app_dir: Path, app_name: str, port: int) -> bool:
        """Déploie une application dans un conteneur Docker."""
        try:
            print(f"\n{Color.YELLOW}➡️  Déploiement de {app_name} sur le port {port}...{Color.NC}")
            subprocess.run(['docker', 'build', '-t', app_name, str(app_dir)], check=True)
            subprocess.run([
                'docker', 'run', '-d', '--rm',
                '--name', app_name,
                '-p', f"{port}:80",
                app_name
            ], check=True)
            print(f"{Color.GREEN}✅ {app_name} déployé avec succès sur le port {port}{Color.NC}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"{Color.RED}❌ Erreur lors du déploiement de {app_name}: {e}{Color.NC}")
            return False

class AppManager:
    def __init__(self):
        self.apps_dir = Path("apps")
        self.docker_manager = DockerManager()
        self.used_ports = set()

    def find_next_available_port(self, start: int = 3000, end: int = 5000) -> Optional[int]:
        for port in range(start, end + 1):
            if port not in self.used_ports:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    if s.connect_ex(('localhost', port)) != 0:
                        return port
        return None

    def deploy_apps(self) -> List[Dict]:
        deployed_apps = []
        if not self.apps_dir.exists():
            print(f"{Color.RED}❌ Aucun dossier 'apps' trouvé.{Color.NC}")
            return deployed_apps

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

            if self.docker_manager.deploy_container(app_dir, app_name, port):
                self.used_ports.add(port)
                deployed_apps.append({
                    "id": app_name,
                    "title": app_info.get('title', 'Sans titre'),
                    "description": app_info.get('description', 'Pas de description'),
                    "port": port,
                    "url": f"http://localhost:{port}"
                })
                INTERNAL_SERVICES[app_name] = port

        return deployed_apps

    def generate_catalog(self, apps: List[Dict]):
        catalog_content = """<!DOCTYPE html>
<html>
<head>
    <title>Catalogue des applications</title>
</head>
<body>
    <h1>Catalogue des applications</h1>
    <ul>
"""
        for app in apps:
            catalog_content += f"        <li><a href=\"/{app['id']}\">{app['title']}</a> - {app['description']}</li>\n"
        catalog_content += "    </ul>\n</body>\n</html>"

        with open("catalog.html", "w") as f:
            f.write(catalog_content)
        print(f"{Color.GREEN}✅ Catalogue généré avec succès.{Color.NC}")

class ReverseProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ['/', '/index.html']:
            try:
                with open("index.html", "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except FileNotFoundError:
                self.send_error(404, "Fichier index.html introuvable")
            return
        elif self.path.startswith("/catalog"):
            try:
                with open("catalog.html", "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except FileNotFoundError:
                self.send_error(404, "Fichier catalog.html introuvable")
            return
        elif self.path.lstrip('/') in INTERNAL_SERVICES:
            dest_host, dest_port = "127.0.0.1", INTERNAL_SERVICES[self.path.lstrip('/')]
            self.send_response(302)
            self.send_header("Location", f"http://{dest_host}:{dest_port}")
            self.end_headers()
        else:
            self.send_error(404, "Application non trouvée")

@click.command()
def main():
    global INTERNAL_SERVICES
    app_manager = AppManager()
    apps = app_manager.deploy_apps()
    app_manager.generate_catalog(apps)

    server_address = ("0.0.0.0", 80)
    with http.server.ThreadingHTTPServer(server_address, ReverseProxyHandler) as httpd:
        print(f"{Color.GREEN}🌍 Proxy inverse démarré sur le port 80{Color.NC}")
        httpd.serve_forever()

if __name__ == '__main__':
    main()
