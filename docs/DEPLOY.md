# Deploying the dashboard (Streamlit Community Cloud, public link)

1. Push `main` to GitHub (already public). Go to <https://share.streamlit.io>, sign in with GitHub, **Create app**.
2. Repository `shjangada/lebanon-hhc-policy`, branch `main`, main file `app/streamlit_app.py`. In **Advanced settings** choose Python 3.12 or 3.13 (the repo is developed on 3.14; the deps are standard wheels).
3. **Secrets** (Advanced settings → Secrets), TOML. Top-level keys are exposed as environment variables, which is how `chat_llm.py` reads them:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   CHAT_MAX_LLM_QUESTIONS = "10"   # per browser session; after this the chat falls back to retrieval-only
   ```
   Set a monthly spend limit on that key in the Anthropic console first: the link is public.
4. Deploy. The app reads the committed real `data/processed/*.csv` and `data/registry/*`; model outputs are recomputed at start (first load is slow, then cached).

Not on the host (by design): raw third-party PDFs (restore locally with `python scripts/fetch_sources.py --restore-pdfs`; the HAUS 2024 PDF has no recorded URL and stays local), `.env`, ACLED data (its terms forbid redistribution), and pipeline outputs `m*_*.csv` (recomputed).
Mock inputs that remain are labelled in the app (badges, watermark, per-page warning) and listed in `docs/MOCK_VS_REAL.md`.

## Retrying ACLED (local only)
The last token request returned HTTP 403: the account was refused, usually because API access is not enabled for that myACLED tier.
1. Sign in at <https://acleddata.com> and check the account's API access / access tier; request API access if it is off.
2. Put `ACLED_EMAIL=` and `ACLED_PASSWORD=` in `.env` (gitignored).
3. `python -m beqaa.ingest acled`. Output goes to gitignored paths; do not commit or deploy it, and keep the ACLED attribution in any figure that uses it.
