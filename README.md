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
python -m uvicorn app.main:app --host 0.0.0.0 --port 3000
```

Then fetch `http://localhost:3000/api/dictionary/en/hello` or open `/` for the UI.

## 📖 Example
`/api/dictionary/en-cn/cook`

```json
{
  "word": "cook",
  "pos": ["verb", "noun"],
  "verbs": [
    {"id":0,"type":"Plain form","text":"cook"},
    {"id":1,"type":"Third-person singular","text":"cooks"},
    {"id":2,"type":"Past tense","text":"cooked"},
    {"id":3,"type":"Past participle","text":"cooked"},
    {"id":4,"type":"Present participle","text":"cooking"},
    {"id":5,"type":"Singular","text":"cook"},
    {"id":6,"type":"Plural","text":"cooks"}
  ],
  "pronunciation": [
    {"pos":"verb","lang":"uk","url":"https://dictionary.cambridge.org/us/media/english-chinese-simplified/uk_pron/...mp3","pron":"/kʊk/"},
    {"pos":"verb","lang":"us","url":"https://dictionary.cambridge.org/us/media/english-chinese-simplified/us_pron/...mp3","pron":"/kʊk/"}
  ],
  "definition": [
    {
      "id": 0,
      "pos": "verb",
      "source": "cald4-us",
      "text": "When you cook food, you prepare it to be eaten...",
      "translation": "做饭，烹调；烧，煮",
      "level": "A2",
      "example": [
        {"id":0, "text":"I don't cook meat very often.", "translation":"我不常煮肉吃。"}
      ]
    },
    {
      "id": 1,
      "pos": "noun",
      "source": "cald4-us",
      "text": "someone who prepares and cooks food",
      "translation": "厨师",
      "level": "A2",
      "example": [{"id":0, "text":"She's a wonderful cook.", "translation":"她是位很出色的厨师。"}]
    }
  ]
}
```

## API Source
- Verbs from Wiktionary (Simple English)
- Other data from Cambridge Dictionary

## Develop ❤️
- Built with FastAPI, Requests, BeautifulSoup
- In-memory TTL/LRU cache for performance
- Contributions are welcome!
