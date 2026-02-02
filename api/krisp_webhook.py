import os
import json
from http.server import BaseHTTPRequestHandler
from vercel_kv import kv

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """
        Handles the incoming webhook from Krisp.ai.
        It stores the payload in a Vercel KV store.
        """
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)

        try:
            payload = json.loads(post_data.decode('utf-8'))

            # Get existing meetings from KV store or initialize an empty list
            meetings = kv.get('krisp_meetings') or []

            # Append the new payload
            meetings.append(payload)

            # Save the updated list back to the KV store
            kv.set('krisp_meetings', meetings)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'success', 'message': 'Webhook received and stored.'}).encode('utf-8'))

        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'error', 'message': 'Invalid JSON payload.'}).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'error', 'message': f'Internal Server Error: {str(e)}'}).encode('utf-8'))

    def do_GET(self):
        """
        Handles the pull request from the SE Command Center.
        It retrieves all meetings from the Vercel KV store, returns them,
        and then clears the store.
        """
        # API Key Authentication
        expected_api_key = os.environ.get("KRISP_API_KEY")
        auth_header = self.headers.get('Authorization')

        if not expected_api_key or not auth_header or auth_header != f"Bearer {expected_api_key}":
            self.send_response(401)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'error', 'message': 'Unauthorized.'}).encode('utf-8'))
            return

        try:
            # Retrieve all meetings from the KV store
            meetings = kv.get('krisp_meetings') or []

            # Clear the store after retrieving the meetings
            kv.delete('krisp_meetings')

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(meetings).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'error', 'message': f'Internal Server Error: {str(e)}'}).encode('utf-8'))