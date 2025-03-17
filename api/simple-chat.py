from http.server import BaseHTTPRequestHandler
import json
import os
import anthropic

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Parse request
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data)
            user_input = data.get('user_input', '')
            user_data = data.get('user_data', None)
            
            # Get API key
            ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
            if not ANTHROPIC_API_KEY:
                self.send_error(500, "API key not configured")
                return

            # Initialize Claude client
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            
            # Use a simpler system prompt
            simple_system = "You are a helpful assistant for Brooks. Keep your responses brief and friendly."
            
            # Add basic user context if available
            if user_data:
                device_type = user_data.get('deviceType', 'unknown device')
                simple_system += f" The user is on a {device_type}."
                
                # Add time of day context if available
                visit_time = user_data.get('visitTime', '')
                if visit_time:
                    simple_system += f" They are chatting with you at {visit_time}."
            
            # Call Claude API
            messages = [{"role": "user", "content": user_input}]
            
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                system=simple_system,
                messages=messages,
                max_tokens=4000,
                temperature=0.7
            )
            
            # Extract response text
            assistant_response = ""
            if response and hasattr(response, 'content') and response.content:
                if isinstance(response.content, list) and len(response.content) > 0:
                    content_list = list(response.content)
                    first_content = content_list[0] if content_list else None
                    if first_content is not None and hasattr(first_content, 'text'):
                        assistant_response = first_content.text
            
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            
            response_data = json.dumps({
                'response': assistant_response
            })
            
            self.wfile.write(response_data.encode('utf-8'))
            
        except Exception as e:
            print(f"Error: {str(e)}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            error_data = json.dumps({
                'error': str(e)
            })
            
            self.wfile.write(error_data.encode('utf-8'))
    
    def do_OPTIONS(self):
        # Handle CORS preflight requests
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()