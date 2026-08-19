#!/bin/sh
# Mint a self-signed certificate on first boot, then start nginx.
set -eu

CERT_DIR="${TLS_CERT_DIR:-/etc/nginx/certs}"
CRT="${CERT_DIR}/fullchain.pem"
KEY="${CERT_DIR}/privkey.pem"

mkdir -p "${CERT_DIR}"

if [ -s "${CRT}" ] && [ -s "${KEY}" ]; then
    echo "TLS: using existing certificate ${CRT}"
else
    CN="${TLS_COMMON_NAME:-localhost}"
    SAN="${TLS_SAN:-DNS:localhost,IP:127.0.0.1}"

    echo "TLS: no certificate found, generating a self-signed one for CN=${CN}"
    # -addext keeps the SAN present; browsers have ignored CN alone for years,
    # so without it even an exception-added cert misbehaves.
    openssl req -x509 -newkey rsa:2048 -sha256 -nodes \
        -days "${TLS_DAYS:-3650}" \
        -keyout "${KEY}" -out "${CRT}" \
        -subj "/CN=${CN}" \
        -addext "subjectAltName=${SAN}" \
        -addext "basicConstraints=critical,CA:FALSE" \
        -addext "keyUsage=critical,digitalSignature,keyEncipherment" \
        -addext "extendedKeyUsage=serverAuth"
    chmod 600 "${KEY}"
    echo "TLS: generated ${CRT} (SAN: ${SAN})"
    echo "TLS: replace both files in this volume with real ones to use a CA cert"
fi

# /docker-entrypoint.sh is nginx's own; it applies its standard init then execs.
exec /docker-entrypoint.sh "$@"
