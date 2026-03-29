"""
Webhook Handler - Send and receive webhooks
"""
import requests

class WebhookServices:
    WEBHOOK_URL = "http://localhost:5678/webhook-test/file"
    
    def send_text(self, text: str):
        payload = {
            "text": text
        }

        try:
            response = requests.post(self.WEBHOOK_URL, json=payload, timeout=60)
            response.raise_for_status()
            print("sent successfully")
            print("Response:", response.text)
            return response.json()

        except requests.exceptions.RequestException as e:
            print("failed to send:", e)
            return []