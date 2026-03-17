WhatsApp Web-Scanner Agent 🔍
=============================

This application turns your WhatsApp into a remote control for your Chrome browser. It uses an AI agent to scan your open browser tabs, search the web, and summarize content, sending the results directly back to your phone.

🚀 Prerequisites
----------------

### 1\. Python Environment

Ensure you have Python **3.9+** installed.

### 2\. Chrome Remote Debugging

For the agent to "see" your open tabs, Chrome must be launched in remote debugging mode.

*   **Close all instances of Chrome** completely.
    
*   Bashchrome.exe --remote-debugging-port=9222_(Note: If chrome.exe is not in your PATH, navigate to its installation folder first.)_
    

### 3\. Twilio Account

*   A **Twilio Account SID** and **Auth Token**.
    
*   A active **Twilio WhatsApp Sandbox** or a registered WhatsApp sender number.
    
*   A public URL (using **ngrok**) to expose your local server to Twilio.
    

🛠️ Installation & Setup
------------------------

### 1\. Clone and Install Dependencies

Bash

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   # Install the core libraries  pip install playwright langchain-ollama langchain-google-genai langchain-core langgraph flask twilio  # Install Playwright browser binaries (for the fallback launcher)  playwright install chromium   `

### 2\. Configuration Files

Ensure you have the following files in your project root:

**config.py**

Python

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   TWILIO_ACCOUNT_SID = "your_sid_here"  TWILIO_AUTH_TOKEN = "your_token_here"  TWILIO_NUMBER = "whatsapp:+14155238886" # Your Twilio Sandbox number   `

**factory.py**Ensure your LLMFactory is correctly configured to return a LangChain LLM (like Google Gemini or Ollama).

### 3\. Expose your Localhost

Twilio needs to send "Webhooks" to your computer. Use ngrok to create a tunnel:

Bash

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   ngrok http 5080   `

Copy the **Forwarding URL** (e.g., https://random-id.ngrok-free.app).

🏃 Running the Application
--------------------------

1.  **Start Chrome** with port 9222 (as shown in Prerequisites).
    
2.  Bashpython agent.py
    
3.  **Configure Twilio Webhook:**
    
    *   Go to the [Twilio Console](https://console.twilio.com/).
        
    *   Navigate to **Messaging > Try it Out > WhatsApp Sandbox**.
        
    *   Paste your ngrok URL followed by /whatsapp into the "When a message comes in" field:https://your-id.ngrok-free.app/whatsapp
        
4.  **Chat!**
    
    *   Send a message like _"Summarize my open job tabs"_ or _"Search for the best price for a Sony camera"_ to your WhatsApp Sandbox number.
        

📋 Features
-----------

*   **Dynamic Scraping:** Uses Playwright to scroll through pages and load lazy-loaded content.
    
*   **Persistence:** Logs all extracted web data to .txt files for auditing.
    
*   **Async Processing:** Uses Python threading to ensure Twilio gets an immediate "Received" response while the agent works in the background.
    
*   **Tool-Augmented:** The agent chooses between searching the web, analyzing specific tabs, or summarizing broad content based on your prompt.
