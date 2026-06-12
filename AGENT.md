# Agent Instructions

## Project Overview

Browse Bot is a Chrome extension paired with a local Flask backend. The extension opens a side panel chat UI and forwards browser actions to the backend over a WebSocket. The backend runs a LangGraph/LangChain agent that can request tab reads, scrolling, web search, and URL navigation through the extension.

## Layout

- `backend/agent.py` - Flask app, WebSocket route, browser-action session bridge, LangGraph agent, and tool definitions.
- `backend/config.py` - Active LLM provider and model configuration.
- `backend/factory.py` - LLM factory for Gemini and Ollama.
- `frontend/manifest.json` - Chrome Manifest V3 extension configuration.
- `frontend/sidepanel.html` - Side panel markup and styles.
- `frontend/sidepanel.js` - WebSocket client and browser action dispatcher.
- `frontend/content.js` - Content script for text extraction and scrolling.
- `README.md` - User-facing setup and run instructions.

## Runtime Setup

Use Python 3.9 or newer. Install dependencies with:

```bash
pip install flask flask-sock python-dotenv langchain-core langgraph langchain-google-genai langchain-ollama
```

Run the backend from the project root:

```bash
python backend/agent.py
```

The backend listens on:

- `ws://localhost:5080/ws`
- `http://127.0.0.1:5080/health`

Load the Chrome extension by opening `chrome://extensions`, enabling Developer mode, and loading the `frontend/` directory as an unpacked extension.

## Configuration Notes

- `backend/config.py` controls `ACTIVE_PROVIDER`.
- Supported providers in the current factory are `gemini` and `ollama`.
- `backend/config.py` currently loads environment variables from `backend/.env`, not the repository root.
- Gemini requires `GOOGLE_API_KEY`.
- Ollama expects a local server at `http://localhost:11434` and the configured model to be available locally.

## Browser Action Contract

Backend tools in `backend/agent.py` send WebSocket messages shaped like:

```json
{
  "type": "action",
  "id": "uuid",
  "command": {
    "action": "extract_current_tab"
  }
}
```

The side panel responds with:

```json
{
  "type": "action_result",
  "id": "same uuid",
  "content": {}
}
```

Supported browser actions are implemented in `frontend/sidepanel.js`:

- `extract_current_tab`
- `extract_all_tabs`
- `scroll_current_tab`
- `search_web`
- `open_url`

Content-script actions are implemented in `frontend/content.js`:

- `extract_text`
- `scroll`

When adding a new browser capability, update the backend tool, `handleBrowserAction` in `frontend/sidepanel.js`, and the content script if page DOM access is required.

## Development Guidance

- Keep backend/browser boundaries explicit. The backend cannot read Chrome directly; it must request actions through the side panel WebSocket.
- Preserve the request/response `id` correlation when changing WebSocket behavior.
- Browser actions should return structured objects with a `status` field and useful `title`, `url`, `text`, or `message` fields where applicable.
- Avoid blocking the WebSocket thread for long browser operations. If adding slow work, use timeouts and status messages like the existing tools.
- Prefer small, direct tools over broad tools with ambiguous behavior.
- Keep prompt changes in `backend/agent.py` explicit and easy to review.
- Do not commit secrets. Use `.env` for provider keys and local tokens.

## Known Gotchas

- `deep_scroll_current_tab` calls `time.sleep(...)`, but `backend/agent.py` does not currently import `time`.
- `README.md` says the backend reads `.env` from the project root, while `backend/config.py` loads `backend/.env`.
- `ACTIVE_PROVIDER = "openai"` is mentioned in a comment, but the current `LLMFactory` does not implement OpenAI.
- Chrome cannot read restricted pages such as `chrome://`, extension pages, `edge://`, `about:`, or DevTools pages.

## Verification

For backend changes, at minimum run:

```bash
python -m py_compile backend/*.py
```

For extension changes, reload the unpacked extension in Chrome, start the backend, open the side panel, and verify:

- The side panel connects to `ws://localhost:5080/ws`.
- A simple prompt returns a `chat_reply`.
- Current-tab extraction works on a normal web page.
- Search or URL-opening behavior still creates a tab and returns readable text/status.
