import asyncio
import websockets


# Asynchronous function to handle incoming client connections
async def handle_client(websocket, path):
    # Notify when a new client connects
    print(f"Client connected from {websocket.remote_address}")
    try:
        # Continuously listen for messages from the client
        async for message in websocket:
            # Print the received message
            print(f"Received message from client: {message}")
            # Send a response back to the client
            await websocket.send(f"Server received your message: {message}")
    except websockets.exceptions.ConnectionClosed as e:
        # Handle client disconnection
        print(f"Client disconnected: {e}")

# Start the server on localhost at port 8765
start_server = websockets.serve(handle_client, "localhost", 8765)

# Get the default event loop
loop = asyncio.get_event_loop()
# Run the server until it is manually stopped
loop.run_until_complete(start_server)
print("WebSocket server started on ws://localhost:8765")
loop.run_forever()

