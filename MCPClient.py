from flask import Flask, request, jsonify, render_template_string
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

app = Flask(__name__)

async def ask_mcp_server(question: str) -> str:
    """Connects to the local MCP server, asks the question, and returns the response."""
    
    # 1. Define the parameters to start the MCP server subprocess
    # Note: Ensure "server.py" exactly matches the name of your MCP server script
    server_params = StdioServerParameters(
        command="python",
        args=["MCPServer.py"] 
    )
    
    # 2. Connect to the server via standard input/output (stdio)
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            
            # 3. Initialize the MCP protocol handshake
            await session.initialize()
            
            # 4. Call the tool defined in your server
            result = await session.call_tool("answer_from_notes", arguments={"question": question})
            
            # 5. Extract the text block from the response
            return result.content[0].text

@app.route("/")
def index():
    # A simple, single-page UI for the chat interface embedded directly in the app
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>MCP Notes Assistant</title>
        <style>
            body { font-family: system-ui, -apple-system, sans-serif; max-width: 700px; margin: 2rem auto; padding: 0 1rem; background: #f9fafb; color: #111827; }
            h2 { text-align: center; color: #374151; }
            #chatbox { height: 60vh; background: white; border: 1px solid #e5e7eb; border-radius: 8px; overflow-y: auto; padding: 1.5rem; margin-bottom: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
            .msg { margin-bottom: 1rem; line-height: 1.5; }
            .user { color: #2563eb; }
            .bot { color: #059669; white-space: pre-wrap; }
            .error { color: #dc2626; }
            #input-container { display: flex; gap: 0.5rem; }
            #input-container input { flex-grow: 1; padding: 0.75rem; border: 1px solid #d1d5db; border-radius: 6px; font-size: 1rem; }
            #input-container button { padding: 0.75rem 1.5rem; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 1rem; transition: background 0.2s; }
            #input-container button:hover { background: #1d4ed8; }
        </style>
    </head>
    <body>
        <h2>🧠 My Notes AI</h2>
        <div id="chatbox"></div>
        <div id="input-container">
            <input type="text" id="prompt" placeholder="Ask a question about your notes..." onkeypress="if(event.key === 'Enter') send()">
            <button onclick="send()">Send</button>
        </div>

        <script>
            async function send() {
                const input = document.getElementById('prompt');
                const chatbox = document.getElementById('chatbox');
                const text = input.value.trim();
                if(!text) return;

                // Add user message to UI
                chatbox.innerHTML += `<div class="msg user"><b>You:</b> ${text}</div>`;
                input.value = '';
                
                // Add loading state
                const loadingId = 'loading-' + Date.now();
                chatbox.innerHTML += `<div class="msg bot" id="${loadingId}"><b>AI:</b> <i>Scouring notes...</i></div>`;
                chatbox.scrollTop = chatbox.scrollHeight;

                try {
                    const response = await fetch('/chat', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({message: text})
                    });
                    const data = await response.json();
                    
                    document.getElementById(loadingId).remove();
                    
                    if(data.error) {
                        chatbox.innerHTML += `<div class="msg error"><b>System Error:</b> ${data.error}</div>`;
                    } else {
                        chatbox.innerHTML += `<div class="msg bot"><b>AI:</b> ${data.response}</div>`;
                    }
                } catch(err) {
                    document.getElementById(loadingId).remove();
                    chatbox.innerHTML += `<div class="msg error"><b>Network Error:</b> Failed to reach the Flask backend.</div>`;
                }
                chatbox.scrollTop = chatbox.scrollHeight;
            }
        </script>
    </body>
    </html>
    """)

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message")
    if not user_message:
        return jsonify({"error": "No message provided"}), 400
        
    try:
        # Run the async MCP client loop inside the synchronous Flask route
        response_text = asyncio.run(ask_mcp_server(user_message))
        return jsonify({"response": response_text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Start the Flask development server
    app.run(debug=True, port=5000)