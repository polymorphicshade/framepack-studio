# TLS front end for FramePack Studio.
#
# Stock nginx plus two things it doesn't ship: the openssl CLI (to mint the
# self-signed cert on first boot) and curl (for the compose healthcheck).
ARG NGINX_IMAGE=nginx:stable-alpine
FROM ${NGINX_IMAGE}

RUN apk add --no-cache openssl curl

COPY entrypoint.sh /usr/local/bin/tls-entrypoint.sh
RUN sed -i 's/\r$//' /usr/local/bin/tls-entrypoint.sh \
    && chmod +x /usr/local/bin/tls-entrypoint.sh

EXPOSE 443

# Generates the cert if missing, then hands off to nginx's own entrypoint.
ENTRYPOINT ["/usr/local/bin/tls-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
