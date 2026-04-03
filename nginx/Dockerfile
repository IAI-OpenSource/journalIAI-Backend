# STAGE 1 : Le "Builder"
FROM openresty/openresty:alpine-fat AS builder

RUN apk add --no-cache git openssl-dev
RUN luarocks install lua-resty-jwt
RUN luarocks install lua-resty-openssl
# STAGE 2 : L'image de Production (Optimisée)
FROM openresty/openresty:alpine

# On ne récupère QUE les fichiers nécessaires depuis le builder
COPY --from=builder /usr/local/openresty/luajit/share/lua/5.1/resty/ /usr/local/openresty/lualib/resty/

# Optionnel : Si le module a des dépendances C (.so), il faut aussi les copier
# Pour lua-resty-jwt, ce sont principalement des fichiers .lua

# Installation uniquement des librairies de runtime (pas de compilateur)
RUN apk add --no-cache libssl3 libcrypto3

# Ton code applicatif
COPY ./lua /etc/nginx/lua