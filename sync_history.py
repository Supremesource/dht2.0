import requests
import json
from fastapi import FastAPI
import socket
from typing import Any
import time
import os
import uvicorn
import threading
import asyncio

# if i have under 5 messages saved locally i look for peers who can provide me with more
download_trashold = 30

# {key_name : number_of_times_contacted}
contacted_keys : dict = {}
history_path = "/home/johny/test_projects/peerchat/node/chat/messages.json"
history_path2 = "/home/johny/test_projects/peerchat/node/chat/messages2.json"

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
    with open(history_path2, "w") as f:
        json.dump(history, f)


def get_history(ip: str, port: int, timeout: int = 10) -> dict[str, Any]:
    url = f"http://{ip}:{port}/history"
    response = requests.get(url, timeout=timeout)
    return response.json()

app = FastAPI()


@app.get("/history")
def __get_history__():
    print ("someone is asking for history")
    history = read_history()
    if history is not None:
        return history
    return {"message": "History not found"}


def start_history_api(ip, port):
    print(f"Service running on http://{ip}:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)

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
                        new_history = get_history(ip_peer, port_peer)   
                        print (f"new history {new_history}")
                except Exception as e:
                    print("error in history", e)
                    continue
                
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


    
    port = int("50265") #find_free_port()
    ip = "127.0.0.1" #get_public_ip()

    get_history(ip, port)
    exit()
    threading.Thread(target=lambda: start_history_api(ip, port),  daemon=True ).start()
    
    while True:
        time.sleep(3600)
    exit()
    # Start the Go application in a separate thread
    threading.Thread(target=lambda: asyncio.run(start_go_app(ip, port)), daemon=True).start()
    
    # Wait for the Go application to start
    # time.sleep(60)
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