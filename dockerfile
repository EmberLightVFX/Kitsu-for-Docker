FROM nginx:alpine as buildStage

LABEL maintainer="Jacob Danell <jacob@emberlight.se>"

USER root

WORKDIR /opt

RUN apk add --no-cache --virtual .build-deps git

ARG KITSU_VERSION

RUN git clone -b "v${KITSU_VERSION}" --single-branch --depth 1 https://github.com/cgwire/kitsu\
    && apk --purge del .build-deps


FROM nginx:alpine as squashStage
COPY --from=buildStage / /

COPY ./nginx.conf /etc/nginx/nginx.conf
