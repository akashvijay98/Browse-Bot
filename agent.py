import os
import time
from typing import Annotated, TypedDict
from playwright.sync_api import sync_playwright

from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI

from langchain_core.messages import HumanMessage, BaseMessage, AIMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
import threading
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import json
from factory import LLMFactory
import config

app = Flask(__name__)
TWILIO_NUMBER = config.TWILIO_NUMBER
client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)

def get_browser_instance(p):
    """
    Tries to connect to your manual Chrome first.
    If it's not running, it launches a temporary one.
    """
    try:
        return p.chromium.connect_over_cdp("http://localhost:9222")
    except Exception:
        # This will open a window you can see
        return p.chromium.launch(headless=False)

@tool
def sweep_open_tabs_and_filter(criteria: str):
    """
    Accesses live Chrome, scrolls through pages to load hidden content,
    and extracts text to find jobs matching criteria.
    """
    results = []
    output_file = "job_hunt_output.txt"
    try:
        with sync_playwright() as p:
            # Note: Chrome must be running with --remote-debugging-port=9222
            browser = get_browser_instance(p)
            context = browser.contexts[0]
            pages = context.pages

            if not pages:
                return "I couldn't find any open tabs. Check port 9222."

            with open(output_file, "a", encoding="utf-8") as f:
                f.write(f"\n--- SESSION START: {time.ctime()} ---\n")
                
                for page in pages:
                    try:
                        page.bring_to_front()
                        print(f"Scanning: {page.url[:50]}...")

                        # --- FULL PAGE SCROLL LOGIC ---
                        last_height = page.evaluate("document.body.scrollHeight")
                        while True:
                            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                            time.sleep(1.5)
                            new_height = page.evaluate("document.body.scrollHeight")
                            if new_height == last_height:
                                break
                            last_height = new_height

                        # Extract text
                        content = page.inner_text("body")
                        entry = f"SOURCE: {page.url}\nCONTENT:\n{content}\n{'-'*30}\n"
                        
                        # --- THE CRITICAL PART: PERSISTENCE ---
                        f.write(entry)
                        f.flush()  # Forces write to disk immediately
                        
                        results.append(entry)
                    except Exception as e:
                        print(f"Skipping page due to error: {e}")
                        continue

            return "\n".join(results) if results else "No content could be read."
    except Exception as e:
        return f"Error: {str(e)}. Ensure Chrome is closed and restarted with --remote-debugging-port=9222"

@tool
def read_and_analyze_tabs(purpose: str = "product recommendation"):
    """
    Reads the content of all open Chrome tabs to analyze products, read their details and reviews, and provide recommendations or
    the return the products details. Do as the user asks. Use this for shopping, product research, or comparison. compare prices of products
    and return the best deal. If the user asks for a specific product, find it in the open tabs and return its details and reviews.

    """
    results = []
    output_file = "product_reccomendation_output.txt"
    
    try:
        with sync_playwright() as p:
            browser = get_browser_instance(p)
            pages = browser.contexts[0].pages
            if not pages:
                return "No open tabs found to read."

            with open(output_file, "a", encoding="utf-8") as f:
                f.write(f"\n--- WEB READ SESSION: {time.ctime()} ---\n")
                
                for page in pages:
                    try:
                        page.bring_to_front()
                        # Simple wait for content instead of heavy scrolling
                        page.wait_for_load_state("domcontentloaded")
                        
                        title = page.title()
                        # Get text but limit it to avoid crashing the LLM
                        content = page.inner_text("body")[:8000] 
                        
                        entry = f"URL: {page.url}\nTITLE: {title}\nCONTENT:\n{content}\n{'-'*30}\n"
                        
                        f.write(entry)
                        f.flush()
                        results.append(entry)
                    except Exception:
                        continue

            return "\n".join(results) if results else "Could not extract text from tabs."
    except Exception as e:
        return f"Error connecting to Chrome: {str(e)}"

@tool
def read_and_summarize_tabs(purpose: str = "general summary"):
    """
    Reads the content of all open Chrome tabs to provide a general 
    summary, headlines, important points, specific highlights or answer a question asked on the content of the tabs.  
    Use this for news, articles, blogs or general research from the open tab.
    perform the task as the user prompts. 

    """
    results = []
    output_file = "web_summary_output.txt"
    
    try:
        with sync_playwright() as p:
            browser = get_browser_instance(p)
            pages = browser.contexts[0].pages
            if not pages:
                return "No open tabs found to read."

            with open(output_file, "a", encoding="utf-8") as f:
                f.write(f"\n--- WEB READ SESSION: {time.ctime()} ---\n")
                
                for page in pages:
                    try:
                        page.bring_to_front()
                        # Simple wait for content instead of heavy scrolling
                        page.wait_for_load_state("domcontentloaded")
                        
                        title = page.title()
                        # Get text but limit it to avoid crashing the LLM
                        content = page.inner_text("body")[:8000] 
                        
                        entry = f"URL: {page.url}\nTITLE: {title}\nCONTENT:\n{content}\n{'-'*30}\n"
                        
                        f.write(entry)
                        f.flush()
                        results.append(entry)
                    except Exception:
                        continue

            return "\n".join(results) if results else "Could not extract text from tabs."
    except Exception as e:
        return f"Error connecting to Chrome: {str(e)}"


@tool
def browser_search(query: str):
    """
    Performs a google/duckduckgo search using the live Chrome instance and returns results.
    """
    results = []
    try:
        with sync_playwright() as p:
            browser = get_browser_instance(p)
            page = browser.contexts[0].new_page()
            
            # Navigate to Google
            page.goto(f"https://duckduckgo.com/?q={query}")
            page.wait_for_selector('article[data-testid="result"]', timeout=10000)
            
            # DuckDuckGo result items are usually within 'article' tags with this testid
            items = page.query_selector_all('article[data-testid="result"]')
            
            for item in items[:5]:  # Top 5 results
                # DuckDuckGo titles are inside headings with a specific link class
                title_el = item.query_selector('h2 a')
                if title_el:
                    title = title_el.inner_text()
                    link = title_el.get_attribute('href')
                    results.append(f"Title: {title}\nURL: {link}")
            page.close()
            return "\n\n".join(results) if results else "No results found."
    except Exception as e:
        return f"Search Error: {str(e)}"

class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

tools = [sweep_open_tabs_and_filter, read_and_analyze_tabs, read_and_summarize_tabs, browser_search]


llm = LLMFactory.build().bind_tools(tools)

def assistant(state: State):
    return {"messages": [llm.invoke(state["messages"])]}

builder = StateGraph(State)
builder.add_node("assistant", assistant)
builder.add_node("tools", ToolNode(tools))
builder.add_edge(START, "assistant")
builder.add_conditional_edges("assistant", tools_condition)
builder.add_edge("tools", "assistant")
graph = builder.compile()

llm_output_file = "llm_output.txt"




def process_agent_task(user_msg, user_phone):
    """
    Runs the LangGraph agent in a separate thread to avoid WhatsApp timeouts.
    """
    try:
        inputs = {"messages": [HumanMessage(content=user_msg)]}
        final_response = "Sorry, I couldn't find anything."

        for event in graph.stream(inputs, stream_mode="values"):
            last_message = event["messages"][-1]
           
            if isinstance(last_message, AIMessage) and not last_message.tool_calls:
                content = last_message.content
                
                # If content is a string, try to parse it as JSON
                if isinstance(content, str):
                    try:
                        data = json.loads(content)
                        # Extract the most likely key containing the answer
                        # This assumes your LLM puts the answer in a key like 'text', 'answer', or 'summary'
                        final_response = data.get("answer") or data.get("summary") or data.get("text") or str(data)
                    except json.JSONDecodeError:
                        final_response = content
                elif isinstance(content, list):
                    final_response = "".join([b.get("text", "") for b in content if isinstance(b, dict)])

        # Send the final result back to the user
        client.messages.create(
            body=final_response[:1500], # WhatsApp limit is ~1600 chars
            from_=TWILIO_NUMBER,
            to=user_phone
        )
    except Exception as e:
        client.messages.create(
            body=f"Error: {str(e)}",
            from_=TWILIO_NUMBER,
            to=user_phone
        )
    try:
        with open("llm_output.txt", "a", encoding="utf-8") as f:
            f.write(f"Timestamp: {time.ctime()}\n")
            f.write(f"User: {user_phone}\n")
            f.write(f"Response: {final_response}\n")
            f.write(f"{'-'*30}\n")
    except Exception as log_err:
        print(f"Failed to write to file: {log_err}")
        
@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    """
    Webhook that Twilio calls when a message arrives.
    """
    incoming_msg = request.values.get('Body', '')
    user_phone = request.values.get('From', '')

    # 1. Start the agent in the background
    thread = threading.Thread(target=process_agent_task, args=(incoming_msg, user_phone))
    thread.start()

    # 2. Respond immediately so Twilio doesn't time out
    resp = MessagingResponse()
    resp.message("Scanned request received. Checking your open Chrome tabs now... 🔍")
    return str(resp)

if __name__ == "__main__":
    print("--- WhatsApp Agent Server Starting ---")
    print("Ensure Chrome is running with: --remote-debugging-port=9222")
    # Run Flask on port 5000
    app.run(port=5080)










