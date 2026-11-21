PY ?= .venv/bin/python

.PHONY: mock all app test readme
mock:
	$(PY) scripts/make_mock_data.py

all: mock
	$(PY) -m beqaa.pipeline

app:
	streamlit run app/streamlit_app.py

test: mock
	$(PY) -m pytest -q

readme:
	$(PY) -c "from beqaa.io import readme_status_table as t; print(t())"
