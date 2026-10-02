# DLES Backend

FastAPI service for the data-lake table enhancement system. See the [root README](../README.md) for the overall setup.

Setup, data preparation, training and running are described in the [root README](../README.md#quick-start).

## Layout

| Directory | Purpose |
| --- | --- |
| `login/`, `settings/` | Registration, login, password recovery, avatar |
| `enhance/` | Table enhancement: history tree, query engine, LLM calls |
| `train/` | Code generation and enhancement-effect comparison |
| `embedding/`, `transformer/` | Table embedding (Qwen3-Embedding) and the contrastive column-context Transformer (training, evaluation) |
| `scripts/` | `create_user`, `smoke_test` |
| `database/`, `utils/`, `logs/` | MySQL access, auth / mail / config helpers, logging |

## Configuration

- Secrets are read from environment variables (or `dles-backend/.env`); see `.env.example`.
- Non-secret settings (paths, model locations, token lifetime) are in the `config.json` files next to each module.
