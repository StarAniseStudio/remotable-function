/**
 * Remotable Function - JavaScript WebSocket Client
 *
 * A lightweight JavaScript client that implements the Remotable protocol
 * to communicate with Python Gateway over WebSocket.
 */

class RemotableClient {
    constructor(serverUrl, clientId = null) {
        this.serverUrl = serverUrl;
        this.clientId = clientId || `web-client-${this.generateId()}`;
        this.ws = null;
        this.connected = false;
        this.tools = new Map();
        this.pendingRequests = new Map();
        this.eventHandlers = new Map();
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000;
    }

    /**
     * Register a tool that can be called by the server
     */
    registerTool(namespace, name, handler, description = "") {
        const fullName = `${namespace}.${name}`;
        this.tools.set(fullName, {
            name: fullName,
            handler: handler,
            description: description
        });
        this.log(`Registered tool: ${fullName}`);
    }

    /**
     * Connect to the Gateway
     */
    async connect() {
        return new Promise((resolve, reject) => {
            this.log(`Connecting to ${this.serverUrl}...`);

            try {
                this.ws = new WebSocket(this.serverUrl);

                this.ws.onopen = () => {
                    this.log("WebSocket connected");
                    this.connected = true;
                    this.reconnectAttempts = 0;
                    this.sendRegisterMessage();
                    this.emit('connected');
                    resolve();
                };

                this.ws.onmessage = (event) => {
                    this.handleMessage(event.data);
                };

                this.ws.onerror = (error) => {
                    this.log(`WebSocket error: ${error}`, 'error');
                    this.emit('error', error);
                    reject(error);
                };

                this.ws.onclose = () => {
                    this.log("WebSocket closed");
                    this.connected = false;
                    this.emit('disconnected');
                    this.attemptReconnect();
                };

            } catch (error) {
                this.log(`Failed to connect: ${error}`, 'error');
                reject(error);
            }
        });
    }

    /**
     * Disconnect from the Gateway
     */
    disconnect() {
        if (this.ws) {
            this.log("Disconnecting...");
            this.ws.close();
            this.ws = null;
            this.connected = false;
        }
    }

    /**
     * Attempt to reconnect
     */
    async attemptReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            this.log(`Max reconnection attempts (${this.maxReconnectAttempts}) reached`, 'error');
            this.emit('reconnect_failed');
            return;
        }

        this.reconnectAttempts++;
        this.log(`Reconnecting in ${this.reconnectDelay / 1000}s (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);

        setTimeout(() => {
            this.connect().catch(err => {
                this.log(`Reconnection failed: ${err}`, 'error');
            });
        }, this.reconnectDelay);
    }

    /**
     * Send registration message to Gateway
     */
    sendRegisterMessage() {
        const toolList = Array.from(this.tools.values()).map(tool => ({
            name: tool.name,
            description: tool.description
        }));

        const registerMsg = {
            jsonrpc: "2.0",
            method: "register",
            params: {
                client_id: this.clientId,
                tools: toolList
            }
        };

        this.send(registerMsg);
        this.log(`Registered with ${toolList.length} tools`);
    }

    /**
     * Call a tool on the server
     */
    async callTool(toolName, args = {}, timeout = 30000) {
        if (!this.connected) {
            throw new Error("Not connected to server");
        }

        const requestId = this.generateId();

        return new Promise((resolve, reject) => {
            // Setup timeout
            const timeoutId = setTimeout(() => {
                this.pendingRequests.delete(requestId);
                reject(new Error(`Tool call timeout: ${toolName}`));
            }, timeout);

            // Store pending request
            this.pendingRequests.set(requestId, {
                resolve: (result) => {
                    clearTimeout(timeoutId);
                    resolve(result);
                },
                reject: (error) => {
                    clearTimeout(timeoutId);
                    reject(error);
                }
            });

            // Send RPC request
            const request = {
                jsonrpc: "2.0",
                method: "call_tool",
                params: {
                    tool: toolName,
                    args: args
                },
                id: requestId
            };

            this.send(request);
            this.log(`Calling tool: ${toolName}`, 'info', args);
        });
    }

    /**
     * Handle incoming WebSocket message
     */
    async handleMessage(data) {
        try {
            const msg = JSON.parse(data);

            // Handle RPC Response (response to our tool call)
            if (msg.id && this.pendingRequests.has(msg.id)) {
                const pending = this.pendingRequests.get(msg.id);
                this.pendingRequests.delete(msg.id);

                if (msg.error) {
                    this.log(`Tool call error: ${msg.error.message}`, 'error');
                    pending.reject(new Error(msg.error.message));
                } else {
                    this.log(`Tool call result received`, 'info', msg.result);
                    pending.resolve(msg.result);
                }
            }
            // Handle RPC Request (server calling our tool)
            else if (msg.method) {
                await this.handleToolCall(msg);
            }
            // Handle other message types
            else {
                this.log(`Received message: ${msg}`, 'info');
            }

        } catch (error) {
            this.log(`Failed to handle message: ${error}`, 'error');
        }
    }

    /**
     * Handle tool call from server
     */
    async handleToolCall(msg) {
        const toolName = msg.params?.tool || msg.method;
        const args = msg.params?.args || msg.params || {};
        const requestId = msg.id;

        this.log(`Server calling tool: ${toolName}`, 'info', args);

        try {
            // Check if we have this tool
            if (!this.tools.has(toolName)) {
                throw new Error(`Tool not found: ${toolName}`);
            }

            // Execute tool
            const tool = this.tools.get(toolName);
            const result = await tool.handler(args);

            // Send success response
            const response = {
                jsonrpc: "2.0",
                id: requestId,
                result: result
            };

            this.send(response);
            this.log(`Tool executed successfully: ${toolName}`, 'success', result);

        } catch (error) {
            // Send error response
            const response = {
                jsonrpc: "2.0",
                id: requestId,
                error: {
                    code: -32000,
                    message: error.message || String(error)
                }
            };

            this.send(response);
            this.log(`Tool execution failed: ${toolName} - ${error}`, 'error');
        }
    }

    /**
     * Send message through WebSocket
     */
    send(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            this.log("Cannot send message: WebSocket not open", 'error');
        }
    }

    /**
     * Register event handler
     */
    on(event, handler) {
        if (!this.eventHandlers.has(event)) {
            this.eventHandlers.set(event, []);
        }
        this.eventHandlers.get(event).push(handler);
    }

    /**
     * Emit event
     */
    emit(event, ...args) {
        if (this.eventHandlers.has(event)) {
            for (const handler of this.eventHandlers.get(event)) {
                try {
                    handler(...args);
                } catch (error) {
                    this.log(`Event handler error: ${error}`, 'error');
                }
            }
        }
    }

    /**
     * Generate unique ID
     */
    generateId() {
        return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }

    /**
     * Log message
     */
    log(message, level = 'info', data = null) {
        const timestamp = new Date().toLocaleTimeString();
        const prefix = `[${timestamp}] [${level.toUpperCase()}]`;

        if (data) {
            console.log(`${prefix} ${message}`, data);
        } else {
            console.log(`${prefix} ${message}`);
        }

        // Emit log event for UI
        this.emit('log', { timestamp, level, message, data });
    }

    /**
     * Get connection status
     */
    isConnected() {
        return this.connected && this.ws && this.ws.readyState === WebSocket.OPEN;
    }

    /**
     * Get registered tools
     */
    getTools() {
        return Array.from(this.tools.keys());
    }
}

// Export for use in HTML
if (typeof window !== 'undefined') {
    window.RemotableClient = RemotableClient;
}
