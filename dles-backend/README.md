# DLES Backend

FastAPI service for the data-lake table enhancement system. See the [root README](../README.md) for the overall setup.

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                 # then fill in your secrets
mysql -u root -p < database/schema.sql
python main.py                                       # http://127.0.0.1:8080, API docs at /docs
```

## Layout

| Directory | Purpose |
| --- | --- |
| `login/`, `settings/` | Registration, login, password recovery, avatar |
| `enhance/` | Table enhancement: history tree, query engine, LLM calls |
| `train/` | Code generation and enhancement-effect comparison |
| `embedding/`, `transformer/` | Table embedding (Jina) and the contrastive Transformer |
| `database/`, `utils/`, `logs/` | MySQL access, auth / mail / config helpers, logging |

## Configuration

- Secrets are read from environment variables (or `dles-backend/.env`); see `.env.example`.
- Non-secret settings (paths, model locations, token lifetime) are in the `config.json` files next to each module.
