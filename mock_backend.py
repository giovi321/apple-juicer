#!/usr/bin/env python3
"""
Simple mock backend to demonstrate WhatsApp indexing progress bar functionality.
This simulates the API responses without requiring a full database setup.
"""

import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading

class MockBackendHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-API-Token, X-Backup-Session')
        self.end_headers()

    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # Send CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        
        if path == '/api/backups':
            self.handle_list_backups()
        elif path.startswith('/api/backups/') and path.endswith('/artifacts/whatsapp/chats'):
            backup_id = path.split('/')[3]
            self.handle_list_whatsapp_chats(backup_id)
        elif path.startswith('/api/backups/') and '/artifacts/whatsapp/chats/' in path:
            parts = path.split('/')
            backup_id = parts[3]
            chat_guid = parts[6]
            self.handle_get_whatsapp_chat(backup_id, chat_guid)
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'{"error": "Not found"}')

    def handle_list_backups(self):
        """Return mock backup data with indexing progress"""
        # Simulate different backup states for testing
        backups = [
            {
                "id": "test-backup-1",
                "display_name": "iPhone Test Backup",
                "device_name": "iPhone 14",
                "product_version": "16.5",
                "is_encrypted": True,
                "status": "indexing",  # Changed from "indexed" to "indexing"
                "decryption_status": "decrypted",
                "last_indexed_at": None,
                "decrypted_at": "2023-12-22T10:00:00Z",
                "size_bytes": 1024 * 1024 * 1024 * 5,  # 5GB
                "last_modified_at": "2023-12-22T09:00:00Z",
                "indexing_progress": 2,  # Added actual progress values
                "indexing_total": 4,
                "indexing_artifact": "whatsapp"
            }
        ]
        
        response = {"backups": backups, "base_directory": "/tmp"}
        self.send_json_response(response)

    def handle_list_whatsapp_chats(self, backup_id):
        """Return empty WhatsApp chats list to trigger progress display"""
        response = {"items": []}
        self.send_json_response(response)

    def handle_get_whatsapp_chat(self, backup_id, chat_guid):
        """Return mock WhatsApp chat data"""
        chat = {
            "chat_guid": chat_guid,
            "title": "Test Chat",
            "participant_count": 2,
            "last_message_at": "2023-12-22T10:00:00Z",
            "metadata": {}
        }
        messages = []
        response = {"chat": chat, "messages": messages}
        self.send_json_response(response)

    def send_json_response(self, data, status_code=200):
        """Send JSON response"""
        response_data = json.dumps(data, indent=2)
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response_data.encode('utf-8'))))
        self.end_headers()
        self.wfile.write(response_data.encode('utf-8'))

    def log_message(self, format, *args):
        """Suppress default logging"""
        pass

def run_mock_backend():
    """Run the mock backend server"""
    server_address = ('', 8002)
    httpd = HTTPServer(server_address, MockBackendHandler)
    print("Mock backend running on http://localhost:8002")
    print("Press Ctrl+C to stop")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down mock backend")
        httpd.shutdown()

if __name__ == '__main__':
    run_mock_backend()
