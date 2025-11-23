/**
 * Remotable Function - Web Client Demo Application Logic
 */

let client = null;
const SERVER_URL = 'ws://localhost:8765';

// Initialize when page loads
window.addEventListener('DOMContentLoaded', async () => {
    console.log('Initializing Remotable Web Client Demo...');
    await initializeClient();
});

/**
 * Initialize the Remotable client
 */
async function initializeClient() {
    try {
        // Create client instance
        client = new RemotableClient(SERVER_URL);

        // Display client ID
        document.getElementById('client-id').textContent = client.clientId;

        // Register browser tools that Python can call
        registerBrowserTools();

        // Setup event handlers
        setupEventHandlers();

        // Connect to server
        await client.connect();

    } catch (error) {
        console.error('Failed to initialize client:', error);
        updateConnectionStatus(false);
        addLog('error', `Connection failed: ${error.message}`);
    }
}

/**
 * Register browser-specific tools
 */
function registerBrowserTools() {
    // Tool: Show notification
    client.registerTool('browser', 'show_notification', async (args) => {
        const { title, message, type = 'info' } = args;

        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <strong>${title}</strong><br>
            ${message}
        `;

        document.body.appendChild(notification);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            notification.remove();
        }, 5000);

        addLog('success', `Notification shown: ${title}`);

        return {
            success: true,
            message: 'Notification displayed'
        };
    }, 'Show browser notification');

    // Tool: Update DOM element
    client.registerTool('browser', 'update_dom', async (args) => {
        const { selector, content } = args;

        const element = document.querySelector(selector);
        if (!element) {
            throw new Error(`Element not found: ${selector}`);
        }

        element.textContent = content;

        addLog('success', `DOM updated: ${selector}`);

        return {
            success: true,
            selector: selector,
            updated: true
        };
    }, 'Update DOM element content');

    // Tool: Get browser information
    client.registerTool('browser', 'get_info', async (args) => {
        const info = {
            userAgent: navigator.userAgent,
            language: navigator.language,
            platform: navigator.platform,
            cookiesEnabled: navigator.cookieEnabled,
            onLine: navigator.onLine,
            screen: {
                width: screen.width,
                height: screen.height,
                colorDepth: screen.colorDepth
            },
            viewport: {
                width: window.innerWidth,
                height: window.innerHeight
            }
        };

        addLog('info', 'Browser info requested by server');

        return info;
    }, 'Get browser information');

    console.log('Browser tools registered:', client.getTools());
}

/**
 * Setup event handlers
 */
function setupEventHandlers() {
    client.on('connected', () => {
        updateConnectionStatus(true);
        addLog('success', 'Connected to Python Gateway');
    });

    client.on('disconnected', () => {
        updateConnectionStatus(false);
        addLog('warning', 'Disconnected from server');
    });

    client.on('error', (error) => {
        addLog('error', `WebSocket error: ${error}`);
    });

    client.on('log', (logEntry) => {
        // Client's internal logs are already shown in console
        // We can optionally display them in the UI too
    });

    client.on('reconnect_failed', () => {
        addLog('error', 'Reconnection failed - max attempts reached');
    });
}

/**
 * Update connection status display
 */
function updateConnectionStatus(connected) {
    const statusEl = document.getElementById('connection-status');
    if (connected) {
        statusEl.textContent = 'Connected';
        statusEl.className = 'status connected';
    } else {
        statusEl.textContent = 'Disconnected';
        statusEl.className = 'status disconnected';
    }
}

/**
 * Add log entry to the log container
 */
function addLog(level, message) {
    const logContainer = document.getElementById('log-container');
    const timestamp = new Date().toLocaleTimeString();

    const logEntry = document.createElement('div');
    logEntry.className = `log-entry log-${level}`;
    logEntry.innerHTML = `
        <span class="log-time">${timestamp}</span>
        <span class="log-level">${level.toUpperCase()}</span>
        <span class="log-message">${message}</span>
    `;

    logContainer.appendChild(logEntry);

    // Auto-scroll to bottom
    logContainer.scrollTop = logContainer.scrollHeight;

    // Keep only last 100 entries
    while (logContainer.children.length > 100) {
        logContainer.removeChild(logContainer.firstChild);
    }
}

/**
 * Clear log
 */
function clearLog() {
    document.getElementById('log-container').innerHTML = '';
}

/**
 * Call Python tool: get_time
 */
async function callGetTime() {
    const format = document.getElementById('time-format').value;
    const resultEl = document.getElementById('time-result');

    try {
        addLog('info', `Calling demo.get_time with format: ${format}`);

        const result = await client.callTool('demo.get_time', { format: format });

        resultEl.innerHTML = `
            <div class="result-success">
                <strong>Time:</strong> ${JSON.stringify(result.time, null, 2)}<br>
                <strong>Timestamp:</strong> ${result.timestamp}<br>
                <strong>Timezone:</strong> ${result.timezone}
            </div>
        `;

        addLog('success', 'demo.get_time succeeded');

    } catch (error) {
        resultEl.innerHTML = `<div class="result-error">Error: ${error.message}</div>`;
        addLog('error', `demo.get_time failed: ${error.message}`);
    }
}

/**
 * Call Python tool: calculate
 */
async function callCalculate() {
    const expression = document.getElementById('calc-expression').value;
    const resultEl = document.getElementById('calc-result');

    try {
        addLog('info', `Calling demo.calculate with expression: ${expression}`);

        const result = await client.callTool('demo.calculate', { expression: expression });

        if (result.error) {
            resultEl.innerHTML = `<div class="result-error">Error: ${result.error}</div>`;
            addLog('error', `Calculation error: ${result.error}`);
        } else {
            resultEl.innerHTML = `
                <div class="result-success">
                    <strong>Expression:</strong> ${result.expression}<br>
                    <strong>Result:</strong> ${result.result}<br>
                    <strong>Type:</strong> ${result.type}
                </div>
            `;
            addLog('success', `Calculation result: ${result.result}`);
        }

    } catch (error) {
        resultEl.innerHTML = `<div class="result-error">Error: ${error.message}</div>`;
        addLog('error', `demo.calculate failed: ${error.message}`);
    }
}

/**
 * Call Python tool: echo
 */
async function callEcho() {
    const message = document.getElementById('echo-message').value;
    const uppercase = document.getElementById('echo-uppercase').checked;
    const resultEl = document.getElementById('echo-result');

    try {
        addLog('info', `Calling demo.echo with message: "${message}"`);

        const result = await client.callTool('demo.echo', {
            message: message,
            uppercase: uppercase
        });

        resultEl.innerHTML = `
            <div class="result-success">
                <strong>Original:</strong> ${result.original}<br>
                <strong>Echoed:</strong> ${result.echoed}<br>
                <strong>Length:</strong> ${result.length}<br>
                <strong>Uppercase Applied:</strong> ${result.uppercase_applied}
            </div>
        `;

        addLog('success', 'demo.echo succeeded');

    } catch (error) {
        resultEl.innerHTML = `<div class="result-error">Error: ${error.message}</div>`;
        addLog('error', `demo.echo failed: ${error.message}`);
    }
}
