TARGET_GROUP ?= $(shell id -gn)
TEST_HOME ?= $(HOME)
TEST_SOCKET ?= /run/ydotoold-$(TARGET_GROUP)/socket

.PHONY: build test test-sandbox
build:
	bash packaging/build.sh package
test:
	bash packaging/build.sh test
test-sandbox:
	python3 tests/sandbox_test.py --group "$(TARGET_GROUP)" --home "$(TEST_HOME)" --socket "$(TEST_SOCKET)"
