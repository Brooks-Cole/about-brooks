from http.server import BaseHTTPRequestHandler
import json
import os
import random
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

# Conversation tracking for email reports
conversation_history = {}

# Timestamp tracking for session timeout
last_activity = {}
SESSION_TIMEOUT = 10 * 60  # 10 minutes in seconds

# Periodic cleanup function to check for inactive sessions
def cleanup_inactive_sessions():
    current_time = datetime.now().timestamp()
    sessions_to_remove = []
    
    for conversation_id, last_time in list(last_activity.items()):
        # If session has been inactive for longer than timeout
        if current_time - last_time > SESSION_TIMEOUT:
            if conversation_id in conversation_history and len(conversation_history[conversation_id]) >= 2:
                # Send email before removing
                try:
                    send_conversation_email(
                        conversation_id, 
                        conversation_history[conversation_id]
                    )
                except Exception as e:
                    print(f"Error sending timeout email: {str(e)}")
            
            # Mark for removal
            sessions_to_remove.append(conversation_id)
    
    # Clean up expired sessions
    for conversation_id in sessions_to_remove:
        if conversation_id in conversation_history:
            del conversation_history[conversation_id]
        if conversation_id in last_activity:
            del last_activity[conversation_id]
    
    return len(sessions_to_remove)

# Email configuration
def send_conversation_email(conversation_id, messages, email_to=PERSONAL_PROFILE.get("email")):
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
        msg['Subject'] = f"Complete AI Conversation - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        # Build HTML body
        conversation_html = ""
        for i, message in enumerate(messages):
            role = "User" if i % 2 == 0 else "AI"
            conversation_html += f"""
            <div style="margin-bottom: 15px;">
                <h3>{role}:</h3>
                <p style="margin-left: 20px;">{message}</p>
                {'' if i == len(messages)-1 else '<hr style="border-top: 1px solid #ddd;">'}
            </div>
            """
        
        # Email body
        body = f"""
        <html>
        <body>
            <h2>Complete Conversation with Your AI</h2>
            <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Conversation ID:</strong> {conversation_id[:8]}...</p>
            <div style="margin-top: 20px; border: 1px solid #ccc; padding: 15px; border-radius: 5px;">
                {conversation_html}
            </div>
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
            
            # Run session cleanup occasionally
            if random.random() < 0.05:  # ~5% chance each request
                try:
                    cleaned = cleanup_inactive_sessions()
                    if cleaned > 0:
                        print(f"Cleaned up {cleaned} inactive sessions")
                except Exception as cleanup_error:
                    print(f"Session cleanup error: {str(cleanup_error)}")
            
            # Extract cookie or create session ID
            cookies = self.headers.get('Cookie', '')
            session_id = None
            
            # Try to extract session cookie if it exists
            if cookies:
                for cookie in cookies.split(';'):
                    if cookie.strip().startswith('session_id='):
                        session_id = cookie.strip().split('=')[1]
                        break
            
            # If no cookie found, generate a new session ID from user agent + timestamp
            if not session_id:
                user_agent = self.headers.get('User-Agent', 'unknown')
                session_id = user_agent + str(datetime.now().timestamp())
            
            # Update conversation history
            if session_id not in conversation_history:
                conversation_history[session_id] = []
            
            # Update last activity time (for timeout detection)
            last_activity[session_id] = datetime.now().timestamp()
            
            # Add the latest messages
            conversation_history[session_id].append(user_input)
            conversation_history[session_id].append(assistant_response)
            
            # Check if this might be the end of a conversation (simple heuristic)
            # Keywords that might indicate end of conversation or natural stopping point
            end_indicators = [
                "goodbye", "bye", "thank", "thanks", "that's all", "that is all", 
                "have a good", "talk later", "talk to you later", "ttyl"
            ]
            
            should_send_email = any(indicator in user_input.lower() for indicator in end_indicators)
            
            # If the conversation seems to be ending, send the full email summary
            if should_send_email and len(conversation_history[session_id]) >= 2:
                try:
                    send_conversation_email(
                        session_id, 
                        conversation_history[session_id]
                    )
                    # Clear history after sending
                    del conversation_history[session_id]
                    if session_id in last_activity:
                        del last_activity[session_id]
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