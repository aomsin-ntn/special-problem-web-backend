"""
Webhook Handler - Send and receive webhooks
"""
import requests
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import json
from pathlib import Path


class WebhookHandler:
    """Handle webhook operations"""
    
    def __init__(self):
        self.timeout = 10  # seconds
        self.retry_count = 3
        self.backoff_factor = 2
    
    async def send_webhook(
        self,
        webhook_url: str,
        data: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Send webhook to external service
        
        Args:
            webhook_url: Target webhook URL
            data: Data to send
            headers: Custom headers (optional)
            
        Returns:
            Response data or error info
        """
        default_headers = {
            "Content-Type": "application/json",
            "User-Agent": "FastAPI-Webhook/1.0",
            "Timestamp": datetime.now().isoformat(),
        }
        
        if headers:
            default_headers.update(headers)
        
        # Retry logic
        for attempt in range(self.retry_count):
            try:
                response = requests.post(
                    webhook_url,
                    json=data,
                    headers=default_headers,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                return {
                    "status": "success",
                    "status_code": response.status_code,
                    "response": response.json() if response.text else {},
                    "timestamp": datetime.now().isoformat(),
                }
                
            except requests.exceptions.RequestException as e:
                if attempt < self.retry_count - 1:
                    wait_time = self.backoff_factor ** attempt
                    await asyncio.sleep(wait_time)
                    continue
                
                return {
                    "status": "failed",
                    "error": str(e),
                    "attempt": attempt + 1,
                    "timestamp": datetime.now().isoformat(),
                }
    
    async def send_webhook_async(
        self,
        webhook_urls: list,
        data: Dict[str, Any]
    ) -> list:
        """
        Send webhooks to multiple URLs asynchronously
        
        Args:
            webhook_urls: List of target URLs
            data: Data to send
            
        Returns:
            List of responses
        """
        tasks = [
            self.send_webhook(url, data)
            for url in webhook_urls
        ]
        return await asyncio.gather(*tasks)
    
    def log_webhook(self, webhook_url: str, data: Dict, status: str):
        """Log webhook activity"""
        log_dir = Path("logs/webhooks")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "webhook_url": webhook_url,
            "data": data,
            "status": status,
        }
        
        log_file = log_dir / f"webhooks_{datetime.now().strftime('%Y-%m-%d')}.log"
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")


# Global instance
webhook_handler = WebhookHandler()


# Example usage functions
async def send_ocr_result_webhook(
    webhook_url: str,
    fields: Dict[str, Any],
    filename: str,
    saved_as: str
):
    """Send OCR results via webhook"""
    data = {
        "event": "ocr_completed",
        "filename": filename,
        "saved_as": saved_as,
        "fields": fields,
        "timestamp": datetime.now().isoformat(),
    }
    
    result = await webhook_handler.send_webhook(webhook_url, data)
    webhook_handler.log_webhook(webhook_url, data, result["status"])
    
    return result


async def send_upload_notification(
    webhook_url: str,
    file_info: Dict[str, Any]
):
    """Send upload notification"""
    data = {
        "event": "file_uploaded",
        "file": file_info,
        "timestamp": datetime.now().isoformat(),
    }
    
    result = await webhook_handler.send_webhook(webhook_url, data)
    webhook_handler.log_webhook(webhook_url, data, result["status"])
    
    return result
