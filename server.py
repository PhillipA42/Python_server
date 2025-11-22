# import BaseHTTPServer
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import sys

class ServerException(Exception):
    """Signals an internal server error."""
    pass

# Case Handler Classes---

class base_case(object):
    '''Base class for all request handlers. Implements basic structure.'''
    
    # Task: Create base_case parent class with test() and act() methods
    def test(self, handler):
        """Returns True if the handler can process the request."""
        raise NotImplementedError()

    def act(self, handler):
        """Performs the action for the request."""
        raise NotImplementedError()
        
class case_default_page(base_case):
    '''Handles the request for the root path ('/').'''

    def test(self, handler):
        # We handle the default path here and set full_path if successful
        if handler.path == "/" or handler.path.strip() == "":
            current_dir = os.getcwd()
            handler.full_path = os.path.join(current_dir, "index.html")
            # If we find index.html, we proceed to case_existing_file
            if os.path.exists(handler.full_path) and os.path.isfile(handler.full_path):
                return True
        return False

    def act(self, handler):
        # If index.html is found, we act just like an existing file
        handler.handle_file(handler.full_path)

class case_no_file(base_case):
    '''File or directory does not exist. Raises a 404 error.'''

    def test(self, handler):
        # Calculate full_path for all subsequent handlers to use
        current_dir = os.getcwd()
        req_path = handler.path.lstrip("/")
        handler.full_path = os.path.join(current_dir, req_path)
        
        # Check if the file (or directory) does not exist
        return not os.path.exists(handler.full_path)

    def act(self, handler):
        # Send a 404 error using the unified error handler
        handler.handle_error(404, "'{0}' not found".format(handler.path))

class case_existing_file(base_case):
    '''File exists and is a file (not a directory).'''

    def test(self, handler):
        # Full path should have been calculated by case_no_file or case_default_page
        if not hasattr(handler, 'full_path'):
            return False # Should not happen with current chain order
            
        # Check if it is a file
        return os.path.isfile(handler.full_path)

    def act(self, handler):
        # Task: handle_file() is executed via act()
        handler.handle_file(handler.full_path)

class case_always_fail(base_case):
    '''Base case if nothing else worked. Catches unhandled paths (like directories).'''

    def test(self, handler):
        # Task: fallback if nothing matches
        return True

    def act(self, handler):
        # If we reach here, it's an unhandled object, which means it's a directory
        handler.handle_error(404, "Unknown object '{0}' or directory listing disabled.".format(handler.path))

# --- 3. Request Handler Class ---
class RequestHandler(BaseHTTPRequestHandler):

    """Handle HTTP requests by returning a fixed 'page'."""

    # Task: Create Cases list in RequestHandler class
    Cases = [case_default_page(), # 1. Check for root path (index.html)
             case_no_file(),      # 2. Check if path exists at all
             case_existing_file(),# 3. Check if path is a regular file
             case_always_fail()]   # 4. Fallback (handles directories)

    # --- Task: Create Error_Page HTML template ---
    Error_Page = """\
        <html>
        <body>
        <h1>{code} - Error accessing {path}</h1>
        <p>{msg}</p>
        <hr>
        <p>Server Time: {date_time}</p>
        </body>
        </html>
        """
    
    # --- Task: Implement handle_error(msg) and proper status codes ---
    def handle_error(self, code, msg):
        """
        Send an error page with a specified HTTP status code.
        """
        
        # Prepare content for the error page template
        content_str = self.Error_Page.format(
            code=code, 
            path=self.path, 
            msg=msg, 
            date_time=self.date_time_string()
        )
        # Encode content and send it with the specified status code
        self.send_content(content_str.encode('utf-8'), code)

    # --- Task: Modify send_content() to accept status code parameter ---
    def send_content(self, content, status=200):
        """
        Send actual content with a specified HTTP status code.
        Content must be bytes.
        """
        self.send_response(status)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        """Serve files based on self.path using os.getcwd(), existence check, and file check."""
        try:
            # 1. Get current working directory
            current_dir = os.getcwd()

            # 2. Build file path from request path
            req_path = self.path.lstrip("/")  # remove leading "/"
            file_path = os.path.join(current_dir, req_path)

            # Default to index.html if root requested (This part is correctly implemented)
            if self.path == "/" or self.path.strip() == "":
                file_path = os.path.join(current_dir, "index.html")

            # 3. Check if file exists
            if not os.path.exists(file_path):
                # *** FIX 1: Use the new handle_error method for a 404 status ***
                self.handle_error(404, "Requested file does not exist.")
                return

            # 4. Check if it is a file
            if not os.path.isfile(file_path):
                self.handle_error(404, "Path is not a file (directory listing not supported).")
                return

            # 5. Serve the file
            self.handle_file(file_path)

        except ServerException as e:
            # Handle internal server error with 500 status (ServerException is custom)
            print(f"Internal Server Error: {e}", file=sys.stderr)
            self.handle_error(500, "Internal Server Error. Please try again later.")
        except Exception as e:
            # Catch any unexpected errors and report them as 500
            print(f"Unexpected Error: {e}", file=sys.stderr)
            self.handle_error(500, f"An unexpected error occurred: {e}")

        
    def handle_file(self, full_path):
        """Read file in binary mode and send it with proper headers."""
        try:
            with open(full_path, 'rb') as html:
                page = html.read()

            # Determine simple content type
            if full_path.endswith(".html"):
                page_str= page.decode("utf-8")

                # the values
                values = {
                    'date_time': self.date_time_string(),
                    'client_host': self.client_address[0],
                    'client_port': self.client_address[1],
                    'command': self.command,
                    'path': self.path
                }

                page = page_str.format(**values).encode("utf-8")
                page_type = "text/html"

            elif full_path.endswith(".txt"):
                page_type = "text/plain"
            else:
                page_type = "application/octet-stream"

                # Send response headers
                self.send_response(200)
                self.send_header("Content-Type", page_type)
                self.send_header("Content-Length", str(len(page)))
                self.end_headers()

                self.wfile.write(page)
        except IOError as e:
            self.send_error_page(500, f"I/O Error: {e}")
            return




    # # Handle a GET request.
    # def send_page(self, page):
    #     self.send_response(200)
    #     self.send_header("Content-type", "text/html")
    #     self.send_header("Content-Length", str(len(page)))
    #     self.end_headers()

        def send_error_page(self, code, message):
            """Send HTML error page."""
            page = f"<h1>{code} - {message}</h1>"
            pages = page.encode('utf-8')
            self.send_response(code)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(pages)))
            self.end_headers()
            self.wfile.write(pages)


#----------------------------------------------------------------------

if __name__ == '__main__':
    serverAddress = ('', 8080)
    server = HTTPServer(serverAddress, RequestHandler)
    print('server running on http://localhost:8080/')
    print('press Ctrl-C to stop it')
    try:      
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n Shutting down server.")
        server.server_close()