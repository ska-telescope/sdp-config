.PHONY: help release-patch release-minor release-major

help: ## Show this help
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' ./Makefile | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-30s\033[0m %s\n", $$1, $$2}'

release-patch: ## Patch release; -n --> do not synchronize tags from git
	bumpver update --patch -n

release-minor: ## Minor release; -n --> do not synchronize tags from git
	bumpver update --minor -n

release-major: ## Major release; -n --> do not synchronize tags from git
	bumpver update --major -n
