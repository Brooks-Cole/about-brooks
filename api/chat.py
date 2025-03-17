from http.server import BaseHTTPRequestHandler
import json
import os
import anthropic
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import parse_qs
from datetime import datetime

# Import your system prompt
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prompts.system_prompt import get_system_prompt
from utils.personal_profile import PERSONAL_PROFILE
from utils.investment_philosophy import INVESTMENT_PHILOSOPHY

# Email configuration
def send_chat_email(user_input, assistant_response, email_to=PERSONAL_PROFILE.get("email")):
    try:
        email_from = os.environ.get('EMAIL_SENDER')
        email_password = os.environ.get('EMAIL_PASSWORD')
        
        if not all([email_from, email_password, email_to]):
            print("Email configuration incomplete. Not sending email.")
            return False
            
        # Create message
        msg = MIMEMultipart()
        msg['From'] = email_from
        msg['To'] = email_to
        msg['Subject'] = f"New Chat with AI - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        # Email body
        body = f"""
        <html>
        <body>
            <h2>New Conversation with Your AI</h2>
            <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <hr>
            <h3>User Message:</h3>
            <p>{user_input}</p>
            <hr>
            <h3>AI Response:</h3>
            <p>{assistant_response}</p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        # Connect to server and send email
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_from, email_password)
        text = msg.as_string()
        server.sendmail(email_from, email_to, text)
        server.quit()
        
        return True
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        return False

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Parse request
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data)
            user_input = data.get('user_input', '')
            
            # Get API key
            ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
            if not ANTHROPIC_API_KEY:
                self.send_error(500, "API key not configured")
                return

            # Initialize Claude client
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            
            # Get system prompt
            enriched_profile = PERSONAL_PROFILE.copy()
            inv_phil = INVESTMENT_PHILOSOPHY.copy()
            if "core_principles" in inv_phil:
                inv_phil["key_principles"] = [p["name"] for p in inv_phil["core_principles"]]
            enriched_profile["investment_philosophy"] = inv_phil
            
            system_prompt = get_system_prompt(enriched_profile)
            
            # Call Claude API
            messages = [{"role": "user", "content": user_input}]
            
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                system=system_prompt,
                messages=messages,
                max_tokens=1500,
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
            
            # Send email with conversation (won't block the response)
            try:
                send_chat_email(user_input, assistant_response)
            except Exception as email_error:
                print(f"Email notification error (non-critical): {str(email_error)}")
            
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