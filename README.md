Browse Bot
==========

Browse Bot is a Chrome extension plus local Flask service that lets you chat with your browser from a side panel. The backend can read the active tab, inspect open tabs, scroll pages, search the web, and open URLs.

What it does
------------

- Reads the current Chrome tab or all open tabs.
- Scrolls the active tab to load more content.
- Searches the web in a new tab and extracts readable text.
- Opens a URL in Chrome on request.
- Sends agent responses back through the extension side panel.

Requirements
------------

- Python 3.9 or newer.
- Google Chrome.
- One supported LLM provider:
  - Google Gemini, or
  - Ollama running locally.

Setup
-----

1. Create and activate a virtual environment.

2. Install the Python dependencies:

```bash
pip install flask flask-sock python-dotenv langchain-core langgraph langchain-google-genai langchain-ollama
```

3. Configure your environment in the project root `.env` file. The backend reads the same variables used in `backend/config.py`:

```env
GOOGLE_API_KEY=your_key_here
```

4. Pick the provider in `backend/config.py`:

```python
ACTIVE_PROVIDER = "gemini"
# or
ACTIVE_PROVIDER = "ollama"
```

5. If you use Ollama, make sure the model in `MODEL_CONFIGS["ollama"]` is available locally and Ollama is running on `http://localhost:11434`.

Load the extension
------------------

1. Open Chrome and go to `chrome://extensions`.
2. Turn on Developer mode.
3. Click Load unpacked.
4. Select the `frontend/` directory.

The extension defines the side panel and content script in `frontend/manifest.json`.

Run the backend
---------------

Start the Flask server from the project root:

```bash
python backend/agent.py
```

The server listens on `127.0.0.1:5080` and exposes:

- `ws://localhost:5080/ws` for the extension side panel
- `http://127.0.0.1:5080/health` for a basic health check

Use it
------

- Open the extension side panel from Chrome.
- Ask the agent to summarize the current page, compare open tabs, search the web, or open a URL.
- The backend will respond in the side panel after it finishes the browser action.

Project layout
--------------

- `backend/agent.py` - Flask app, WebSocket bridge, and LangGraph agent.
- `backend/config.py` - Provider configuration.
- `backend/factory.py` - LLM construction based on the active provider.
- `frontend/manifest.json` - Chrome extension manifest.
- `frontend/sidepanel.html` - Side panel UI.
- `frontend/sidepanel.js` - WebSocket client and browser action dispatcher.
- `frontend/content.js` - Content script that extracts text and handles scrolling.
