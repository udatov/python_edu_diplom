# include .example.env

SHELL = /bin/bash

PWD = $(shell pwd)

PAYMENT_API__ALEMBIC_DIR = $(PWD)/billing/payment_api/src/alembic_async
PAYMENT_API__ALEMBIC_CONFIG = $(PWD)/billing/payment_api/src/alembic_async/alembic.ini

#
# Payment API: Alembic
#
.PHONY: payment_api__alembic_init
payment_api__alembic_init:
	alembic --config ${PAYMENT_API__ALEMBIC_CONFIG} init billing/payment_api/src/alembic

.PHONY: build_payment-api-alembic_containers
build_payment-api-alembic_containers:
	ENV_FILE=${PROD_ENV_FILE} docker compose -f docker-compose.yml -f docker-compose/compose.dev.yml \
		--profile require__payment_api_alembic build --no-cache

.PHONY: run_payment-api-alembic_containers
run_payment-api-alembic_containers:
	make down_payment-api-alembic_containers
	ENV_FILE=${PROD_ENV_FILE} docker compose -f docker-compose.yml -f docker-compose/compose.dev.yml \
		--profile require__payment_api_alembic \
		up --build -d

.PHONY: down_payment-api-alembic_containers
down_payment-api-alembic_containers:
	ENV_FILE=${PROD_ENV_FILE} docker compose -f docker-compose.yml -f docker-compose/compose.dev.yml \
		--profile require__payment_api_alembic down
	rm -f billing/payment_api/src/alembic_async/versions/*.py

#
# Payment API: app
#
.PHONY: build_payment-api_docker
build_payment-api_docker:
	ENV_FILE=${PROD_ENV_FILE} docker compose --profile require__auth_api_alembic \
		--profile require__auth_service \
		--profile require__payment_api_alembic --profile require__redis \
		-f docker-compose.yml build


.PHONY: run_payment-api_docker
run_payment-api_docker:
	ENV_FILE=${PROD_ENV_FILE} docker compose --profile require__auth_api_alembic  \
		--profile require__auth_service \
		--profile require__payment_api_alembic --profile require__redis \
		-f docker-compose.yml -f docker-compose/compose.dev.yml up --build -d

.PHONY: down_payment-api_docker
down_payment-api_docker:
	ENV_FILE=${PROD_ENV_FILE} docker compose  --profile require__auth_api_alembic \
		--profile require__auth_service \
		--profile require__redis --profile require__payment_api_alembic \
		-f docker-compose.yml -f docker-compose/compose.dev.yml down -v
	docker rmi -f auth_service payment_api_alembic

#
# Payment API (app,tests): For debugging
#
.PHONY: run_payment-api-containers_for_debug
run_payment-api-containers_for_debug:
	make run_basedev_containers
	ENV_FILE=${DEV_ENV_FILE} $(PWD)/billing/payment_api/src/alembic_async/entry-point.sh

.PHONY: down_payment-api-containers_for_debug
down_payment-api-containers_for_debug:
	make down_basedev_containers
	rm -f $(PWD)/billing/payment_api/src/alembic_async/versions/*.py

#
# Payment API: end
#

#
# GUI: begin
#
.PHONY: build_gui_docker
build_gui_docker:
	ENV_FILE=${PROD_ENV_FILE} docker compose --profile require__redis \
		--profile require__auth_api_alembic \
		--profile require__auth_service \
		--profile require__payment_api_alembic \
		--profile require__payment_service \
		--profile require__gui_service \
		-f docker-compose.yml build


.PHONY: run_gui_docker
run_gui_docker:
	ENV_FILE=${PROD_ENV_FILE} docker compose --profile require__redis \
		--profile require__auth_api_alembic \
		--profile require__auth_service \
		--profile require__payment_api_alembic \
		--profile require__payment_service \
		--profile require__gui_service \
		-f docker-compose.yml -f docker-compose/compose.dev.yml up --build -d

.PHONY: down_gui_docker
down_gui_docker:
	ENV_FILE=${PROD_ENV_FILE} docker compose --profile require__redis \
		--profile require__auth_api_alembic \
		--profile require__auth_service \
		--profile require__payment_api_alembic \
		--profile require__payment_service \
		--profile require__gui_service \
		-f docker-compose.yml -f docker-compose/compose.dev.yml down -v
