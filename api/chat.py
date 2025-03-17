from http.server import BaseHTTPRequestHandler
import json
import os
import random
import anthropic
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import parse_qs
from datetime import datetime
import time
import traceback
import html

# Common carrier email-to-SMS gateways
CARRIER_GATEWAYS = {
    'verizon': 'vtext.com',
    'tmobile': 'tmomail.net',
    'att': 'txt.att.net',
    'sprint': 'messaging.sprintpcs.com',
    'boost': 'sms.myboostmobile.com',
    'cricket': 'sms.cricketwireless.net',
    'uscellular': 'email.uscc.net',
}

# Import your system prompt
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prompts.system_prompt import get_system_prompt
from utils.personal_profile import PERSONAL_PROFILE
from utils.investment_philosophy import INVESTMENT_PHILOSOPHY

# SMS notification functions
def send_sms_via_email(message, phone_number=None, carrier=None):
    """Send SMS via email-to-SMS gateway"""
    try:
        # Get credentials from environment variables
        email_from = os.environ.get('EMAIL_SENDER')
        email_password = os.environ.get('EMAIL_PASSWORD')
        phone_number = phone_number or os.environ.get('ADMIN_PHONE_NUMBER')
        carrier = carrier or os.environ.get('CARRIER', 'verizon')  # Default to Verizon
        
        # Check if all required credentials are available
        if not all([email_from, email_password, phone_number]):
            logger.warning("Email-to-SMS configuration incomplete. SMS not sent.")
            return False
        
        # Validate carrier
        if carrier.lower() not in CARRIER_GATEWAYS:
            logger.warning(f"Unknown carrier: {carrier}. Using Verizon as default.")
            carrier = 'verizon'
        
        # Format recipient address
        recipient = f"{phone_number}@{CARRIER_GATEWAYS[carrier.lower()]}"
        
        # Create message
        msg = MIMEText(message)
        msg['From'] = email_from
        msg['To'] = recipient
        msg['Subject'] = ''  # Subject is often ignored in SMS gateways
        
        # Connect to server and send email
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_from, email_password)
        server.sendmail(email_from, recipient, msg.as_string())
        server.quit()
        
        logger.info(f"SMS via email gateway sent to {phone_number}")
        return True
    except Exception as e:
        logger.error(f"Failed to send SMS via email: {str(e)}")
        return False

# Format a conversation exchange for SMS
def format_conversation_for_sms(user_message, ai_response, session_id):
    """Format messages for SMS delivery (truncated for length limits)"""
    # Truncate messages if they're too long for SMS
    if len(user_message) > 100:
        user_message = user_message[:97] + "..."
    if len(ai_response) > 300:
        ai_response = ai_response[:297] + "..."
    
    # Format the message - keep it minimal for SMS
    sms_text = f"USER: {user_message}\nAI: {ai_response}"
    
    return sms_text

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("chat_api")

# Configure conversation logger - separate from main application logs
conversation_logger = logging.getLogger("conversations")
conversation_logger.setLevel(logging.INFO)

# Check if we're in a Vercel environment or similar serverless setup
IS_SERVERLESS = os.environ.get('VERCEL') == '1' or os.environ.get('SERVERLESS') == '1'

# Create a formatter for the logs
formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')

# If we're not in a serverless environment, set up file logging
if not IS_SERVERLESS:
    try:
        # Set up directory for logs
        LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
        os.makedirs(LOG_DIR, exist_ok=True)
        
        # Create a file handler that logs to a different file each day
        log_file = os.path.join(LOG_DIR, f"conversations_{datetime.now().strftime('%Y-%m-%d')}.log")
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        
        # Add the handler to the logger
        conversation_logger.addHandler(file_handler)
        logger.info("File logging enabled")
    except Exception as e:
        logger.warning(f"Could not set up file logging: {str(e)}")

# Always add console handler as fallback for serverless environments
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
conversation_logger.addHandler(console_handler)
logger.info("Console logging enabled")

# Full conversation tracking to maintain entire chat history
full_conversations = {}

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
            if conversation_id in full_conversations and len(full_conversations[conversation_id]) >= 2:
                # Send email before removing
                try:
                    send_conversation_email(
                        conversation_id, 
                        full_conversations[conversation_id],
                        subject=f"Timed Out AI Conversation - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                    )
                except Exception as e:
                    print(f"Error sending timeout email: {str(e)}")
            
            # Mark for removal
            sessions_to_remove.append(conversation_id)
    
    # Clean up expired sessions
    for conversation_id in sessions_to_remove:
        if conversation_id in full_conversations:
            del full_conversations[conversation_id]
        if conversation_id in last_activity:
            del last_activity[conversation_id]
    
    return len(sessions_to_remove)

# Improved email formatting with better styling
# Replace your current send_conversation_email function with this one:

def send_conversation_email(conversation_id, messages, email_to=PERSONAL_PROFILE.get("email"), subject=None):
    try:
        email_from = os.environ.get('EMAIL_SENDER')
        email_password = os.environ.get('EMAIL_PASSWORD')
        
        if not all([email_from, email_password, email_to]):
            print("Email configuration incomplete. Not sending email.")
            return False
        
        # Format start and end times
        start_time = datetime.fromtimestamp(last_activity[conversation_id] - (len(messages) // 2 * 60))  # Rough estimate
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds() // 60  # Duration in minutes
            
        # Create message
        msg = MIMEMultipart()
        msg['From'] = email_from
        msg['To'] = email_to
        msg['Subject'] = subject or f"Complete AI Conversation - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        # Build HTML body with improved styling
        conversation_html = ""
        
        # This is the key change - make sure we're processing ALL messages in the conversation
        total_messages = len(messages)
        print(f"Preparing email with {total_messages} messages")
        
        for i in range(total_messages):
            message = messages[i]
            role_is_user = i % 2 == 0
            role = "User" if role_is_user else "AI"
            
            # Style the message differently based on role
            style = "background-color: #f0f0f0; border-radius: 10px; padding: 15px; margin-bottom: 10px;"
            if not role_is_user:
                style = "background-color: #e1f5fe; border-radius: 10px; padding: 15px; margin-bottom: 10px;"
                
            # Convert plain text to HTML with line breaks preserved
            formatted_message = html.escape(str(message)).replace('\n', '<br>')
            
            conversation_html += f"""
            <div style="{style}">
                <p style="margin: 0; font-weight: bold; margin-bottom: 5px;">{role}:</p>
                <div style="margin-left: 10px;">
                    {formatted_message}
                </div>
            </div>
            """
        
        # Email body with more comprehensive metadata
        body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                .conversation {{ border: 1px solid #ddd; padding: 20px; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Complete AI Conversation</h2>
                    <p><strong>Session ID:</strong> {conversation_id[:8]}...</p>
                    <p><strong>Started:</strong> {start_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p><strong>Ended:</strong> {end_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p><strong>Duration:</strong> Approximately {duration} minutes</p>
                    <p><strong>Messages:</strong> {len(messages)}</p>
                </div>
                
                <div class="conversation">
                    {conversation_html}
                </div>
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
        
        print(f"Email sent successfully for conversation {conversation_id[:8]}... with {total_messages} messages")
        return True
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        traceback.print_exc()
        return False
    
# Enhanced trigger detection for conversation end
def is_conversation_ending(message):
    """
    Determine if the message signals the likely end of a conversation.
    Returns True if the message contains end indicators.
    """
    # Keywords that might indicate end of conversation
    end_indicators = [
        "goodbye", "bye", "thank", "thanks", "that's all", "that is all", 
        "have a good", "talk later", "talk to you later", "ttyl", "appreciate", 
        "until next time", "see you", "adios", "au revoir",
        "take care", "got what i needed", "all set", "good night", "good day"
    ]
    
    message_lower = message.lower()
    
    # Simple matching
    direct_match = any(indicator in message_lower for indicator in end_indicators)
    
    # Length-based heuristic (very short messages + contains thanks can be goodbyes)
    short_thank = len(message_lower.split()) <= 5 and ("thank" in message_lower or "thanks" in message_lower)
    
    return direct_match or short_thank

class Handler(BaseHTTPRequestHandler):
    # Replace the do_POST method in your Handler class with this one:
    
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
                timestamp = datetime.now().timestamp()
                session_id = f"{user_agent[:20]}-{timestamp}"
            
            # Initialize or update full conversation tracking
            if session_id not in full_conversations:
                full_conversations[session_id] = []
            
            # Update last activity time (for timeout detection)
            last_activity[session_id] = datetime.now().timestamp()
            
            # Add the latest messages to conversation history
            full_conversations[session_id].append(user_input)
            full_conversations[session_id].append(assistant_response)
            
            # Debug logging to see conversation length
            print(f"Conversation {session_id[:8]}... now has {len(full_conversations[session_id])} messages")
            
            # Log the conversation exchange and send SMS
            try:
                user_agent = self.headers.get('User-Agent', 'unknown')
                # Get IP address safely (may not be available in all environments)
                ip_address = 'unknown'
                if hasattr(self, 'client_address') and self.client_address:
                    ip_address = self.client_address[0]
                elif 'X-Forwarded-For' in self.headers:
                    ip_address = self.headers.get('X-Forwarded-For')
                
                # Prepare log data
                log_data = {
                    'timestamp': datetime.now().isoformat(),
                    'session_id': session_id[:8] + '...' if len(session_id) > 8 else session_id,  # Truncate for privacy
                    'user_agent': user_agent[:50] + '...' if len(user_agent) > 50 else user_agent,
                    'ip_address': ip_address,
                    'user_message': user_input,
                    'ai_response': assistant_response
                }
                
                # Log in a structured format that's easy to parse later
                log_entry = json.dumps(log_data)
                
                # Write to log
                conversation_logger.info(log_entry)
                
                # Send SMS notification for each message exchange
                try:
                    # Format the message for SMS
                    sms_text = format_conversation_for_sms(user_input, assistant_response, session_id)
                    # Send the SMS
                    send_sms_via_email(sms_text)
                except Exception as sms_error:
                    logger.error(f"Failed to send SMS notification: {str(sms_error)}")
                    # Continue even if SMS fails
            except Exception as log_error:
                # If logging fails, don't break the main functionality
                logger.error(f"Failed to log conversation: {str(log_error)}")
                # Continue processing without breaking user experience
            
            # Check if this might be the end of a conversation
            should_send_email = is_conversation_ending(user_input)
            
            # If the conversation seems to be ending, send the full email summary
            if should_send_email and len(full_conversations[session_id]) >= 2:
                try:
                    # Important: Log the number of messages before sending
                    print(f"Sending email for conversation with {len(full_conversations[session_id])} messages")
                    
                    success = send_conversation_email(
                        session_id, 
                        full_conversations[session_id]
                    )
                    
                    if success:
                        print(f"Email sent successfully with {len(full_conversations[session_id])} messages")
                        # Clear conversation after sending
                        if session_id in full_conversations:
                            del full_conversations[session_id]
                        if session_id in last_activity:
                            del last_activity[session_id]
                    else:
                        print("Failed to send email, keeping conversation in memory")
                except Exception as email_error:
                    print(f"Email notification error (non-critical): {str(email_error)}")
                    traceback.print_exc()
            
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
            error_msg = str(e)
            stack_trace = traceback.format_exc()
            
            # Log the error
            logger.error(f"API Error: {error_msg}")
            logger.error(f"Stack trace: {stack_trace}")
            
            # Log in conversation log too for context
            conversation_logger.error(f"API Error: {error_msg}")
            
            # Send response to client
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            error_data = json.dumps({
                'error': error_msg
            })
            
            self.wfile.write(error_data.encode('utf-8'))

    def do_OPTIONS(self):
        # Handle CORS preflight requests
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()