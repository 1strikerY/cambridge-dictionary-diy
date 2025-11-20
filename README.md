# Cambridge Dictionary (Python)

A simple API for Cambridge Dictionary, built with FastAPI.

## 🕹️ Manual

### 📚 dictionary
`/api/dictionary/{language}/{word}`

- language option:
  - `en` — English (US)
  - `uk` — English (UK)
  - `en-cn` — English–Chinese (Simplified)
  - `en-tw` — English–Chinese (Traditional)

Open `/` to use the built-in Web UI.

### Response fields
- `word`: headword
- `pos`: list of parts of speech
- `pronunciation`: list with `pos`, `lang`, `url` (audio), `pron` (IPA)
- `definition`: list per sense, with `id`, `pos`, `source`, `text`, `translation`, `level` (CEFR A1–C2), `example[]`
- `verbs`: verb forms from Simple Wiktionary

### Error codes
- `400` Unsupported language
- `404` Word not found
- `500` Internal server error

## 🌐 Deploy
- Works as a standard Python web app (FastAPI + Uvicorn).
- Can be deployed to platforms supporting long-running processes (Render, Railway, etc.). Vercel serverless requires adapter; run locally is recommended.

## 💻 Running Locally
After cloning, run the following in the project folder:

```bash
# create & activate venv
python3 -m venv .venv
. .venv/bin/activate

# install dependencies
pip install -r requirements.txt

# run
./.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 3000
```

Then fetch `http://localhost:3000` or open `/` for the UI.

## 📖 Example
![alt text](image.png)

## API Source
- Verbs from Wiktionary (Simple English)
- Other data from Cambridge Dictionary

## Develop ❤️
- Built with FastAPI, Requests, BeautifulSoup
- In-memory TTL/LRU cache for performance
- Contributions are welcome!
