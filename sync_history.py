import requests
import json
from fastapi import FastAPI, Request
import socket
from typing import Any
import time
import os
import uvicorn
import threading
import asyncio
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded



# if i have under 5 messages saved locally i look for peers who can provide me with more
download_trashold : int = 10
contact_refill = 360 # refill in 6 minutes

# {key_name : time_of_last_contact}
contacted_keys : dict = {}

history_path = "/Users/janzimula/dht2.0/node/chat/messages.json"


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]

def get_public_ip() -> str:
    try:
        response = requests.get("https://api.ipify.org?format=json")
        ip = response.json()["ip"]
        return ip
    except requests.RequestException as e:
        print(f"Error fetching public IP: {e}")
        return "Error"


def read_history() -> None | dict[str, Any]:
    try:
        with open(history_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print (e)
        return None
    
def write_history(history):
    with open(history_path, "w") as f:
        json.dump(history, f, indent=4)


def get_history(ip: str, port: int, timeout: int = 10) -> None | dict[str, Any]:
    url = f"http://{ip}:{port}/history"
    try:
        response = requests.get(url, timeout=timeout)
        contacted_keys[f"{ip}:{port}"] = time.time()
        if response.status_code == 200:
            return response.json()
    except (requests.ConnectionError, requests.Timeout):
        pass
    return None

app = FastAPI()
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# max 5 requests per minute
@app.get("/history")
@limiter.limit("5/minute")
def __get_history__(request: Request):
    print ("someone is asking for history")
    history = read_history()
    if history is not None:
        return history
    return {"message": "History not found"}



def start_history_api(ip, port):
    print(f"Service running on http://{ip}:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)


ip = "127.0.0.1" 
port = find_free_port()

def should_contact_peer(ip_p: str, port_p: int) -> bool:
    print("checking if should contact peer")
    now = time.time()

    if ip_p == ip and port_p == port:
        return False

    client = f"{ip_p}:{port_p}"

    if client in contacted_keys:
        time_diff = now - contacted_keys[client]
        return time_diff > contact_refill

    return True


async def async_main():
    sleep = 5
    while True:
        # print (f"sleeping for {sleep}")
        time.sleep(sleep)
        print ("running main")
        history = read_history()
        if history is not None and history:
            print (2)
            history_len = len(history)
            if history_len < download_trashold:
                print("trying to download larger history pack")
                try:
                    for message in history:
                        print ("loop running here")
                        ip_peer = message["ip"]
                        port_peer = message["port"]
                      
                        if should_contact_peer(ip_peer, port_peer):
                                new_history = get_history(ip_peer, port_peer)   
                                print (f"new history {new_history}")

                except Exception as e:
                    print("error in history", e)
                    continue
                if new_history is not None and new_history:
                    if len(new_history) > history_len:
                        print("new history downloaded")
                        write_history(new_history)
    
    
async def start_go_app(ip, port):
    print (f"starting on ip {ip} and port {port}")
    print ("starting go app")
     # Start the Go application as a background task
    await asyncio.create_subprocess_exec(
        "go", "run", ".", f"-ip={ip}", f"-port={port}"
    )




def main() -> None:
    # ip = "127.0.0.1"                         #get_public_ip()
    # Start the Go application in a separate thread
    threading.Thread(target=lambda: asyncio.run(start_go_app(ip, port)), daemon=True).start()
    # Wait for the Go application to start
    time.sleep(60)
    # Run FastAPI server in a separate thread
    threading.Thread(target=lambda: start_history_api(ip, port),  daemon=True ).start()
    # Run the main loop asynchronously in a separate thread
    threading.Thread(target=lambda: asyncio.run(async_main()), daemon=True).start()

    # Keep the main thread alive
    while True:
        time.sleep(3600)

    #os.system(f"go run . -ip={ip} -port={port}")
if __name__ == "__main__":
    main()