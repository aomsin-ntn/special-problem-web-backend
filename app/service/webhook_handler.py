"""
Webhook Handler - Send and receive webhooks
"""
import requests


class WebhookHandler:
    WEBHOOK_URL = "http://localhost:5678/webhook-test/file"
    
    def send_text(self, text: str):
        payload = {
            "text": text
        }

        try:
            response = requests.post(self.WEBHOOK_URL, json=payload, timeout=10)
            response.raise_for_status()
            print("ส่งข้อความสำเร็จ")
            print("Response:", response.text)

        except requests.exceptions.RequestException as e:
            print("ส่งไม่สำเร็จ:", e)