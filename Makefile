PY ?= .venv/bin/python

.PHONY: mock all app app-stable test readme ingest appendix
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

ingest:
	$(PY) -m beqaa.ingest all

app-stable:
	scripts/run_stable.sh

appendix:
	$(PY) -m beqaa.ingest all
	$(PY) -m beqaa.pipeline
	$(PY) scripts/make_figures.py
	$(PY) scripts/make_appendix_notebook.py
