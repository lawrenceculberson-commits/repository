import json
import os
from datetime import datetime
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    """
    Vercel serverless function to handle Krisp.ai webhooks.

    - POST: Receives webhook from Krisp.ai and stores temporarily (requires Krisp auth)
    - GET: Returns stored data to SE Command Center (requires API key auth)
    """

    # Temporary storage file path
    STORAGE_FILE = '/tmp/krisp_meetings.json'

    def do_POST(self):
        """Handle POST from Krisp.ai webhook"""
        try:
            # Verify Krisp.ai authentication
            krisp_auth = os.environ.get('KRISP_WEBHOOK_AUTH', '')
            provided_auth = self.headers.get('Authorization', '')

            if krisp_auth and provided_auth != krisp_auth:
                self.send_response(403)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'status': 'error',
                    'message': 'Invalid Krisp.ai authentication'
                }).encode())
                return

            # Read the incoming data
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            meeting_data = json.loads(post_data.decode('utf-8'))

            # Add timestamp
            meeting_data['received_at'] = datetime.utcnow().isoformat()

            # Load existing meetings
            meetings = []
            try:
                with open(self.STORAGE_FILE, 'r') as f:
                    meetings = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                meetings = []

            # Append new meeting
            meetings.append(meeting_data)

            # Save back to file
            with open(self.STORAGE_FILE, 'w') as f:
                json.dump(meetings, f)

            # Respond to Krisp.ai
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'status': 'success',
                'message': 'Meeting data received'
            }).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'status': 'error',
                'message': str(e)
            }).encode())

    def do_GET(self):
        """Handle GET from SE Command Center (authenticated)"""
        try:
            # Check API key authentication
            auth_header = self.headers.get('Authorization', '')
            expected_key = os.environ.get('KRISP_API_KEY', '')

            if not expected_key:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'error': 'KRISP_API_KEY not configured in Vercel'
                }).encode())
                return

            # Verify Bearer token
            if not auth_header.startswith('Bearer '):
                self.send_response(401)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'error': 'Missing or invalid Authorization header'
                }).encode())
                return

            provided_key = auth_header.replace('Bearer ', '').strip()
            if provided_key != expected_key:
                self.send_response(403)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'error': 'Invalid API key'
                }).encode())
                return

            # Authentication successful - return meetings
            meetings = []
            try:
                with open(self.STORAGE_FILE, 'r') as f:
                    meetings = json.load(f)

                # Clear the file after reading (optional - prevents re-importing)
                with open(self.STORAGE_FILE, 'w') as f:
                    json.dump([], f)

            except (FileNotFoundError, json.JSONDecodeError):
                meetings = []

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(meetings).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'error': str(e)
            }).encode())
