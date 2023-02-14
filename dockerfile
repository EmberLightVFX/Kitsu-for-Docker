FROM nginx:alpine

LABEL maintainer="Jacob Danell <jacob@emberlight.se>"

RUN apk add git bash curl jq

ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8

COPY ./nginx.conf /etc/nginx/nginx.conf
COPY ./launch_kitsu.sh /launch_kitsu.sh

RUN mkdir /opt/kitsu

CMD /launch_kitsu.sh