"""Converters from raw downloads (data/raw/<source folders>) to the project's dataset schemas (data/derived/<dataset>.csv).

Run all converters whose inputs are present:  python -m beqaa.ingest
Derived files are used instead of mock files only when BEQAA_DATA=derived (see beqaa.io); every derived row carries provenance."""
