.PHONY: test python-test java-test demo docker-up docker-down

test: python-test java-test

python-test:
	cd agent-orchestrator && python -m pytest

java-test:
	cd shortener-service && mvn test

demo:
	cd agent-orchestrator && python scripts/demo.py

docker-up:
	docker compose up --build

docker-down:
	docker compose down
