# Utilisation d'une image Nginx légère
FROM nginx:alpine

# Copie des fichiers statiques dans le répertoire par défaut de Nginx
COPY ./index.html /usr/share/nginx/html/
COPY ./results.html /usr/share/nginx/html/

# Exposition du port 80
EXPOSE 80

# Commande par défaut de Nginx
CMD ["nginx", "-g", "daemon off;"]
