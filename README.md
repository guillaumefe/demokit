# DemoKit 2.0

Un outil simple pour déployer et gérer des applications de démonstration via Docker.

## Prérequis

Avant d'installer DemoKit, assurez-vous d'avoir :

1. **Python 3.6 ou supérieur**
   - Vérifiez avec : `python --version`
   - Installation : https://www.python.org/downloads/

2. **Docker**
   - MacOS :
     ```bash
     # Via Homebrew
     brew install --cask docker
     # Lancez ensuite Docker Desktop
     ```
   - Debian/Ubuntu :
     ```bash
     sudo apt-get update
     sudo apt-get install -y docker.io
     sudo systemctl start docker
     sudo systemctl enable docker
     sudo usermod -aG docker $USER  # Ajout de l'utilisateur au groupe docker
     # Déconnectez-vous et reconnectez-vous
     ```
   - Autres systèmes : https://docs.docker.com/engine/install/

3. **pip** (gestionnaire de paquets Python)
   ```bash
   python -m ensurepip --upgrade
   ```

## Installation

```bash
pip install demokit
```

## Utilisation

1. Créez un nouveau dossier pour votre projet :
   ```bash
   mkdir mon-projet
   cd mon-projet
   ```

2. Initialisez DemoKit :
   ```bash
   demokit
   ```

3. Ajoutez vos applications dans le dossier `apps/` créé :
   ```
   apps/
   ├── app1/
   │   ├── app-info.json
   │   └── Dockerfile
   └── app2/
       ├── app-info.json
       └── Dockerfile
   ```

4. Relancez DemoKit pour déployer vos applications :
   ```bash
   demokit
   ```

## Configuration

Chaque application nécessite :

1. Un `app-info.json` :
   ```json
   {
       "title": "Mon Application",
       "description": "Description de l'application",
       "version": "1.0.0"
   }
   ```

2. Un `Dockerfile` pour construire l'image Docker

## Options

```bash
demokit --help          # Affiche l'aide
demokit --port 9000     # Change le port principal
demokit --catalog-port 9001  # Change le port du catalogue
demokit --debug         # Active les logs détaillés
```

## Support

Pour les problèmes courants :

1. **Docker n'est pas accessible**
   - Vérifiez que Docker est installé : `docker --version`
   - Vérifiez que le service tourne : `docker ps`
   - Sur Linux, vérifiez les permissions : `groups` (docker doit apparaître)

2. **Ports déjà utilisés**
   - Utilisez d'autres ports : `demokit --port 9000 --catalog-port 9001`

# Tutoriel : Cloner et Créer Son Propre Package Python avec Flit

Ce tutoriel vous guide à travers les étapes nécessaires pour cloner ce dépôt, installer les dépendances et créer votre propre package Python utilisant Flit.

## Table des matières
1. [Cloner le Dépôt](#cloner-le-dépôt)
2. [Installer les Désendances](#installer-les-dépendances)
3. [Créer un Nouveau Package avec Flit](#créer-un-nouveau-package-avec-flit)

## Cloner le Dépôt

Pour commencer, vous devez cloner ce dépôt sur votre machine locale.

```bash
git clone https://github.com/yourusername/demokit.git
cd demokit
```

## Installer les Dépendances
Assurez-vous d'avoir Python et pip installés sur votre système. Vous pouvez installer les dépendances du projet en utilisant le fichier `requirements.txt`.

```
pip install -r requirements.txt
```

## Créer un Nouveau Package avec Flit
Pour créer un nouveau package, vous devez d'abord installer Flit.

```
pip install flit
```

Modifiez le contenu du code source. Par exemple, pour ajouter une nouvelle "APP" :

```
mkdir -p demokit/apps/APP-A{new number here}/public
touch demokit/apps/APP-A0/Dockerfile demokit/apps/APP-A0/app-info.json demokit/apps/APP-A0/public/index.html
# Copier tel quel le contenu d'un Dockerfile précédent dans le nouveau Dockerfile
# Copier le contenu d'un app-info.json précédent comme modèle puis le modifier en conséquence
# Concevez de toute pièce un fichier public/index.html correspondant aux attentes
```

Editez le fichier `demokit/__init__.py` pour incrémenter le numéro de version de votre package. Voici un exemple de contenu basique :

```
vim demokit/__init__.py
```

Modifiez le fichier pyproject.toml. Ce fichier doit contenir les informations nécessaires, par exemple :

```
[build-system]
requires = ["flit_core >=3.2,<4"]
build-backend = "flit_core.buildapi"

[tool.flit.metadata]
name = "nom_de_votre_package"
author = "Votre Nom"
author-email = "votre.email@example.com"
description = "Description courte de votre package"
```

Vous pouvez maintenant construire et installer localement votre package :

```
flit build
```

Cela va générer un fichier .tar.gz et un .whl dans le dossier dist/.

Pour tester le package sans le publier :
*Les fichiers du package sont copiés dans l'environnement, créant une version "figée" du package. Les modifications ultérieures apportées au code source dans le répertoire de développement ne seront pas reflétées dans l'installation.*

```
flit install
```

Ou pour une installation en mode développement :
*L'option --symlink lors de l'installation avec flit permet d'installer le package en mode développement. Au lieu de copier les fichiers dans votre environnement Python, flit crée un lien symbolique (symlink) qui pointe vers le répertoire source de votre package. Cela signifie que toutes les modifications apportées au code source seront immédiatement prises en compte, sans avoir à réinstaller le package à chaque changement. C'est particulièrement utile pour tester et développer votre package de manière itérative.*

```
flit install --symlink
```

Dans un script Python ou un interpréteur interactif, essayez :

```
import mon_projet
print(mon_projet.__version__)
```

Si tout fonctionne, votre package est prêt !

Pour publier votre package sur PyPI, vous devez d'abord configurer les informations d'identification. Créez un fichier .pypirc dans votre répertoire personnel avec le contenu suivant :

```
[distutils]
index-servers = pypi

[pypi]
username:your_username
password:your_password
```

Puis publiez votre package avec Flit :

```
flit publish
```
