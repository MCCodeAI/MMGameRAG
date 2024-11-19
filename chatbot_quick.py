import streamlit as st
import time
import random
from datetime import datetime
import threading
import asyncio
import websockets
import socket



from mmgamerag import *
from mmgamer_quicksearch import *

prompt = ""

# WebSocket works fine, but to refresh ui doesn't work, might because of mechanism of Streamlit...

# ============================
# WebSocket Server Setup
# ============================

# WebSocket server configuration
WS_HOST = "localhost"
WS_PORT = 8765  # Default port

# Global flag to track server initialization
# This flag ensures the server starts only once across all sessions
if 'ws_server_started' not in st.session_state:
    st.session_state['ws_server_started'] = False

def is_port_in_use(host: str, port: int) -> bool:
    """
    Check if a specific port is in use on the given host.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0

# Asynchronous function to handle incoming client connections
async def handle_client(websocket, path):
    # Notify when a new client connects
    print(f"Client connected from {websocket.remote_address}")
    try:
        # Continuously listen for messages from the client
        async for message in websocket:
            # Print the received message
            print(f"Received message from client: {message}")
            global prompt
            prompt = message
            print("asdf:"+ prompt)

            # Send a response back to the client
            await websocket.send(f"Server received your message: {message}")
    except websockets.exceptions.ConnectionClosed as e:
        # Handle client disconnection
        print(f"Client disconnected: {e}")

# Function to start the WebSocket server
def start_websocket_server(host: str, port: int):

    # Create a new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Start the WebSocket server
    start_server = websockets.serve(handle_client, host, port)
    server = loop.run_until_complete(start_server)
    print(f"WebSocket server started on ws://{host}:{port}")
    
    # Run the event loop forever
    loop.run_forever()


# Function to initialize the WebSocket server in a separate thread
def init_websocket_server():
    if not st.session_state['ws_server_started']:
        # Check if the desired port is already in use
        # if is_port_in_use(WS_HOST, WS_PORT):
        #     st.error(f"Port {WS_PORT} is already in use. Please choose a different port.")
        #     return
        
        st.session_state['ws_server_started'] = True
        server_thread = threading.Thread(target=start_websocket_server, args=(WS_HOST, WS_PORT), daemon=True)
        server_thread.start()
        print("WebSocket server thread started.")

# Initialize the WebSocket server
init_websocket_server()


# ============================
# Streamlit App Starts Here
# ============================



# Left side for the chat interface
with st.sidebar:
    # Input for OpenAI API key and links for additional resources
    openai_api_key = st.text_input("OpenAI API Key", key="chatbot_api_key", type="password")
    st.markdown("[Get an OpenAI API key](https://platform.openai.com/account/api-keys)")
    st.markdown("[View the source code](https://github.com/MCCodeAI/MMGameRAG)")
    st.markdown("[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/streamlit/llm-examples?quickstart=1)")
    
    # Divider line and button to clear chat history
    st.markdown("---")
    if st.button("Clear Chat"):
        # Clear chat session state if it exists
        if 'messages' in st.session_state:
            del st.session_state['messages']
        st.success("Chat cleared!")


# Title and description of the application
st.title("Quick MMGameRAG")
st.caption("Quick Multimodal Retrieval-Augmented Generation System for Game Walkthroughs")
st.caption("一个图文并茂的多模态游戏攻略高手，帮助用户快速检索和了解《黑神话悟空》🐵🍌")

# Initialize chat messages in session state
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        ("assistant", "How can I help you for Black Myth quickly?")
    ]

# Display chat messages
for role, content in st.session_state["messages"]:
    if role == "assistant":
        st.chat_message(role).markdown(content, unsafe_allow_html=True)
    else:
        st.chat_message(role).write(content, unsafe_allow_html=True)



def chatbotprocess(prompt0):
    print(f"User input: {prompt0}")


    # Add user input to the chat history
    st.session_state["messages"].append(("user", prompt0))
    st.chat_message("user").write(prompt0, unsafe_allow_html=True)

    # Placeholder for the animated search feedback
    placeholder = st.empty()
    gif_index = random.randint(0, 0)
    gif_path = f"monkeying{gif_index}.gif"
    placeholder.image(f"uidata/{gif_path}", caption="攻略快速搜索中...")

    # Record start time for search
    start_time = datetime.now()

    # Execute quick search with multimodal capabilities
    response = llm_chatbot_quick(prompt0, st.session_state["messages"])

    # Record end time and calculate execution time
    end_time = datetime.now()
    execution_time = (end_time - start_time).total_seconds()
    print(f"Time: {end_time}, llm Execution time: {execution_time} seconds")

    # Process and display the response
    msg = response
    msg_base64 = msg_imgurl_to_base64_quick(msg)
    st.chat_message("assistant").write(msg_base64, unsafe_allow_html=True)

    # Clear placeholder
    placeholder.empty()
    # Add assistant's response to chat history
    st.session_state["messages"].append(("assistant", msg_base64))



# # Capture user input
# if prompt != "":
#     chatbotprocess()

if prompt1 := st.chat_input("Type your question here..."):
    chatbotprocess(prompt1)

import streamlit.components.v1 as components

# 嵌入 HTML 和 JavaScript 以监听父页面的消息
html_code = """
<!DOCTYPE html>
<html lang="en">
<head>
    <script>
        // 监听来自父页面的消息
        console.log("start it");
        window.addEventListener("message", function(event) {
            console.log("got it");
            // 确保消息来源安全
            if (event.origin === "http://127.0.0.1:5500") {
                document.getElementById("data-display").innerText = "Received data: " + event.data;
                console.log("Received data from siframe in chatbot:", event.data);
            }
        });
    </script>
</head>
<body>
    <h3>数据接收区</h3>
    <div id="data-display">等待接收数据...</div>
</body>
</html>
"""

# 在 Streamlit 中嵌入 HTML
components.html(html_code, height=200)