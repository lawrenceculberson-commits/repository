from http.server import BaseHTTPRequestHandler
import json
import os
from urllib.parse import urlparse, parse_qs
from vercel_blob import put, list, delete


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """
        Handles the incoming webhook from Krisp.ai.
        It stores the JSON payload as a new blob in Vercel Blob Storage.
        """
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))

            # Use a unique name for each file, e.g., based on meeting ID or a timestamp
            # This avoids overwriting and makes it easier to manage individual meetings.
            meeting_id = data.get('meeting_id', f'unknown_id_{os.urandom(4).hex()}')
            filename = f"krisp_data/{meeting_id}.json"

            # Upload the JSON data to Vercel Blob Storage
            # The `put` function returns a dictionary with the URL of the stored blob
            blob_result = put(filename, json.dumps(data), {'access': 'public'}) # Store as a JSON string

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'success', 'url': blob_result['url']}).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'error', 'message': str(e)}).encode('utf-8'))

    def do_GET(self):
        """
        Handles the pull request from the SE Command Center.
        It retrieves all meeting blobs, returns their content, and then deletes them.
        """
        # --- Authentication ---
        expected_api_key = os.environ.get("KRISP_API_KEY")
        auth_header = self.headers.get('Authorization')

        if not expected_api_key or not auth_header or auth_header != f"Bearer {expected_api_key}":
            self.send_response(401, "Unauthorized")
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Missing or invalid API key"}).encode('utf-8'))
            return

        try:
            # List all blobs in the "krisp_data" directory
            blobs = list(prefix="krisp_data/", options={'limit': 500}).get('blobs', [])
            
            all_meetings = []
            urls_to_delete = []

            # Download the content of each blob
            for blob in blobs:
                # In Vercel Blob, you can't directly read the content via the serverless function.
                # The recommended way is to fetch the content via its public URL.
                # This requires the blob to be uploaded with `access: 'public'`.
                import requests
                response = requests.get(blob['url'])
                if response.status_code == 200:
                    all_meetings.append(response.json())
                    urls_to_delete.append(blob['url'])
            
            # Delete the blobs after they have been successfully retrieved
            if urls_to_delete:
                delete(urls_to_delete)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(all_meetings).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'error', 'message': f"Internal Server Error: {str(e)}"}).encode('utf-8'))
