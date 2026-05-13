.PHONY: install quality test check api dashboard generate

install:
	python -m pip install -r requirements-dev.txt

quality:
	ruff check .
	black --check .
	python -m compileall -q app

test:
	python -m pytest

check: quality test

api:
	uvicorn app.api.main:app --reload

dashboard:
	streamlit run app/dashboard.py

generate:
	python -m app.generate_data
