SHELL := /bin/bash
ROOT_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
BIN_DIR := $(ROOT_DIR)bin
SERVER_URL ?= http://127.0.0.1:8787
export AGENT_CLI_DEMO_HOME ?= $(ROOT_DIR).demo-data

.PHONY: help build test clean demo run-server

help:
	@printf "Targets:\n"
	@printf "  make build      Build mp-sso-cli and mp-admin-cli\n"
	@printf "  make test       Run Node and Go tests\n"
	@printf "  make run-server Start the mock server on $(SERVER_URL)\n"
	@printf "  make demo       Build and run the full login loop\n"
	@printf "  make clean      Remove generated data and binaries\n"

build:
	@mkdir -p "$(BIN_DIR)"
	cd "$(ROOT_DIR)cli" && go build -o ../bin/mp-sso-cli ./cmd/mp-sso-cli
	cd "$(ROOT_DIR)cli" && go build -o ../bin/mp-admin-cli ./cmd/mp-admin-cli

test:
	cd "$(ROOT_DIR)server" && pnpm test
	cd "$(ROOT_DIR)cli" && go test ./...

run-server:
	cd "$(ROOT_DIR)server" && PORT=$${PORT:-8787} pnpm start

demo: build
	cd "$(ROOT_DIR)" && SERVER_URL="$(SERVER_URL)" bash scripts/run-demo.sh

clean:
	rm -rf "$(ROOT_DIR).demo-data" "$(BIN_DIR)"
