FROM php:8.3-fpm
COPY . /srv/app
WORKDIR /srv/app
RUN composer install --no-dev --prefer-dist
