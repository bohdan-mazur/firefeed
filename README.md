# FireFeed

> **Demo on synthetic data. All calls, places and people are fictional.**

FireFeed turns fire department radio traffic into structured incidents: audio or a transcript goes in, and out come typed records (fire or not, incident type, street, units, status) grouped into incidents.

The demo runs on 53 invented calls from Larkmoor County, a county that does not exist. See [`data/README.md`](data/README.md) for the dataset, the labeling rules and the name check.

## Pipeline

```
calls/ (.txt or audio + .json)
  → transcribe   speech-to-text; skipped when a transcript exists
  → analyze      OpenAI Responses API, strict JSON schema, every answer validated
  → cluster      related calls grouped into incidents
  → export       feed.json for the site
  → notify       Telegram or webhook; off in the demo
```

Answers are cached by a hash of the model, settings, prompt, schema and input, so a repeated run makes no API requests. Before a run the pipeline counts cache misses and estimates their cost; it refuses to start above the request limit and asks for `--yes` above the cost threshold in `firefeed.toml`.

## Quick start

Python 3.12.

```bash
python -m venv .venv
.venv/Scripts/activate            # Windows; on macOS or Linux: source .venv/bin/activate
pip install -e ".[dev]" -c constraints.txt
pytest
ruff check .
```

Run the demo dataset. The committed cache answers every call, so this needs no API key and makes no requests:

```bash
firefeed run --dry-run     # what would need the API, and an estimate of its cost
firefeed run               # writes data/demo/out/feed.json
firefeed evaluate          # compares with data/spec.csv, writes data/demo/out/evaluation.json
```

## Your own calls

Put one transcript (`.txt`) or audio file (`.wav`, `.mp3`, `.m4a`, `.ogg`, `.flac`, `.webm`) per call into a folder, each with a JSON file of the same name:

```json
{ "timestamp": "2026-10-17T13:04:12-05:00", "channel": "Dispatch" }
```

Copy `.env.example` to `.env` and set `OPENAI_API_KEY`, then:

```bash
firefeed run --input path/to/calls --out out --cache .cache --dry-run
firefeed run --input path/to/calls --out out --cache .cache
```

A street and unit list (`gazetteer.json`, see `data/gazetteer.json`) is optional; with it, misheard street names are matched to the right street.

## Site

`site/` is the demo website: a static Next.js export that reads `data/demo/out/feed.json`, `data/demo/out/evaluation.json` and `data/map.json` at build time. No backend, no API keys. Node 24.

```bash
cd site
npm ci
npm run build          # writes site/out/
npm run check:links    # every internal link resolves; the synthetic-data notice is on every page
```

## License

MIT, see [LICENSE](LICENSE).
