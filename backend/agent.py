import json
import threading
import uuid
from typing import Annotated, Any, TypedDict

from flask import Flask
from flask_sock import Sock
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import tools_condition

from factory import LLMFactory


app = Flask(__name__)
sock = Sock(app)

_tool_context = threading.local()


class BrowserSession:
    def __init__(self, ws):
        self.ws = ws
        self.closed = False
        self._send_lock = threading.Lock()
        self._condition = threading.Condition()
        self._pending_results: dict[str, Any] = {}

    def send_json(self, payload: dict[str, Any]) -> None:
        if self.closed:
            return
        with self._send_lock:
            self.ws.send(json.dumps(payload))

    def request_action(self, command: dict[str, Any], timeout: int = 60) -> Any:
        action_id = str(uuid.uuid4())
        self.send_json({
            "type": "action",
            "id": action_id,
            "command": command,
        })

        with self._condition:
            if not self._condition.wait_for(
                lambda: action_id in self._pending_results or self.closed,
                timeout=timeout,
            ):
                raise TimeoutError(f"Timed out waiting for browser action: {command.get('action')}")

            if self.closed:
                raise RuntimeError("Browser session closed before the action completed.")

            result = self._pending_results.pop(action_id)

        if isinstance(result, dict) and result.get("status") == "error":
            raise RuntimeError(result.get("message") or result.get("error") or "Browser action failed.")

        return result

    def store_action_result(self, action_id: str | None, result: Any) -> None:
        if not action_id:
            return
        with self._condition:
            self._pending_results[action_id] = result
            self._condition.notify_all()

    def close(self) -> None:
        self.closed = True
        with self._condition:
            self._condition.notify_all()


def current_browser_session() -> BrowserSession:
    session = getattr(_tool_context, "session", None)
    if session is None:
        raise RuntimeError("No Chrome extension session is attached to this tool call.")
    return session


def format_tab_result(tab: dict[str, Any]) -> str:
    title = tab.get("title") or "Untitled"
    url = tab.get("url") or "unknown URL"
    text = tab.get("text") or ""
    status = tab.get("status") or "success"
    if status != "success":
        return f"TITLE: {title}\nURL: {url}\nERROR: {tab.get('message') or tab.get('error') or status}"
    return f"TITLE: {title}\nURL: {url}\nCONTENT:\n{text}"


@tool
def read_current_tab(purpose: str = "answer the user's question") -> str:
    """
    Read visible text, title, and URL from the user's active Chrome tab.
    Use this for questions about the current page, summaries, forms, products, articles, or page-specific research.
    """
    result = current_browser_session().request_action({
        "action": "extract_current_tab",
        "purpose": purpose,
        "maxChars": 20000,
    })
    return format_tab_result(result)


@tool
def read_open_tabs(purpose: str = "answer the user's question") -> str:
    """
    Read visible text, titles, and URLs from open tabs in the current Chrome window.
    Use this when the user asks to compare, summarize, filter, or analyze multiple open tabs.
    """
    result = current_browser_session().request_action({
        "action": "extract_all_tabs",
        "purpose": purpose,
        "maxCharsPerTab": 12000,
        "maxTabs": 12,
    }, timeout=120)
    tabs = result.get("tabs", []) if isinstance(result, dict) else []
    if not tabs:
        return "No readable open tabs were returned by the Chrome extension."
    return "\n\n--- TAB ---\n\n".join(format_tab_result(tab) for tab in tabs)


@tool
def scroll_current_tab(direction: str = "down") -> str:
    """
    Scroll the user's active Chrome tab. Use this when more page content needs to be loaded before reading or acting.
    Direction should be one of: down, up, top, bottom.
    """
    result = current_browser_session().request_action({
        "action": "scroll_current_tab",
        "direction": direction,
    })
    return json.dumps(result)


@tool
def browser_search(query: str) -> str:
    """
    Open a browser search for the query in Chrome and return readable text from the search results page.
    Use this when the user asks for new web information rather than only content from already-open tabs.
    """
    result = current_browser_session().request_action({
        "action": "search_web",
        "query": query,
        "maxChars": 18000,
    }, timeout=90)
    return format_tab_result(result)


@tool
def open_url(url: str) -> str:
    """
    Open a URL in Chrome for the user. Use this when the user explicitly asks to navigate to a page or site.
    """
    result = current_browser_session().request_action({
        "action": "open_url",
        "url": url,
    })
    return json.dumps(result)


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


TOOLS = [read_current_tab, read_open_tabs, scroll_current_tab, browser_search, open_url]
TOOLS_BY_NAME = {tool_.name: tool_ for tool_ in TOOLS}

llm = LLMFactory.build().bind_tools(TOOLS)

SYSTEM_PROMPT = """You are a browser assistant connected to a Chrome extension side panel.
Use the provided browser tools whenever the user asks about the active page, open tabs, web search, scrolling, or navigation.
The backend cannot access Chrome directly; it must request browser actions through the side panel extension.
After tool results are available, answer the user's request directly and concisely.
"""


def assistant(state: State) -> dict[str, list[BaseMessage]]:
    return {"messages": [llm.invoke(state["messages"])]}


def run_tools(state: State) -> dict[str, list[BaseMessage]]:
    last_message = state["messages"][-1]
    tool_messages: list[ToolMessage] = []

    for tool_call in getattr(last_message, "tool_calls", []):
        tool_name = tool_call.get("name")
        tool_id = tool_call.get("id")
        args = tool_call.get("args") or {}
        selected_tool = TOOLS_BY_NAME.get(tool_name)

        if selected_tool is None:
            content = f"Unknown tool requested: {tool_name}"
        else:
            try:
                content = selected_tool.invoke(args)
            except Exception as exc:
                content = f"Tool {tool_name} failed: {exc}"

        tool_messages.append(ToolMessage(content=str(content), tool_call_id=tool_id))

    return {"messages": tool_messages}


builder = StateGraph(State)
builder.add_node("assistant", assistant)
builder.add_node("tools", run_tools)
builder.add_edge(START, "assistant")
builder.add_conditional_edges("assistant", tools_condition)
builder.add_edge("tools", "assistant")
graph = builder.compile()


def extract_message_text(message: AIMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or ""))
            else:
                parts.append(str(item))
        return "".join(parts).strip()
    return str(content)


def run_agent_prompt(session: BrowserSession, user_text: str) -> None:
    _tool_context.session = session
    try:
        session.send_json({"type": "status", "content": "Thinking..."})

        inputs = {
            "messages": [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=user_text),
            ]
        }
        final_response = "I couldn't produce a response."

        for event in graph.stream(inputs, stream_mode="values"):
            last_message = event["messages"][-1]
            if isinstance(last_message, AIMessage) and not last_message.tool_calls:
                text = extract_message_text(last_message)
                if text:
                    final_response = text

        session.send_json({"type": "chat_reply", "content": final_response})
    except Exception as exc:
        session.send_json({"type": "chat_reply", "content": f"Agent error: {exc}"})
    finally:
        _tool_context.session = None


@sock.route("/ws")
def agent_socket(ws):
    session = BrowserSession(ws)
    workers: list[threading.Thread] = []

    try:
        while True:
            raw_data = ws.receive()
            if raw_data is None:
                break

            try:
                message = json.loads(raw_data)
            except json.JSONDecodeError:
                session.send_json({"type": "chat_reply", "content": "Invalid JSON message received."})
                continue

            message_type = message.get("type")

            if message_type == "user_prompt":
                user_text = str(message.get("content") or "").strip()
                if not user_text:
                    session.send_json({"type": "chat_reply", "content": "Please enter a prompt."})
                    continue

                worker = threading.Thread(
                    target=run_agent_prompt,
                    args=(session, user_text),
                    daemon=True,
                )
                workers.append(worker)
                worker.start()

            elif message_type == "action_result":
                session.store_action_result(message.get("id"), message.get("content"))

            else:
                session.send_json({"type": "chat_reply", "content": f"Unknown message type: {message_type}"})
    finally:
        session.close()
        for worker in workers:
            worker.join(timeout=0.2)


@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    print("--- Chrome Extension Agent Server Starting on port 5080 ---")
    app.run(host="127.0.0.1", port=5080, threaded=True)
