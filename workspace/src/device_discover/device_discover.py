import socket
import struct
import json
import time
from datetime import datetime
import threading

MCAST_GRP = "224.1.1.1"
MCAST_PORT = 15000

# ------------------------
# Multicast Receiver
# ------------------------
def listen_multicast():
    global pass_data
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", MCAST_PORT))

    mreq = struct.pack("4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    print("[Receiver] Listening multicast...")

    while True:
        data, addr = sock.recvfrom(1024)
        try:
            payload = data.decode("utf-8")
            print(payload)
            obj = json.loads(payload)
            print(obj)

        except Exception as e:
            print("[Receiver] 解析失敗:", e)


# ------------------------
# Multicast Sender
# ------------------------
def send_multicast():
    global pass_data
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)

    print("[Sender] Start sending...")

    while True:
        packet = {
              "node_id": "gimbal",
              "endpoints": {
                "device_id" : ["HYT_S2000"],
                "video": [
                  "rtsp://192.168.144.64:554/H264"
                ],
                "control": [
                  "192.168.144.64:8888",
                  "192.168.144.30:10000"
                ]
              }
            }
        
        data = json.dumps(packet).encode()
        print(pass_data)
        sock.sendto(data, (MCAST_GRP, MCAST_PORT))
        time.sleep(5)


# ------------------------
# device_discover
# ------------------------
# 啟動 receiver thread
def device_discover():
    global pass_data
    pass_data = True
    threading.Thread(target=listen_multicast, daemon=True).start()
    threading.Thread(target=send_multicast, daemon=True).start()
    
if __name__ == "__main__":
    device_discover()