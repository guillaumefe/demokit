FROM php:8.2-apache

# Installation des dépendances nécessaires
RUN apt-get update && apt-get install -y \
    vim \
    git \
    && rm -rf /var/lib/apt/lists/*

# Configuration d'Apache
RUN a2enmod rewrite

# Création du répertoire de l'application
WORKDIR /var/www/html

# Copie des fichiers de l'application
COPY index.php /var/www/html/
COPY app-info.json /var/www/html/

# Création du fichier pour les messages stockés avec les permissions appropriées
RUN touch /var/www/html/stored_messages.txt && \
    chown www-data:www-data /var/www/html/stored_messages.txt && \
    chmod 666 /var/www/html/stored_messages.txt

# Configuration des permissions
RUN chown -R www-data:www-data /var/www/html

# Exposition du port 80
EXPOSE 80

# Commande par défaut pour démarrer Apache
CMD ["apache2-foreground"]
