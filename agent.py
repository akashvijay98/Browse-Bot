import os
import time
from typing import Annotated, TypedDict
from playwright.sync_api import sync_playwright
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, BaseMessage, AIMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition


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
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
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
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
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
    summary, headlines, or specific highlights. 
    Use this for news, articles, or general research.
    """
    results = []
    output_file = "web_summary_output.txt"
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
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

# --- LANGGRAPH SETUP ---
class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

tools = [sweep_open_tabs_and_filter]


llm = ChatOllama(
    model="qwen3.5:9b", 
    temperature=0,
    format="json",            # Excellent for parsing web data into state
    num_ctx=32768,            # Qwen 3.5 supports huge context; 32k is safe for local VRAM
    base_url="http://localhost:11434"
).bind_tools(tools)

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

# --- RUNNING THE AGENT ---
if __name__ == "__main__":
    print("--- Gemini Job Hunter Active ---")
    print("1. Close all Chrome windows.")
    print("2. Run: chrome.exe --remote-debugging-port=9222")
    print("3. Open your job tabs, then type your request below.")
    
    while True:
        user_prompt = input("\nUser: ")
        if user_prompt.lower() in ["exit", "quit"]: 
            break
            
        inputs = {"messages": [HumanMessage(content=user_prompt)]}
        
        # We use stream_mode="values" to track the full message history
        for event in graph.stream(inputs, stream_mode="values"):
            last_message = event["messages"][-1]
            
            # The Fix: Only print if it's an AIMessage and it has finished its tool calls
            if isinstance(last_message, AIMessage) and not last_message.tool_calls:
                if last_message.content:
                    if isinstance(last_message.content, list):
                        # Extract text from content blocks if it's a list
                        text_to_save = "".join([
                            block.get("text", "") if isinstance(block, dict) else str(block) 
                            for block in last_message.content
                        ])
                    else:
                        text_to_save = last_message.content

                    print(f"\nAgent: {text_to_save}")

                    with open(llm_output_file, "a", encoding="utf-8") as f:
                        f.write(f"\n--- AGENT SUMMARY ---\n")
                        f.write(text_to_save)
                        f.write(f"\n{'-'*50}\n")