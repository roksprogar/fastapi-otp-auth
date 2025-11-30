
.PHONY: test clean

test:
	docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from app-test

lint:
	docker-compose -f docker-compose.test.yml run --rm app-test uv run ruff check .

clean:
	docker-compose -f docker-compose.test.yml down -v
