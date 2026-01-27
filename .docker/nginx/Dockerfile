FROM nginx:alpine

# Installiere envsubst (für Template-Ersetzung)
RUN apk add --no-cache gettext

# Kopiere Template und Entrypoint
COPY nginx.conf.template /etc/nginx/nginx.conf.template
COPY entrypoint.sh /entrypoint.sh

# Mache Entrypoint ausführbar
RUN chmod +x /entrypoint.sh

EXPOSE 80

ENTRYPOINT ["/entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]