import json
import os
import urllib.request

def send_notifications(message: str):
    ntfy_topic = os.getenv("PRICERADAR_NTFY_TOPIC")
    webhook = os.getenv("PRICERADAR_WEBHOOK_URL")
    if ntfy_topic:
        server = os.getenv("PRICERADAR_NTFY_SERVER", "https://ntfy.sh")
        req = urllib.request.Request(f"{server.rstrip('/')}/{ntfy_topic}", data=message.encode(), headers={"Title":"PriceRadar","Priority":"default"}, method="POST")
        try: urllib.request.urlopen(req, timeout=15).read()
        except Exception: pass
    if webhook:
        req = urllib.request.Request(webhook, data=json.dumps({"text":message,"content":message}).encode(), headers={"Content-Type":"application/json"}, method="POST")
        try: urllib.request.urlopen(req, timeout=15).read()
        except Exception: pass
