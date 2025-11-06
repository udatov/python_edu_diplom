# include .example.env

SHELL = /bin/bash

PWD = $(shell pwd)

COMMON_DIR = $(PWD)/common
AUTH_API_DIR = $(PWD)/auth_api
PAYMENT_API_DIR = $(PWD)/billing/payment_api
GUI_DIR = $(PWD)/gui
AUTH_API__ALEMBIC_DIR = $(PWD)/auth_api/src/alembic_async
AUTH_API__ALEMBIC_CONFIG = $(PWD)/auth_api/src/alembic_async/alembic.ini

DEV_ENV_FILE = $(PWD)/.dev.env
PROD_ENV_FILE = $(PWD)/.example.env
TEST_ENV_FILE = $(PWD)/.dev.env

WAIT_REDIS = PYTHONPATH=$(PWD) uv run --env-file ${DEV_ENV_FILE} python3 common/src/theatre/core/waiters/wait_for_redis.py
WAIT_PG = PYTHONPATH=$(PWD) uv run --env-file ${DEV_ENV_FILE} python3 common/src/theatre/core/waiters/wait_for_db.py

#
# General tasks
#
.PHONY: prepare-dev-env
prepare-dev-env:
	deactivate || true
	python3 -m ensurepip
	./install-uv.sh
	uv venv --python 3.13
	make compile_requirements
	make venv

.PHONY: compile_requirements
compile_requirements:
	uv pip compile pyproject.toml -o requirements.txt
	cd $(COMMON_DIR) && uv pip compile pyproject.toml -o requirements.txt
	cd ${AUTH_API_DIR} && uv pip compile pyproject.toml -o requirements.txt
	cd ${AUTH_API__ALEMBIC_DIR} && uv pip compile pyproject.toml -o requirements.txt
	cd ${PAYMENT_API_DIR} && uv pip compile pyproject.toml -o requirements.txt
	cd ${GUI_DIR} && uv pip compile pyproject.toml -o requirements.txt

.PHONY: venv
venv:
	uv sync --all-packages --all-groups

#
# Base containers: db, redis. To build elastic add profile: require__elastic
#
.PHONY: run_basedev_containers
run_basedev_containers:
	ENV_FILE=${DEV_ENV_FILE} docker compose -f docker-compose.yml -f docker-compose/compose.dev.yml \
		--profile require__redis \
		up --build -d
	$(WAIT_PG) && $(WAIT_REDIS)

.PHONY: list_basedev_containers
list_basedev_containers:
	ENV_FILE=${DEV_ENV_FILE} docker compose -f docker-compose.yml -f docker-compose/compose.dev.yml
		--profile require__redis \
		ps -a

.PHONY: down_basedev_containers
down_basedev_containers:
	ENV_FILE=${DEV_ENV_FILE} docker compose -f docker-compose.yml -f docker-compose/compose.dev.yml \
		--profile require__redis \
		down -v

#
# Build service base images
#
.PHONY: build_all-threatre-base_containers
build_all-threatre-base_containers:
	ENV_FILE=${PROD_ENV_FILE} docker compose -f docker-compose.yml \
		--profile require__theatre_common \
		--profile require__auth_api_alembic_async_base \
		--profile require__auth_api_base \
		--profile require__payment_api_alembic_async_base \
		--profile require__payment_api_base \
		--profile require__gui_base \
		build

.PHONY: build_threatre-common_container
build_threatre-common_container:
	ENV_FILE=${PROD_ENV_FILE} docker compose -f docker-compose.yml \
		--profile require__theatre_common \
		build

.PHONY: build_auth-api-base_container
build_auth-api-base_container:
	ENV_FILE=${PROD_ENV_FILE} docker compose -f docker-compose.yml \
	 	--profile require__theatre_common \
		--profile require__auth_api_alembic_async_base \
		--profile require__auth_api_base \
		build

.PHONY: build_payment-api-base_container
build_payment-api-base_container:
	ENV_FILE=${PROD_ENV_FILE} docker compose -f docker-compose.yml \
	 	--profile require__theatre_common \
		--profile require__payment_api_alembic_async_base \
		--profile require__payment_api_base \
		build

.PHONY: build_gui-base_container
build_gui-base_container:
	ENV_FILE=${PROD_ENV_FILE} docker compose -f docker-compose.yml \
	 	--profile require__theatre_common \
		--profile require__gui_base \
		build

#
# Build service base images: section end
#

#
# Auth API: Alembic
#
.PHONY: auth_api__alembic_init
auth_api__alembic_init:
	alembic --config ${AUTH_API__ALEMBIC_CONFIG} init auth_api/src/alembic

.PHONY: build_auth-api-alembic_containers
build_auth-api-alembic_containers:
	ENV_FILE=${PROD_ENV_FILE} docker compose -f docker-compose.yml -f docker-compose/compose.dev.yml \
		--profile require__auth_api_alembic build --no-cache

.PHONY: run_auth-api-alembic_containers
run_auth-api-alembic_containers:
	make down_auth-api-alembic_containers
	ENV_FILE=${PROD_ENV_FILE} docker compose -f docker-compose.yml -f docker-compose/compose.dev.yml \
		--profile require__auth_api_alembic \
		up --build -d

.PHONY: down_auth-api-alembic_containers
down_auth-api-alembic_containers:
	ENV_FILE=${PROD_ENV_FILE} docker compose -f docker-compose.yml -f docker-compose/compose.dev.yml \
		--profile require__auth_api_alembic down
	rm -f auth_api/src/alembic_async/versions/*.py

#
# Auth API: app
#
.PHONY: build_auth-api_docker
build_auth-api_docker:
	ENV_FILE=${PROD_ENV_FILE} docker compose --profile require__auth_service \
		--profile require__auth_api_alembic --profile require__redis \
		-f docker-compose.yml build


.PHONY: run_auth-api_docker
run_auth-api_docker:
	ENV_FILE=${PROD_ENV_FILE} docker compose --profile require__auth_service \
		--profile require__auth_api_alembic --profile require__redis \
		-f docker-compose.yml -f docker-compose/compose.dev.yml up --build -d

.PHONY: down_auth-api_docker
down_auth-api_docker:
	ENV_FILE=${PROD_ENV_FILE} docker compose --profile require__auth_service \
		--profile require__redis --profile require__auth_api_alembic \
		-f docker-compose.yml -f docker-compose/compose.dev.yml down -v

#
# Auth API (app,tests): For debugging
#
.PHONY: run_auth-api-containers_for_debug
run_auth-api-containers_for_debug:
	make run_basedev_containers
	ENV_FILE=${DEV_ENV_FILE} $(PWD)/auth_api/src/alembic_async/entry-point.sh

.PHONY: down_auth-api-containers_for_debug
down_auth-api-containers_for_debug:
	make down_basedev_containers
	rm -f $(PWD)/auth_api/src/alembic_async/versions/*.py

#
# Auth API: end
#

#
# Billing
#
include billing.mk