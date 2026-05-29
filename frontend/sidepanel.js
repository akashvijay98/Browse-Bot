const chatHistory = document.getElementById('chat-history');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');

let socket;
let reconnectTimer;

function appendMessage(text, sender) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender === 'user' ? 'user-msg' : 'agent-msg'}`;
    msgDiv.innerText = text;
    chatHistory.appendChild(msgDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

function connectSocket() {
    socket = new WebSocket('ws://localhost:5080/ws');

    socket.onopen = () => {
        sendBtn.disabled = false;
        appendMessage('Connected to local agent.', 'agent');
    };

    socket.onmessage = async (event) => {
        const response = JSON.parse(event.data);

        if (response.type === 'chat_reply') {
            appendMessage(response.content, 'agent');
            return;
        }

        if (response.type === 'status') {
            appendMessage(response.content, 'agent');
            return;
        }

        if (response.type === 'action') {
            const result = await handleBrowserAction(response.command);
            socket.send(JSON.stringify({
                type: 'action_result',
                id: response.id,
                content: result,
            }));
        }
    };

    socket.onclose = () => {
        sendBtn.disabled = true;
        clearTimeout(reconnectTimer);
        reconnectTimer = setTimeout(connectSocket, 1500);
    };

    socket.onerror = () => {
        appendMessage('Cannot reach local agent on ws://localhost:5080/ws.', 'agent');
    };
}

function sendPrompt() {
    const text = userInput.value.trim();
    if (!text || !socket || socket.readyState !== WebSocket.OPEN) return;

    appendMessage(text, 'user');
    userInput.value = '';
    socket.send(JSON.stringify({ type: 'user_prompt', content: text }));
}

sendBtn.addEventListener('click', sendPrompt);
userInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') sendPrompt();
});

async function handleBrowserAction(command) {
    try {
        switch (command.action) {
            case 'extract_current_tab':
                return await extractCurrentTab(command.maxChars);
            case 'extract_all_tabs':
                return await extractAllTabs(command.maxTabs, command.maxCharsPerTab);
            case 'scroll_current_tab':
                return await sendToActiveTab({ action: 'scroll', direction: command.direction });
            case 'search_web':
                return await searchWeb(command.query, command.maxChars);
            case 'open_url':
                return await openUrl(command.url);
            default:
                return { status: 'error', message: `Unknown browser action: ${command.action}` };
        }
    } catch (error) {
        return { status: 'error', message: error.message || String(error) };
    }
}

async function getActiveTab() {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) throw new Error('No active tab found.');
    return tab;
}

async function sendToActiveTab(message) {
    const tab = await getActiveTab();
    return await sendToTab(tab, message);
}

async function sendToTab(tab, message) {
    if (!tab.id) return { status: 'error', title: tab.title, url: tab.url, message: 'Tab has no id.' };
    if (isRestrictedUrl(tab.url)) {
        return { status: 'error', title: tab.title, url: tab.url, message: 'Chrome extensions cannot read this page.' };
    }

    try {
        return await chrome.tabs.sendMessage(tab.id, message);
    } catch (error) {
        return { status: 'error', title: tab.title, url: tab.url, message: error.message || String(error) };
    }
}

async function extractCurrentTab(maxChars) {
    return await sendToActiveTab({ action: 'extract_text', maxChars });
}

async function extractAllTabs(maxTabs = 12, maxCharsPerTab = 12000) {
    const tabs = await chrome.tabs.query({ currentWindow: true });
    const readableTabs = tabs.slice(0, maxTabs);
    const results = [];

    for (const tab of readableTabs) {
        const result = await sendToTab(tab, { action: 'extract_text', maxChars: maxCharsPerTab });
        results.push({
            title: result.title || tab.title,
            url: result.url || tab.url,
            status: result.status,
            text: result.text,
            message: result.message,
        });
    }

    return { status: 'success', tabs: results };
}

async function searchWeb(query, maxChars) {
    if (!query) return { status: 'error', message: 'Search query is required.' };

    const searchUrl = `https://duckduckgo.com/?q=${encodeURIComponent(query)}`;
    const tab = await chrome.tabs.create({ url: searchUrl, active: true });
    await waitForTabComplete(tab.id);
    await delay(700);
    return await sendToTab(tab, { action: 'extract_text', maxChars });
}

async function openUrl(url) {
    if (!url) return { status: 'error', message: 'URL is required.' };

    const normalizedUrl = /^https?:\/\//i.test(url) ? url : `https://${url}`;
    const tab = await chrome.tabs.create({ url: normalizedUrl, active: true });
    return { status: 'success', title: tab.title, url: normalizedUrl, text: `Opened ${normalizedUrl}` };
}

function waitForTabComplete(tabId) {
    return new Promise((resolve) => {
        const listener = (updatedTabId, changeInfo) => {
            if (updatedTabId === tabId && changeInfo.status === 'complete') {
                chrome.tabs.onUpdated.removeListener(listener);
                resolve();
            }
        };
        chrome.tabs.onUpdated.addListener(listener);
        setTimeout(() => {
            chrome.tabs.onUpdated.removeListener(listener);
            resolve();
        }, 10000);
    });
}

function delay(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

function isRestrictedUrl(url = '') {
    return /^(chrome|chrome-extension|edge|about|devtools):\/\//i.test(url);
}

sendBtn.disabled = true;
connectSocket();
