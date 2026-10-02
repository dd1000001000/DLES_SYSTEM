# DLES — Data Lake Table Enhancement System

My undergraduate thesis project: a system that enhances a user's table with relevant data found in a data lake.

- **Backend**: FastAPI (`dles-backend/`)
- **Frontend**: Vue 3 + TypeScript + Vite (`dles-frontend/DLES/`)
- **Design and algorithms**: see the thesis in this repository
  - [English translation](<yuming ding undergraduate thesis.pdf>) (translated by GPT6.1 Sol)
  - [中文原文](<丁郁明 毕业论文 终稿.pdf>)

`real_data_lake_benchmark_query_tables.csv` lists the query tables of the SANTOS real data lake benchmark (not used by the scripts below, which use TUS small).

## Repository layout

```
dles-backend/      FastAPI service (login, settings, table enhancement, model training)
dles-frontend/DLES Vue 3 web client
```

## Quick start

### 1. Prerequisites

- Python 3.10, Node.js 18+, Docker (or any MySQL 8)
- An NVIDIA GPU is strongly recommended (CPU works but is slow). RTX 50-series cards need the CUDA 12.8 build of PyTorch
- An OpenAI-compatible model service (OpenAI, DashScope, DeepSeek, a local Ollama, ...). Each user enters the endpoint, API key and model names in the web UI under Settings → 模型配置; table enhancement and AI code generation use them

### 2. Backend environment

```bash
cd dles-backend
python -m venv .venv
.venv/Scripts/activate                    # Windows; Linux/macOS: source .venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cu128    # pick the build for your GPU
pip install -r requirements.txt
cp .env.example .env                      # then fill in the secrets (see the table below)

# MySQL (any MySQL 8 works; this is a throwaway local one)
docker run -d --name dles-mysql -e MYSQL_ROOT_PASSWORD=<DLES_DB_PASSWORD from .env> \
  -e MYSQL_DATABASE=dles_system -p 127.0.0.1:3306:3306 mysql:8
docker exec -i dles-mysql mysql -uroot -p<password> < database/schema.sql
```

### 3. Data lake, models and vectors

Large files are not in the repository. By default they live next to `dles-backend/` (the project root); set `DLES_DATA_DIR` to put them elsewhere, or edit the relative paths in the `config.json` files.

| What | Where from | Goes to |
| --- | --- | --- |
| Data lake: TUS small, 1,526 CSV tables (the "Santos small" lake of the thesis) | [`tus.tar.gz`](https://zenodo.org/records/15499092) (Zenodo, CC-BY-4.0, 441 MB). Extract it to `_downloads/tus/`, then move `_downloads/tus/tus/datalake` to `datalake/`. `query/` and `benchmark.pkl` stay in `_downloads/tus/tus/` for evaluation | `datalake/` |
| Embedding model [`Qwen/Qwen3-Embedding-0.6B`](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B) (1024-d) | Hugging Face | `models/Qwen/Qwen3-Embedding-0.6B/` |
| [`google-bert/bert-base-uncased`](https://huggingface.co/google-bert/bert-base-uncased) (fills missing text values) | Hugging Face | `models/google-bert/bert-base-uncased/` |

```bash
# from dles-backend/, with the venv active
python -m embedding.table_embedding --reset            # embed every table, register it in table_base_info (~5 min on a GPU)
python -m transformer.train --benchmark-dir ../_downloads/tus/tus   # train the column-context Transformer (~15 min incl. augmentation)
python -m transformer.transformer                       # run the Transformer over all tables, update table_base_info
python -m transformer.evaluate --benchmark-dir ../_downloads/tus/tus    # P@k / R@k on the TUS queries
```

The embedding model replaces the thesis' Jina v2: it is stronger, needs no remote code, and has 1024 dimensions, so the Transformer has to be retrained whenever the embedding model changes. `transformer/models/full_trained_model.pth` is a plain state dict (loaded with `weights_only=True`), not a pickled model.

### 4. Run

On Windows, once steps 1–3 are done, double-click `start.bat` (or run `.\start.ps1`): it starts the `dles-mysql` container, the backend (`:8080`) and the frontend (`:5173`), waits until each answers, and opens the browser. `stop.bat` stops the backend and frontend (`stop.ps1 -Db` also stops MySQL). Create a user once with `scripts.create_user` (below). To start things by hand:

```bash
python -m scripts.create_user you@example.com           # creates a user without the e-mail verification code
python main.py                                          # API on http://localhost:8080, docs at /docs

cd ../dles-frontend/DLES
npm install
npm run dev                                             # http://localhost:5173
```

Log in, open Settings → 模型配置 and enter your model endpoint. Registration through the UI needs `DLES_MAIL_SENDER` / `DLES_MAIL_TOKEN` (SMTP) to send the verification code; without them use `scripts.create_user`. `python -m scripts.smoke_test <model> <csv>` runs login → upload → enhance through the HTTP API.

For a local Ollama, set `DLES_ALLOW_PRIVATE_LLM_ENDPOINTS=1`, use `http://localhost:11434/v1` as the endpoint, and start Ollama with `OLLAMA_CONTEXT_LENGTH=16384` — the enhancement prompt contains samples of 9 tables and is far longer than Ollama's default context.

## Configuration

Secrets are read from environment variables (`dles-backend/.env`):

| Variable | Purpose |
| --- | --- |
| `DLES_DB_PASSWORD` | MySQL password |
| `DLES_JWT_SECRET_KEY` | JWT signing key |
| `DLES_MAIL_SENDER`, `DLES_MAIL_TOKEN` | Optional. SMTP account for verification mails |
| `DLES_ENCRYPTION_KEY` | Optional Fernet key for encrypting users' saved model API keys (derived from `DLES_JWT_SECRET_KEY` if empty) |
| `DLES_ALLOW_PRIVATE_LLM_ENDPOINTS` | `1` allows model endpoints on localhost/private addresses (Ollama, vLLM). Keep `0` on a shared server to prevent SSRF |
| `DLES_COOKIE_SECURE` | Set to `1` when serving over HTTPS (login cookie is `Secure`) |
| `DLES_DATA_DIR` | Optional. Where `datalake/`, `models/` and the vector folders live (default: project root) |

Login uses an `httpOnly`, `SameSite=Lax` cookie, so the frontend and the API must be on the same site (same hostname, ports may differ). The frontend uses the current page's hostname by default; override with `VITE_API_BASE_URL`. Changing the password invalidates all previously issued tokens, and failed logins are rate limited (in memory, per process).

Non-secret settings are in the `config.json` files next to each module: `database/` (MySQL user, database name, optional `host`/`port`), `utils/authorization/` (token lifetime), and `embedding/`, `transformer/`, `enhance/enhance_main/service/` (data lake, model and vector paths, relative to the data directory).

## Related-table discovery results

Follows the thesis pipeline (TF-IDF column truncation → embedding → contrastive column-context Transformer → Sinkhorn table similarity → graph search), evaluated on the 125 TUS small query tables (ground truth: tables cut from the same base table, ~180 per query). Queries are split in half by position: the first half was used to pick hyper-parameters, the table below is the held-out half (62 queries).

| | P@1 | P@5 | P@10 | P@20 | P@50 |
| --- | --- | --- | --- | --- | --- |
| Qwen3 embeddings, no Transformer | 1.000 | 1.000 | 0.990 | 0.989 | 0.977 |
| + trained Transformer | 1.000 | 0.994 | 0.992 | 0.994 | 0.994 |

TUS small is close to saturated for a modern embedding model, so the gain is mostly at larger k. Differences from the thesis' training recipe, all in `transformer/train.py` and `transformer/similarity_torch.py`:

- **False-negative cancellation**: with plain NT-Xent every other table in the batch is a negative, but this lake is 1,526 tables cut from only ~10 base tables, so most "negatives" are really related. Training for 100 epochs that way pushed related tables apart (P@50 over all 125 queries fell from 0.973 to 0.687). Negatives that are already similar to the anchor in the raw embedding space (≥ 0.5 × the positive pair's similarity) are now excluded from the loss, which needs no labels.
- Random column dropout and a warm-up + cosine learning-rate schedule; a residual connection around the Transformer; a differentiable version of the Sinkhorn matching similarity as the contrastive similarity.
- The thesis' WWk (Wikipedia tables) datasets have no public source and were not reproduced.

## License

[MIT](LICENSE)
