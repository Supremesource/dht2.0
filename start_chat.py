import requests
import json
from fastapi import FastAPI, Request
import socket
from typing import Any
import time
import uvicorn
import threading
import asyncio
from slowapi import Limiter, _rate_limit_exceeded_handler # type: ignore
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded


# if i have under 10 messages saved locally i look for peers who can provide me with more
download_threshold: int = 10
contact_refill: int = 360  # refill in 6 minutes
# {key_name : time_of_last_contact}
contacted_keys: dict[Any, Any] = {}
# where to save the history
history_path: str = "/Users/janzimula/dht2.0/node/src/chat/messages.json"


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def get_public_ip() -> str:
    try:
        url: str = "https://api.ipify.org?format=json"
        response = requests.get(url)
        ip = response.json()["ip"]
        return ip
    except requests.RequestException as e:
        print(f"Error fetching public IP: {e}")
        return "Error"


def read_history() -> None | list[dict[str, Any]]:
    try:
        with open(history_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(e)
        return None


def write_history(history : list[dict[str, Any]]) -> None:
    with open(history_path, "w") as f:
        json.dump(history, f, indent=4)


def get_history(ip: str, port: int, timeout: int = 10) -> None | list[dict[str, Any]]:
    url = f"http://{ip}:{port}/history"
    try:
        response = requests.get(url, timeout=timeout)
        contacted_keys[f"{ip}:{port}"] = time.time()
        if response.status_code == 200:
            return response.json()
    except (requests.ConnectionError, requests.Timeout):
        pass
    return None


app : Any = FastAPI()
limiter : Any = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler) # type: ignore



# max 5 requests per minute
@app.get("/history")
@limiter.limit("5/minute") # type: ignore
def __get_history__(request: Request):
    print("someone is asking for history")
    history = read_history()
    if history is not None:
        return history
    return {"message": "History not found"}


def start_history_api(ip : str, port : int) -> None:
    print(f"Service running on http://{ip}:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port) # type: ignore


def should_contact_peer(ip_p: str, port_p: int, ip_loc : str, port_loc : int) -> bool:
    print("checking if should contact peer")
    now = time.time()

    if ip_p == ip_loc and port_p == port_loc:
        return False

    client = f"{ip_p}:{port_p}"

    if client in contacted_keys:
        time_diff = now - contacted_keys[client]
        return time_diff > contact_refill

    return True


def async_sync_history(ip : str, port : int) -> None:
    sleep_duration: int = 5
    new_history : None | list[dict[str, Any]]  = None
    while True:
        time.sleep(sleep_duration)
        print("running main")

        current_history: None | list[dict[str, Any]] = read_history()
        if current_history:
            if len(current_history) < download_threshold:
                print("trying to download larger history pack")
                try:
                    for message in current_history:
                        print("loop running here")
                        ip_peer: str = message["ip"]
                        port_peer: int = message["port"]

                        if should_contact_peer(ip_peer, port_peer, ip, port):
                            new_history: None | list[dict[str, Any]] = get_history(
                                ip_peer, port_peer
                            )
                            print(f"new history {new_history}")

                except Exception as e:
                    print("error in history", e)
                    continue

                if new_history and len(new_history) > len(current_history):
                    print("new history downloaded")
                    write_history(new_history)
                    

async def start_go_app(ip: str, port: int | str, name : str, chatroom : str) -> None:
    # print(f"starting on ip {ip} and port {port}")
    print("starting go app")
    # Start the Go application as a background task
    await asyncio.create_subprocess_exec("go", "run", ".", f"-ip={ip}", f"-port={port}", f"-user={name}", f"-room={chatroom}", cwd="node")


welcome = """
 ██████╗ ██████╗ ███╗   ███╗███╗   ███╗██╗   ██╗███╗   ██╗███████╗
██╔════╝██╔═══██╗████╗ ████║████╗ ████║██║   ██║████╗  ██║██╔════╝
██║     ██║   ██║██╔████╔██║██╔████╔██║██║   ██║██╔██╗ ██║█████╗  
██║     ██║   ██║██║╚██╔╝██║██║╚██╔╝██║██║   ██║██║╚██╗██║██╔══╝  
╚██████╗╚██████╔╝██║ ╚═╝ ██║██║ ╚═╝ ██║╚██████╔╝██║ ╚████║███████╗
 ╚═════╝ ╚═════╝ ╚═╝     ╚═╝╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝
                                                                  
 ██████╗██╗  ██╗ █████╗ ████████╗                                 
██╔════╝██║  ██║██╔══██╗╚══██╔══╝                                 
██║     ███████║███████║   ██║                                    
██║     ██╔══██║██╔══██║   ██║                                    
╚██████╗██║  ██║██║  ██║   ██║                                    
 ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝                                                                                                                             																																																												  
"""

def main(sync_history : bool = True, name: str = 'user', chatroom : str = 'general') -> None:

    ip = "127.0.0.1" # get_public_ip()
    port = find_free_port()
    # Start with an empty history
    write_history([])
    threading.Thread(
        target=lambda: asyncio.run(start_go_app(ip, port, name, chatroom)), daemon=True
    ).start()
    # Wait for the Go application to start
    time.sleep(60)
    # Run FastAPI server in a separate thread
    threading.Thread(target=lambda: start_history_api(ip, port), daemon=True).start()
    
    if sync_history:
        threading.Thread(target=lambda: asyncio.run(async_sync_history(ip, port)), daemon=True).start() # type: ignore
    # Keep the main thread alive
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    room = "general"
    print (welcome)
    agreement_room = input("do you want to join the default room? [y/n] ").lower()
    if agreement_room == "y":
        print("joining the default room")
    else:
        room = input("enter the name of the room you want to join: ")
    agreement_sync = input("do you want to sync chat history? [y/n] ").lower()
    if agreement_sync == "y":
        print("syncing chat allowed, waiting for peers to start activity in room to sync")
        sync_history = True
    else:
        sync_history = False
    name = input("enter your name: ")

    main()
