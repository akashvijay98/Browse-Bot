chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'extract_text') {
        const maxChars = Number(request.maxChars || 15000);
        sendResponse({
            status: 'success',
            title: document.title,
            url: window.location.href,
            text: document.body.innerText.substring(0, maxChars),
        });
        return true;
    }

    if (request.action === 'scroll') {
        const direction = request.direction || 'down';

        if (direction === 'top') {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        } else if (direction === 'bottom') {
            window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
        } else if (direction === 'up') {
            window.scrollBy({ top: -window.innerHeight * 0.8, behavior: 'smooth' });
        } else {
            window.scrollBy({ top: window.innerHeight * 0.8, behavior: 'smooth' });
        }

        setTimeout(() => {
            sendResponse({
                status: 'success',
                title: document.title,
                url: window.location.href,
                text: `Scrolled ${direction}.`,
            });
        }, 700);

        return true;
    }

    sendResponse({ status: 'error', message: `Unknown content action: ${request.action}` });
    return true;
});
