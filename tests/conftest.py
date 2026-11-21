import os

# Unit tests exercise the models on mock data unless a test opts in to processed (real) data explicitly.
os.environ.setdefault("BEQAA_DATA", "mock")
