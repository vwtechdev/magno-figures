FROM nginx:1.25-alpine

RUN apk add --no-cache curl && rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/templates/default.conf.template

EXPOSE 80
