
.PHONY: test clean

test:
	docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from app-test

lint:
	docker-compose -f docker-compose.test.yml run --rm app-test sh -c "uv run ruff check . && uv run ruff format --check ."

format:
	docker-compose -f docker-compose.test.yml run --rm app-test uv run ruff format .

clean:
	docker-compose -f docker-compose.test.yml down -v
