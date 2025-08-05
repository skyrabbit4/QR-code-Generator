#!/usr/bin/env python3
"""
A simple full‑stack application for generating QR codes for uploaded images.

The server accepts image uploads via a POST to `/upload`, saves the image to an
`uploads/` directory, and returns an HTML page containing a QR code that
encodes a URL pointing back to the uploaded image.  The QR code itself is
generated on the fly by embedding a remote QR code API URL into the HTML,
allowing the client browser to fetch the QR code image directly without
requiring extra Python libraries.

To run the application:

```bash
python3 server.py
```

Then visit `http://localhost:3000` in a web browser, choose an image, and
submit the form.  The response page will display a link to the uploaded
image and a QR code that, when scanned, opens the image in the browser.
"""

import http.server
import socketserver
import os
import urllib.parse
import cgi


PORT = 3000


class QRCodeRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Handle GET requests for static files and POST requests for uploads."""

    def do_GET(self):
        """Serve the index page or other static resources."""
        # If root path, serve index.html
        if self.path in ('', '/'):
            self.path = '/index.html'
        return super().do_GET()

    def do_POST(self):
        """Handle image uploads and respond with a page containing a QR code."""
        if self.path != '/upload':
            # We only support /upload for POST
            self.send_error(404, "File not found")
            return

        # Determine a persistent uploads directory relative to this script.  Using
        # os.path.dirname(__file__) ensures that uploads end up in the app
        # directory regardless of the current working directory when the server
        # is started.
        script_dir = os.path.dirname(os.path.abspath(__file__))
        uploads_dir = os.path.join(script_dir, 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)

        # Parse the incoming multipart form data
        ctype = self.headers.get('Content-Type')
        if not ctype:
            self.send_error(400, "Missing Content-Type header")
            return
        # Use FieldStorage from cgi module to parse the POST body
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                'REQUEST_METHOD': 'POST',
                'CONTENT_TYPE': ctype,
            }
        )

        # Expect a file input named 'image'
        if 'image' not in form:
            self.send_error(400, "No image file provided")
            return

        fileitem = form['image']
        # Check if a file was uploaded
        if not getattr(fileitem, 'filename', None):
            self.send_error(400, "No file selected")
            return

        # Sanitize the filename and save to uploads directory
        filename = os.path.basename(fileitem.filename)
        save_path = os.path.join(uploads_dir, filename)
        # Read the file data and write it to disk
        with open(save_path, 'wb') as f:
            data = fileitem.file.read()
            f.write(data)

        # Construct a publicly accessible URL to the uploaded image
        host = self.headers.get('Host', f'localhost:{PORT}')
        # Use urllib.parse.quote to properly encode special characters
        image_path = f'/uploads/{urllib.parse.quote(filename)}'
        image_url = f'http://{host}{image_path}'

        # Generate a QR code URL using a third‑party API.  The API will
        # dynamically create a QR code image when the browser requests it.
        qr_api_url = (
            'https://api.qrserver.com/v1/create-qr-code/?'
            + urllib.parse.urlencode({'data': image_url})
        )

        # Build the response HTML
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>QR Code Result</title>
    <style>
        body {{ font-family: Arial, sans-serif; background-color: #f6f8fa; padding: 40px; }}
        h1 {{ color: #333; }}
        a {{ color: #007bff; }}
    </style>
</head>
<body>
    <h1>QR Code for Your Image</h1>
    <p>Your image has been uploaded successfully.  Use the link below to view it.</p>
    <p><strong>Image URL:</strong> <a href="{image_url}" target="_blank">{image_url}</a></p>
    <p>Scan the QR code below to open the image on another device:</p>
    <img src="{qr_api_url}" alt="QR code for uploaded image">
    <p><a href="/">Upload another image</a></p>
</body>
</html>"""

        # Send response headers
        encoded = html.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(encoded)))
        self.end_headers()
        # Write response body
        self.wfile.write(encoded)


def run_server():
    """Start the HTTP server on the specified port."""
    handler = QRCodeRequestHandler
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"Serving on http://localhost:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


if __name__ == '__main__':
    run_server()