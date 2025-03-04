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
import socketserver
import threading
import click
import shutil
import importlib.resources
import importlib.util
import platform  # Pour détecter l'OS

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

class DockerManager:
    @staticmethod
    def check_docker(wait=False):
        """Vérifie si Docker est installé et en cours d'exécution"""
        def is_docker_running():
            try:
                subprocess.run(['docker', 'ps'], capture_output=True, check=True)
                return True
            except (subprocess.CalledProcessError, FileNotFoundError):
                return False

        if is_docker_running():
            return True

        print("\n⚠️  Docker n'est pas démarré")
        print("\n🐳 État : Docker est installé mais pas en cours d'exécution")
        print("\n🚀 Pour démarrer Docker :")
        
        if platform.system() == "Darwin":  # MacOS
            print("\n1. Ouvrez Docker Desktop depuis vos Applications")
            print("2. Attendez que l'icône 🐳 dans la barre de menu indique 'Docker is running'")
        elif platform.system() == "Windows":
            print("\n1. Ouvrez Docker Desktop depuis le menu Démarrer")
            print("2. Attendez que l'icône 🐳 dans la barre des tâches devienne stable")
        else:  # Linux
            print("\n1. Démarrez le service Docker :")
            print("   sudo systemctl start docker")

        if wait:
            print("\n⏳ En attente du démarrage de Docker", end="", flush=True)
            for _ in range(30):  # Attendre maximum 30 secondes
                time.sleep(1)
                print(".", end="", flush=True)
                if is_docker_running():
                    print("\n\n✅ Docker est maintenant démarré !")
                    return True
            print("\n\n❌ Docker n'a pas démarré dans le temps imparti.")
        else:
            print("\n⏳ Une fois Docker démarré, relancez DemoKit")
        
        sys.exit(1)

    def cleanup_container(self, container_name: str):
        # Vérifier Docker avant toute tentative de nettoyage
        if not self.check_docker():
            return
        try:
            result = subprocess.run(
                ['docker', 'ps', '-a', '--format', '{{.Names}}'],
                capture_output=True,
                text=True,
                check=True
            )
            if container_name in result.stdout.split('\n'):
                subprocess.run(['docker', 'stop', container_name], 
                             capture_output=True,
                             check=False)
                subprocess.run(['docker', 'rm', '-f', container_name],
                             capture_output=True,
                             check=False)
        except subprocess.CalledProcessError as e:
            print(f"Erreur lors du nettoyage du conteneur {container_name}: {e}")

    def check_port_conflict(self, port: int) -> bool:
        try:
            result = subprocess.run(
                ['docker', 'ps', '--format', '{{.Ports}}'],
                capture_output=True,
                text=True,
                check=True
            )
            return f":{port}->" in result.stdout or f":{port}/" in result.stdout
        except subprocess.CalledProcessError:
            return False

    def deploy_container(self, app_dir: Path, app_name: str, port: int) -> bool:
        # Vérifier Docker avant toute tentative de déploiement
        if not self.check_docker():
            return False
        try:
            self.cleanup_container(app_name)

            if self.check_port_conflict(port):
                print(f"Le port {port} est déjà utilisé par un autre conteneur")
                return False

            print(f"Construction de l'image pour {app_name}...")
            build_result = subprocess.run(
                ['docker', 'build', '-t', app_name, str(app_dir)],
                capture_output=True,
                text=True
            )
            if build_result.returncode != 0:
                print(f"Erreur de build pour {app_name}: {build_result.stderr}")
                return False

            print(f"Lancement du conteneur {app_name} sur le port {port}...")
            run_result = subprocess.run(
                ['docker', 'run', '-d', '--rm',
                 '--name', app_name,
                 '-p', f"{port}:80",
                 app_name],
                capture_output=True,
                text=True
            )
            if run_result.returncode != 0:
                print(f"Erreur de lancement pour {app_name}: {run_result.stderr}")
                return False

            time.sleep(2)
            check_result = subprocess.run(
                ['docker', 'ps', '--format', '{{.Names}}'],
                capture_output=True,
                text=True
            )
            if app_name not in check_result.stdout:
                print(f"Le conteneur {app_name} n'a pas démarré correctement")
                return False

            print(f"✅ Conteneur {app_name} déployé avec succès sur le port {port}")
            return True

        except Exception as e:
            print(f"Erreur inattendue lors du déploiement de {app_name}: {str(e)}")
            return False

    def cleanup_all(self):
        try:
            result = subprocess.run(
                ['docker', 'ps', '-a', '--format', '{{.Names}}'],
                capture_output=True,
                text=True,
                check=True
            )
            for container in result.stdout.strip().split('\n'):
                if container:
                    self.cleanup_container(container)
        except Exception as e:
            print(f"Erreur lors du nettoyage global: {str(e)}")

class PortManager:
    @staticmethod
    def is_port_available(port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('', port))
                return True
            except OSError:
                return False

    @classmethod
    def find_available_port(cls, start: int, end: int) -> Optional[int]:
        for port in range(start, end + 1):
            if cls.is_port_available(port):
                return port
        return None

class WebServer:
    def __init__(self, port: int, directory: str = '.'):
        self.port = port
        self.directory = directory
        self.httpd = None

    def start(self):
        os.chdir(self.directory)
        handler = NoCacheHTTPRequestHandler
        self.httpd = socketserver.TCPServer(("0.0.0.0", self.port), handler)
        print(f"Serveur web démarré sur le port {self.port}, répertoire : {self.directory}")
        self.httpd.serve_forever()

class AppManager:
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.template_file = self.base_path / "catalog.template.html"
        self.splash_file = self.base_path / "splash.html"
        self.docker_manager = DockerManager()
        self.used_ports = set()

        if not self.template_file.exists():
            print(f"Erreur: Template {self.template_file} manquant")
            sys.exit(1)
        if not self.splash_file.exists():
            print(f"Erreur: Template {self.splash_file} manquant")
            sys.exit(1)

    def find_next_available_port(self, start: int = 3000, end: int = 5000) -> Optional[int]:
        for port in range(start, end + 1):
            if port not in self.used_ports and PortManager.is_port_available(port):
                if not self.docker_manager.check_port_conflict(port):
                    return port
        return None

    def generate_main_page(self, catalog_port: int):
        with open(self.splash_file, "r") as f:
            splash_content = f.read()

        main_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Accueil</title>
    <style>
        body {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            font-family: Arial, sans-serif;
            background: #f4f4f9;
        }}
        button {{
            padding: 15px 30px;
            font-size: 18px;
            font-weight: bold;
            color: #fff;
            background: #007bff;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            transition: background 0.3s ease;
        }}
        button:hover {{
            background: #0056b3;
        }}
    </style>
</head>
<body>
{splash_content}
<button onclick="location.href='http://' + window.location.hostname + ':{catalog_port}/catalog.html'">Parcourir les apps</button>
</body>
</html>"""

        with open("index.html", "w") as f:
            f.write(main_page)

    def deploy_apps(self) -> List[Dict]:
        deployed_apps = []
        app_infos = list(Path('apps').rglob('app-info.json'))
        
        if not app_infos:
            print("Aucune application trouvée (pas de fichier app-info.json)")
            return deployed_apps

        for app_info_path in app_infos:
            app_dir = app_info_path.parent
            app_name = app_dir.name.lower()

            try:
                with open(app_info_path) as f:
                    try:
                        app_info = json.load(f)
                    except json.JSONDecodeError:
                        print(f"Fichier app-info.json invalide dans {app_dir}")
                        continue

                port = self.find_next_available_port()
                if not port:
                    print(f"Pas de port disponible pour {app_name}")
                    continue

                if self.docker_manager.deploy_container(app_dir, app_name, port):
                    self.used_ports.add(port)
                    deployed_apps.append({
                        "id": app_name,
                        "category": "Applications",
                        "title": app_info.get('title', 'Sans titre'),
                        "description": app_info.get('description', 'Pas de description'),
                        "port": port,
                        "url": f"http://localhost:{port}"
                    })
                else:
                    print(f"Échec du déploiement de {app_name}")

            except Exception as e:
                print(f"Erreur lors du traitement de {app_name}: {str(e)}")
                continue

        return deployed_apps

    def generate_catalog(self, apps: List[Dict]):
        with open(self.template_file) as f:
            template = f.read()

        apps_data = []
        for app in sorted(apps, key=lambda x: x['title']):
            app_data = app.copy()
            app_data['url'] = f"http://__HOST__:{app_data['port']}"
            app_data['port'] = str(app_data['port'])
            apps_data.append(app_data)

        apps_json = json.dumps(apps_data)
        catalog_content = template.replace('{{VULNERABILITIES_DATA}}', apps_json)

        with open("catalog.html", "w") as f:
            f.write(catalog_content)

        print("\nVérification des URLs générées dans le catalogue:")
        for app in apps_data:
            print(f"- {app['title']}: {app['url']}")

def display_summary(main_port: int, catalog_port: int):
    print("\n===== Résumé des informations utiles =====")
    print(f"\n📌 Serveur principal : {Color.GREEN}http://localhost:{main_port}{Color.NC}")
    print(f"📌 Catalogue des applications : {Color.GREEN}http://localhost:{catalog_port}/catalog.html{Color.NC}")
    print("\n🛠️  Informations pour le formateur :")
    print("1. Utilisez l'URL du catalogue pour accéder à toutes les applications hébergées")
    print("2. Si vous ajoutez de nouvelles applications avec 'app-info.json', redémarrez le script")
    print("3. Assurez-vous que Docker fonctionne correctement pour déployer les conteneurs")
    print(f"\n🔍 Ports utilisés :")
    print(f"   - Port serveur principal : {main_port}")
    print(f"   - Port catalogue des applications : {catalog_port}")
    print(f"\n🎯 Pour arrêter le serveur :")
    print(f"   {Color.RED}pkill -f \"python3 -m http.server\"{Color.NC}")
    print("\n==========================================")

def initialize_workspace():
    """Initialise le workspace avec les applications du package"""
    apps_dir = Path('apps')
    if not apps_dir.exists():
        print("\n🚀 Initialisation de DemoKit")
        
        # Trouver le chemin du package installé
        spec = importlib.util.find_spec('demokit')
        if spec:
            package_path = Path(spec.origin).parent
            package_apps = package_path / 'apps'
            
            if package_apps.exists() and any(package_apps.iterdir()):
                print("\n📁 Copie des applications de démonstration...")
                shutil.copytree(str(package_apps), str(apps_dir), dirs_exist_ok=True)
                print("✅ Applications copiées avec succès")
                return apps_dir
            
    return apps_dir

@click.command()
@click.option('--wait-docker', is_flag=True, help="Attendre que Docker démarre")
def main(wait_docker):
    try:
        # Vérification du dossier apps
        apps_dir = initialize_workspace()

        if not apps_dir.exists():
            apps_dir.mkdir(exist_ok=True)
            print("\n🚀 Initialisation de DemoKit")
            print("\n📁 Le dossier 'apps' a été créé.")
            print("\nPour utiliser DemoKit:")
            print("1. Créez un dossier pour chaque application dans 'apps/'")
            print("2. Ajoutez un fichier app-info.json dans chaque dossier")
            print("3. Ajoutez un Dockerfile dans chaque dossier")
            print("4. Relancez demokit")
            sys.exit(0)

        # Vérification des applications
        app_infos = list(apps_dir.rglob('app-info.json'))
        if not app_infos:
            print("\n❌ Aucune application trouvée dans le dossier 'apps'")
            print("\nStructure attendue:")
            print("apps/")
            print("├── app1/")
            print("│   ├── app-info.json")
            print("│   └── Dockerfile")
            print("└── app2/")
            print("    ├── app-info.json")
            print("    └── Dockerfile")
            sys.exit(0)

        docker_manager = DockerManager()
        app_manager = AppManager()

        # Passer le paramètre wait_docker au check
        if not docker_manager.check_docker(wait=wait_docker):
            sys.exit(1)

        if PortManager.is_port_available(80) and not docker_manager.check_port_conflict(80):
            main_port = 80
        else:
            main_port = PortManager.find_available_port(8000, 8100)

        catalog_port = PortManager.find_available_port(8101, 8200)

        if not main_port or not catalog_port:
            print("Pas de ports disponibles")
            sys.exit(1)

        apps = app_manager.deploy_apps()
        app_manager.generate_catalog(apps)
        app_manager.generate_main_page(catalog_port)

        main_server = threading.Thread(
            target=lambda: WebServer(main_port).start(),
            daemon=True
        )
        catalog_server = threading.Thread(
            target=lambda: WebServer(catalog_port).start(),
            daemon=True
        )

        main_server.start()
        catalog_server.start()

        display_summary(main_port, catalog_port)

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n👋 Arrêt de DemoKit...")
        if 'app_manager' in locals():
            app_manager.docker_manager.cleanup_all()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erreur: {str(e)}")
        if 'app_manager' in locals():
            app_manager.docker_manager.cleanup_all()
        sys.exit(1)

if __name__ == '__main__':
    main()
