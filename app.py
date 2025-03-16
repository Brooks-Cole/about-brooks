from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
import anthropic
from anthropic.types import MessageParam
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Union, Optional
from utils.personal_profile import PERSONAL_PROFILE
from prompts.system_prompt import get_system_prompt
from utils.investment_philosophy import INVESTMENT_PHILOSOPHY
from utils.s3_utils import s3_image_url

# Environment variables for configuration
env_loaded = False

# Define the absolute path to the .env file
ENV_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
print(f"Looking for .env file at: {ENV_FILE_PATH}")

# First try to install dotenv if it's missing
try:
    import importlib.metadata
    importlib.metadata.version('python-dotenv')
except (ImportError, importlib.metadata.PackageNotFoundError):
    print("python-dotenv not found, attempting to install...")
    try:
        import subprocess
        subprocess.check_call(["pip", "install", "python-dotenv"])
        print("python-dotenv installed successfully")
    except Exception as e:
        print(f"Error installing python-dotenv: {str(e)}")

# Now try to load the .env file using the absolute path
try:
    # More explicit import to help linters/IDE
    import dotenv
    from dotenv import load_dotenv
    # Load environment variables from the absolute path to .env file
    env_loaded = load_dotenv(dotenv_path=ENV_FILE_PATH, verbose=True)
    if env_loaded:
        print(f"Environment variables loaded from {ENV_FILE_PATH} using dotenv {dotenv.__file__}")
    else:
        print(f"No variables loaded from {ENV_FILE_PATH}")
except ImportError:
    print("dotenv package not available, using default environment variables")
except Exception as e:
    print(f"Error loading environment variables: {str(e)}")

# Manual load from .env file using the absolute path if dotenv fails
if not env_loaded:
    try:
        print(f"Attempting manual load from {ENV_FILE_PATH}")
        with open(ENV_FILE_PATH, 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    key = key.strip()
                    value = value.strip().strip("'").strip('"')
                    os.environ[key] = value
                    print(f"Manually loaded {key} environment variable")
        print("Manually loaded environment variables from .env file")
    except Exception as e:
        print(f"Error manually loading .env file: {str(e)}")


def configure_sessions(app):
    """
    Configure sessions for Vercel deployment - serverless environment requires simpler session handling
    """
    # For serverless, we use simpler cookie-based sessions with a secret key from environment
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    # These settings help with cookie size in serverless environments
    # Store sessions in files for reliability
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_FILE_DIR'] = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'flask_session')
    app.config['SESSION_PERMANENT'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(
        hours=24)  # Extend session lifetime
    # Set to False for local development
    app.config['SESSION_COOKIE_SECURE'] = False
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    # Sign the session cookie for additional security
    app.config['SESSION_USE_SIGNER'] = True
    # Fix for bytes/string issue with session IDs
    app.config['SESSION_USE_SIGNER'] = False
    app.config['SESSION_KEY_PREFIX'] = 'session:'
    
    # Create session directory if it doesn't exist
    if not os.path.exists(app.config['SESSION_FILE_DIR']):
        try:
            os.makedirs(app.config['SESSION_FILE_DIR'])
            print(
                f"Created session directory: {
                    app.config['SESSION_FILE_DIR']}")
        except Exception as e:
            print(f"Error creating session directory: {str(e)}")

    # Initialize Flask-Session
    try:
        from flask_session import Session
        Session(app)
        print("Flask-Session initialized successfully")
    except ImportError:
        print("Flask-Session not available, falling back to default sessions")
    except Exception as e:
        print(f"Error initializing Flask-Session: {str(e)}")

    return app


app = Flask(__name__)
app = configure_sessions(app)  # Configure sessions
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching for static files

# Configure CORS with more specific settings
CORS(app, resources={
    r"/*": {
        "origins": ["*"],  # Allow all origins for now
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Add debug route to check if backend is responding
@app.route('/api/debug', methods=['GET'])
def debug_route():
    """Simple endpoint to verify the API is working"""
    return jsonify({
        "status": "ok",
        "message": "Backend API is responding",
        "timestamp": datetime.now().isoformat(),
        "env_vars_present": {
            "ANTHROPIC_API_KEY": bool(os.environ.get('ANTHROPIC_API_KEY')),
            "SECRET_KEY": bool(os.environ.get('SECRET_KEY')),
            "AWS_ACCESS_KEY_ID": bool(os.environ.get('AWS_ACCESS_KEY_ID')),
            "AWS_SECRET_ACCESS_KEY": bool(os.environ.get('AWS_SECRET_ACCESS_KEY')),
            "AWS_S3_BUCKET": bool(os.environ.get('AWS_S3_BUCKET'))
        }
    })

# Get API key from environment variable
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
print(f"Checking for API key in environment variables: {'Found' if ANTHROPIC_API_KEY else 'Not found'}")

# Fallback to check directly from .env file if environment variable is not set
if not ANTHROPIC_API_KEY:
    try:
        print(f"Attempting to directly read API key from {ENV_FILE_PATH}")
        with open(ENV_FILE_PATH, 'r') as f:
            content = f.read()
            import re
            match = re.search(
                r'ANTHROPIC_API_KEY\s*=\s*[\'"]?(sk-[^\'"]+)', content)
            if match:
                ANTHROPIC_API_KEY = match.group(1)
                print("Retrieved API key directly from .env file")
                # Also set it in environment for other imports
                os.environ['ANTHROPIC_API_KEY'] = ANTHROPIC_API_KEY
            else:
                print("API key pattern not found in .env file content")
    except Exception as e:
        print(f"Failed to retrieve API key from .env file: {str(e)}")

# Last check - validate and report on the API key
if not ANTHROPIC_API_KEY or not ANTHROPIC_API_KEY.startswith('sk-'):
    print("WARNING: Valid ANTHROPIC_API_KEY not found. API calls will fail.")
    # This will cause a clear error if API is called
    ANTHROPIC_API_KEY = "MISSING_API_KEY"
else:
    # Safe API key masking with length check
    if len(ANTHROPIC_API_KEY) > 12:
        print(f"Valid API key found: {ANTHROPIC_API_KEY[:8]}...{ANTHROPIC_API_KEY[-4:]}")
    else:
        print("Valid API key found but too short to safely display")

try:
    # Print key info for debugging
    if ANTHROPIC_API_KEY != "MISSING_API_KEY" and len(ANTHROPIC_API_KEY) > 8:
        print(f"Initializing Anthropic client with API key: {ANTHROPIC_API_KEY[:8]}...")
    
    # Force re-read of environment variable in case it was updated
    env_api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if env_api_key:
        key_preview = env_api_key[:8] if len(env_api_key) > 8 else env_api_key
        print(f"Using API key from environment: {key_preview}...")
        client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
    else:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    # Test if client was successfully initialized
    if hasattr(client, 'api_key'):
        print("Successfully initialized Anthropic client")
    else:
        print("Warning: Client initialized but may not have proper configuration")
        
except Exception as e:
    print(f"Error initializing Anthropic client: {str(e)}")
    import traceback
    traceback.print_exc()


def truncate_history(history, max_messages=20):
    """Truncate conversation history to avoid token limits"""
    if len(history) > max_messages:
        # Keep the most recent messages
        return history[-max_messages:]
    return history


@app.route('/chat', methods=['POST'])
def chat():
    try:
        # Initialize session if not already set
        if 'history' not in session:
            print("Initializing new session")
            session['history'] = []

        data = request.get_json()
        user_input = data.get('user_input', '')

        # Get and truncate history to manage token count
        history = truncate_history(session.get('history', []))

        # Handle first message - auto-generate a welcome message
        if len(history) == 0 and user_input.lower() in [
                'hi', 'hello', 'hey', 'start']:
            welcome_message = (
                "Hi there! I'm Brooks' AI assistant. I can tell you about his background, interests, "
                "projects, and more. What would you like to know about Brooks?"
            )

            # Update conversation history
            history.append({'role': 'user', 'content': user_input})
            history.append({'role': 'assistant', 'content': welcome_message})
            session['history'] = history

            return jsonify({
                'response': welcome_message,
            })

        # Search the photo database for relevant photos based on user input
        # Import the search_photos function
        from utils.photo_database import search_photos
        # Search for up to 3 matching photos
        relevant_photos = search_photos(user_input, limit=3)

        # Format the photo information to include in the API call
        photo_context = ""
        if relevant_photos:
            photo_context = "Here are some relevant photos you can reference in your response:\n"
            for photo in relevant_photos:
                photo_context += f"- {
                    photo['title']}: {
                    photo['description']}. Filename: {
                    photo['filename']}\n"
            # Get S3 bucket name from environment variable
            s3_bucket = os.environ.get('AWS_S3_BUCKET')
            s3_enabled = False
            
            # Check if S3 is properly configured
            try:
                if s3_bucket:
                    from utils.s3_utils import get_s3_client
                    s3_client = get_s3_client()
                    if s3_client:
                        # Test connection
                        s3_client.list_objects_v2(Bucket=s3_bucket, MaxKeys=1)
                        s3_enabled = True
            except Exception as e:
                print(f"S3 connection test failed: {str(e)}")
                s3_enabled = False
                
            if s3_enabled:
                photo_context += f"\nIf relevant, include a photo link by saying exactly: 'You can see a photo of it here: {{s3_url}}' where {{s3_url}} is the full S3 URL I'll provide for each image."
                # Generate S3 URLs for each photo
                for photo in relevant_photos:
                    filename = photo['filename']
                    s3_url = s3_image_url(s3_bucket, f"images/{filename}")
                    photo_context += f"\nFor image '{photo['title']}', use: {s3_url}"
            else:
                photo_context += "\nIf relevant, include a photo link by saying exactly: 'You can see a photo of it here: /static/images/{filename}' where {filename} is the EXACT filename from above, already URL encoded."

        # Normal flow for all other messages
        # Prepare messages for Anthropic API with proper typing
        messages: List[MessageParam] = []
        for msg in history:
            # Create properly typed message params
            if msg["role"] == "user":
                messages.append({"role": "user", "content": msg["content"]})
            elif msg["role"] == "assistant":
                messages.append({"role": "assistant", "content": msg["content"]})
            # Skip any other roles that might not be compatible

        # Add the new user message
        messages.append({"role": "user", "content": user_input})

        # Add investment philosophy to the personal profile
        enriched_profile = PERSONAL_PROFILE.copy()
        
        # Ensure the INVESTMENT_PHILOSOPHY has the key_principles field that system_prompt.py expects
        inv_phil = INVESTMENT_PHILOSOPHY.copy()
        # Map core_principles to key_principles for compatibility
        if "core_principles" in inv_phil:
            inv_phil["key_principles"] = [p["name"] for p in inv_phil["core_principles"]]
        
        enriched_profile["investment_philosophy"] = inv_phil
        
        # Add photo context to the system prompt dynamically
        system_prompt = get_system_prompt(enriched_profile)
        if photo_context:
            system_prompt += f"\n\n# Relevant Photos for This Query\n{photo_context}\n"

        # Call Claude API
        try:
            
            # Log the full messages for debugging
            import json
            print("\nMessage structure:")
            try:
                # Safely print message structure with personal info redacted
                safe_messages = []
                for msg in messages:
                    safe_msg = msg.copy()
                    if 'content' in safe_msg and isinstance(safe_msg['content'], str) and len(safe_msg['content']) > 50:
                        safe_msg['content'] = safe_msg['content'][:50] + "..."
                    safe_messages.append(safe_msg)
                print(json.dumps(safe_messages, indent=2))
            except Exception as json_err:
                print(f"Error printing messages: {str(json_err)}")
            
            # Use an updated model name as the old one is deprecated
            print("\nMaking API call to Anthropic...")
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",  # Updated to newer model
                system=system_prompt,
                messages=messages,
                max_tokens=1500,
                temperature=0.7
            )
            
            print("\nAPI call successful!")
            print(f"Response type: {type(response)}")
            print(f"Response attributes: {dir(response)[:10]}...")
            
            # Get response text safely with type checking
            assistant_response = ""
            if response and hasattr(response, 'content') and response.content:
                print(f"Content type: {type(response.content)}")
                content_preview = ""
                if isinstance(response.content, str) and response.content:
                    content_preview = response.content[:100]
                else:
                    content_preview = "List/Object"
                print(f"Content structure: {content_preview}")
                
                if isinstance(response.content, list) and len(response.content) > 0:
                    # Convert to list explicitly to handle the case where it might be an iterable without __getitem__
                    content_list = list(response.content)
                    first_content = content_list[0] if content_list else None
                    print(f"First content type: {type(first_content)}")
                    fc_attrs = dir(first_content) if first_content else []
                    attr_preview = fc_attrs[:10] if fc_attrs else []
                    print(f"First content attributes: {attr_preview}...")
                    
                    if first_content is not None and hasattr(first_content, 'text'):
                        assistant_response = first_content.text
                    else:
                        fc_attrs = dir(first_content) if first_content else []
                        print(f"Warning: first_content is None or has no 'text' attribute. Available attributes: {fc_attrs}")
            else:
                resp_attrs = dir(response) if response else []
                print(f"Warning: Missing response content. Response structure: {resp_attrs}")
            
            response_length = len(assistant_response) if assistant_response else 0
            print(f"Final response length: {response_length}")
            print("======== END DEBUG ========\n")
                
        except Exception as e:
            print("\n======== API ERROR DEBUG ========")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            # Simplify API key masking without excess type checking
            api_preview = f"{ANTHROPIC_API_KEY[:8]}..." if ANTHROPIC_API_KEY and len(ANTHROPIC_API_KEY) > 8 else "not available"
            print(f"API Key used: {api_preview}")
            
            # Try to determine what kind of error occurred
            error_str = str(e).lower()
            if "unauthorized" in error_str or "key" in error_str or "auth" in error_str:
                print("Likely an API key or authentication issue")
            elif "rate" in error_str or "limit" in error_str or "quota" in error_str:
                print("Likely a rate limit issue")
            elif "timeout" in error_str or "timed out" in error_str:
                print("Likely a timeout issue")
            elif "model" in error_str:
                print("Likely an issue with the model name")
            
            # Log the message structure that caused the issue
            try:
                msg_count = len(messages)
                print(f"Number of messages in request: {msg_count}")
                if msg_count > 0:
                    print(f"Last message role: {messages[-1]['role'] if 'role' in messages[-1] else 'unknown'}")
                    content_preview = messages[-1].get('content', '')[:50]
                    print(f"Last message content preview: {content_preview}...")
            except Exception as msg_err:
                print(f"Error analyzing messages: {str(msg_err)}")
            
            # Print full traceback
            import traceback
            print("\nFull traceback:")
            traceback.print_exc()
            print("======== END ERROR DEBUG ========\n")
            
            # User-facing error message
            assistant_response = "I'm having trouble connecting to my knowledge base. Please try again in a moment."

        # Update conversation history
        history.append({'role': 'user', 'content': user_input})
        history.append({'role': 'assistant', 'content': assistant_response})
        session['history'] = history

        return jsonify({
            'response': assistant_response,
        })
    except Exception as e:
        # Handle any errors
        error_message = f"An error occurred: {str(e)}"
        print(error_message)
        import traceback
        traceback.print_exc()

        # Check specific error types
        error_str = str(e).lower()
        error_type = type(e).__name__
        print(f"Error type: {error_type}")

        user_error_message = "I encountered an error. Please try again or reset the conversation."

        # More specific error handling
        if "token" in error_str or "exceed" in error_str or "overload" in error_str:
            user_error_message = "The conversation has become too long. Please reset the conversation to continue."
        elif "api" in error_str or "anthropic" in error_str or "key" in error_str:
            user_error_message = "There was an issue connecting to the AI service. Please check server configuration."
        elif "session" in error_str or "cookie" in error_str:
            # Session issues
            user_error_message = "Your session has expired or is invalid. Please refresh the page and try again."
            # Clear the session to reset it
            try:
                session.clear()
            except Exception as session_error:
                print(f"Error clearing session: {str(session_error)}")
                # Force a new session
                session.pop('history', None)

        # Return details about the error to help with debugging
        response_data = {
            'response': user_error_message,
            'error': error_message,
            'error_type': error_type
        }

        # Log the full response for debugging
        print(f"Returning error response: {response_data}")

        return jsonify(response_data), 500


@app.route('/reset', methods=['POST'])
def reset_conversation():
    # Clear session data
    try:
        # First try to clear the full session
        try:
            session.clear()
        except Exception as clear_err:
            print(f"Error fully clearing session: {str(clear_err)}")
            # Fall back to just removing specific keys
            for key in list(session.keys()):
                try:
                    session.pop(key, None)
                except Exception:
                    pass
        
        # Ensure flashes are gone
        if session.get('_flashes'):
            try:
                del session['_flashes']
            except Exception:
                pass
                
        # Reinitialize session
        session['history'] = []
        print("Successfully reset session")
        return jsonify({
            'status': 'success',
            'message': 'Conversation has been reset.'
        })
    except Exception as e:
        print(f"Error resetting session: {str(e)}")
        import traceback
        traceback.print_exc()
        # Try one more approach - regenerate the session
        try:
            # Create a completely new session
            import uuid
            session.sid = str(uuid.uuid4())
            session['history'] = []
            return jsonify({
                'status': 'success',
                'message': 'Conversation has been reset with a new session.'
            })
        except Exception as new_err:
            print(f"Error creating new session: {str(new_err)}")
            return jsonify({
                'status': 'error',
                'message': f'Error resetting session: {str(e)}'
            }), 500


@app.route('/test-session', methods=['GET'])
def test_session():
    """Simple endpoint to test if sessions are working properly"""
    try:
        # Try to get existing count
        count = session.get('count', 0)
        # Increment and store it
        count += 1
        session['count'] = count

        # Check if we can store and retrieve history
        if 'history' not in session:
            session['history'] = []

        # Add a test message
        test_message = {'role': 'system', 'content': f'Test message {count}'}
        session['history'].append(test_message)

        # Return the current state
        return jsonify({
            'status': 'success',
            'session_working': True,
            'count': count,
            'history_length': len(session.get('history', [])),
            'session_data': {
                'count': session.get('count'),
                'history': session.get('history')
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'session_working': False,
            'error': str(e)
        }), 500


@app.route('/api/health')
def health_check():
    """Simple health check endpoint to verify API is working"""
    # Collect diagnostic information
    import sys
    import platform

    # Check if we can connect to Anthropic API
    api_status = "ok"
    api_key_masked = "Not set"

    if ANTHROPIC_API_KEY:
        # Mask the API key for security - simplified
        if len(ANTHROPIC_API_KEY) > 12:
            api_key_masked = ANTHROPIC_API_KEY[:8] + "..." + ANTHROPIC_API_KEY[-4:]
        else:
            api_key_masked = "Set but too short"

    try:
        # Just do a simple API check
        models = client.models.list()
        model_names = [
            model.id for model in models.data] if hasattr(
            models, 'data') else []
    except Exception as e:
        api_status = f"error: {str(e)}"
        model_names = []

    return jsonify({
        "status": "ok",
        "version": "1.0",
        "environment": os.environ.get('VERCEL_ENV', 'development'),
        "python_version": sys.version,
        "platform": platform.platform(),
        "api_status": api_status,
        "api_key_check": api_key_masked,
        "available_models": model_names,
        "env_vars": {k: "***" for k in os.environ if k.startswith("ANTHROPIC") or k == "SECRET_KEY"}
    })


@app.route('/api/check')
def check_api():
    """Simple endpoint to quickly check if Anthropic API is working"""
    try:
        # Create properly typed messages
        messages: List[MessageParam] = [
            {"role": "user", "content": "Are you connected?"}
        ]
        
        # Log detailed debugging information
        print("\n======== API CHECK DEBUG ========")
        # Safe API key masking
        api_key_display = "not available"
        if ANTHROPIC_API_KEY:
            if len(ANTHROPIC_API_KEY) > 12:
                api_key_display = f"{ANTHROPIC_API_KEY[:8]}...{ANTHROPIC_API_KEY[-4:]}"
            else:
                api_key_display = "valid but too short to mask properly"
        print(f"API Key: {api_key_display}")
        
        # Verify API key format
        if not ANTHROPIC_API_KEY or not ANTHROPIC_API_KEY.startswith('sk-'):
            key_preview = ANTHROPIC_API_KEY[:4] if ANTHROPIC_API_KEY else "none"
            print(f"WARNING: API key appears invalid. Key format: {key_preview}...")
        
        # Check client initialization
        print(f"Client type: {type(client)}")
        print(f"Client API base URL: {client.base_url if hasattr(client, 'base_url') else 'unknown'}")
        
        # Make API call
        print("Making test API call...")
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",  # Updated model
            system="Please respond with only the word 'Connected'",
            messages=messages,
            max_tokens=10
        )
        
        print(f"Response received - type: {type(response)}")
        print(f"Response attributes: {dir(response)[:10]}...")
        
        # Get response text safely with type checking
        api_response = ""
        if response and hasattr(response, 'content') and response.content:
            print(f"Content type: {type(response.content)}")
            
            if isinstance(response.content, list) and len(response.content) > 0:
                # Convert to list explicitly to handle the case where it might be an iterable without __getitem__
                content_list = list(response.content)
                first_content = content_list[0] if content_list else None
                print(f"First content type: {type(first_content)}")
                
                if first_content and hasattr(first_content, 'text'):
                    api_response = first_content.text
                else:
                    fc_attrs = dir(first_content) if first_content else []
                    print(f"Warning: first_content has no 'text' attribute: {fc_attrs}")
        else:
            print(f"Warning: Response has no content attribute or content is empty")
        
        print(f"Final response: {api_response}")
        print("======== END API CHECK DEBUG ========\n")
        
        # Safely mask API key - simplified
        masked_key = "Invalid API key"
        if ANTHROPIC_API_KEY:
            if len(ANTHROPIC_API_KEY) > 12:
                masked_key = ANTHROPIC_API_KEY[:8] + "..." + ANTHROPIC_API_KEY[-4:]
            else:
                masked_key = "Valid but short key"
        
        # Get additional diagnostic info
        import anthropic
        import platform
        import sys
        
        return jsonify({
            "status": "success",
            "api_response": api_response,
            "api_key": masked_key,
            "diagnostics": {
                "anthropic_version": anthropic.__version__,
                "python_version": sys.version,
                "platform": platform.platform(),
                "model_used": "claude-3-5-sonnet-20241022",
                "api_key_looks_valid": bool(ANTHROPIC_API_KEY and ANTHROPIC_API_KEY.startswith("sk-")),
                "response_received": bool(response),
                "has_content": bool(api_response),
                "response_length": len(api_response) if api_response else 0
            }
        })
    except Exception as e:
        # Log detailed error information
        print("\n======== API CHECK ERROR DEBUG ========")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        
        # Try to determine what kind of error occurred
        error_str = str(e).lower()
        error_type = "unknown"
        if "unauthorized" in error_str or "key" in error_str or "auth" in error_str:
            error_type = "authentication"
            print("Likely an API key or authentication issue")
        elif "rate" in error_str or "limit" in error_str or "quota" in error_str:
            error_type = "rate_limit"
            print("Likely a rate limit issue")
        elif "timeout" in error_str or "timed out" in error_str:
            error_type = "timeout"
            print("Likely a timeout issue")
        elif "model" in error_str:
            error_type = "model_not_found"
            print("Likely an issue with the model name")
        elif "network" in error_str or "connection" in error_str:
            error_type = "network"
            print("Likely a network connectivity issue")
        
        # Print full traceback
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()
        print("======== END API CHECK ERROR DEBUG ========\n")
        
        # Safely mask API key - simplified
        masked_key = "Invalid API key"
        if ANTHROPIC_API_KEY:
            if len(ANTHROPIC_API_KEY) > 12:
                masked_key = ANTHROPIC_API_KEY[:8] + "..." + ANTHROPIC_API_KEY[-4:]
            else:
                masked_key = "Valid but short key"
        
        # Get additional diagnostic info
        import anthropic
        import platform
        import sys
        
        return jsonify({
            "status": "error",
            "error": str(e),
            "error_type": error_type,
            "api_key": masked_key,
            "diagnostics": {
                "anthropic_version": anthropic.__version__,
                "python_version": sys.version,
                "platform": platform.platform(),
                "model_tried": "claude-3-5-sonnet-20241022",
                "api_key_looks_valid": bool(ANTHROPIC_API_KEY and ANTHROPIC_API_KEY.startswith("sk-"))
            }
        })


@app.route('/simple-chat', methods=['POST'])
def simple_chat():
    """Simplified chat endpoint for testing without sessions"""
    try:
        data = request.get_json()
        user_input = data.get('user_input', '')

        print(f"Received user input: {user_input}")

        # Get simple system prompt
        simple_system = "You are a helpful assistant for Brooks. Keep your responses brief and friendly."

        # Call Claude API
        try:
            # Create properly typed messages
            messages: List[MessageParam] = [
                {"role": "user", "content": user_input}
            ]
            
            print("\n======== SIMPLE CHAT API DEBUG ========")
            # Safe API key masking
            api_key_display = "not available"
            if ANTHROPIC_API_KEY and len(ANTHROPIC_API_KEY) > 12:
                api_key_display = f"{ANTHROPIC_API_KEY[:8]}...{ANTHROPIC_API_KEY[-4:]}"
            elif ANTHROPIC_API_KEY:
                api_key_display = "valid but too short to mask properly"
            print(f"API Key: {api_key_display}")
            
            print(f"Model: claude-3-5-sonnet-20241022")
            # Safe user input preview
            input_preview = user_input
            if user_input and len(user_input) > 50:
                input_preview = f"{user_input[:50]}..."
            print(f"User input: {input_preview}")
            print(f"Simple system prompt: {simple_system}")
            
            # Verify client is properly initialized
            print(f"Client instance type: {type(client)}")
            # Safely get client attributes
            client_attrs = dir(client) if client else []
            attr_preview = client_attrs[:10] if client_attrs else []
            print(f"Client attributes: {attr_preview}...")
            
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                system=simple_system,
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )

            print(f"Response received - type: {type(response)}")
            
            # Get response text safely with type checking
            assistant_response = ""
            if response and hasattr(response, 'content') and response.content:
                print(f"Content type: {type(response.content)}")
                
                if isinstance(response.content, list) and len(response.content) > 0:
                    # Convert to list explicitly to handle the case where it might be an iterable without __getitem__
                    content_list = list(response.content)
                    first_content = content_list[0] if content_list else None
                    print(f"First content type: {type(first_content)}")
                    
                    if first_content and hasattr(first_content, 'text'):
                        assistant_response = first_content.text
                    else:
                        fc_attrs = dir(first_content) if first_content else []
                        print(f"Warning: first_content has no 'text' attribute: {fc_attrs}")
            else:
                print(f"Warning: Response has no content attribute or content is empty")
            
            preview = assistant_response[:50] if assistant_response else ""
            print(f"Final response: {preview}...")
            print("======== END SIMPLE CHAT DEBUG ========\n")

            return jsonify({
                'response': assistant_response,
                'debug_info': {
                    'api_key_valid': bool(ANTHROPIC_API_KEY and ANTHROPIC_API_KEY.startswith('sk-')),
                    'response_received': bool(response),
                    'response_length': len(assistant_response) if assistant_response else 0
                }
            })
        except Exception as e:
            print("\n======== SIMPLE CHAT ERROR DEBUG ========")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            # Safely mask API key
            api_key_display = "not available"
            if ANTHROPIC_API_KEY:
                if len(ANTHROPIC_API_KEY) > 12:
                    api_key_display = f"{ANTHROPIC_API_KEY[:8]}...{ANTHROPIC_API_KEY[-4:]}"
                else:
                    api_key_display = "valid but too short to mask properly"
            print(f"API Key used: {api_key_display}")
            
            # Try to determine what kind of error occurred
            error_str = str(e).lower()
            error_type = "unknown"
            if "unauthorized" in error_str or "key" in error_str or "auth" in error_str:
                error_type = "authentication"
            elif "rate" in error_str or "limit" in error_str or "quota" in error_str:
                error_type = "rate_limit"
            elif "timeout" in error_str or "timed out" in error_str:
                error_type = "timeout"
            elif "model" in error_str:
                error_type = "model_not_found"
            
            # Print full traceback
            import traceback
            print("\nFull traceback:")
            traceback.print_exc()
            print("======== END SIMPLE CHAT ERROR DEBUG ========\n")
            
            return jsonify({
                'response': f"API error: {str(e)}",
                'error': str(e),
                'error_type': error_type,
                'debug_info': {
                    'api_key_valid': bool(ANTHROPIC_API_KEY and ANTHROPIC_API_KEY.startswith('sk-')),
                    'error_class': type(e).__name__
                }
            }), 500
    except Exception as e:
        print(f"General error: {str(e)}")
        return jsonify({
            'response': f"Error: {str(e)}",
            'error': str(e)
        }), 500


@app.route('/api/env-check')
def check_env():
    """Diagnostic endpoint to check environment variables loading"""
    # Only accessible in development mode for security
    if os.environ.get('VERCEL_ENV') not in ['production']:
        results = {
            "timestamp": datetime.now().isoformat(),
            "env_file_path": ENV_FILE_PATH,
            "env_file_exists": os.path.exists(ENV_FILE_PATH),
            "anthropic_key_in_env": bool(os.environ.get('ANTHROPIC_API_KEY')),
            "env_variables": {
                k: "***" if "KEY" in k or "SECRET" in k else v 
                for k, v in os.environ.items()
                if k.startswith(("ANTHROPIC", "FLASK", "SECRET"))
            }
        }
        
        # Read .env file content (redacting secrets)
        if os.path.exists(ENV_FILE_PATH):
            try:
                with open(ENV_FILE_PATH, 'r') as f:
                    content = f.read()
                    # Redact API keys and secrets
                    import re
                    redacted_content = re.sub(
                        r'(API_KEY|SECRET)\s*=\s*[\'"]?([^\'"]+)',
                        r'\1=***', 
                        content
                    )
                    results["env_file_preview"] = redacted_content
            except Exception as e:
                results["env_file_error"] = str(e)
        
        return jsonify(results)
    else:
        return jsonify({"error": "This endpoint is only available in development mode"}), 403

@app.route('/api/diagnose')
def diagnose_api():
    """Full diagnostic endpoint that checks API connectivity without requiring the API to actually work"""
    results = {
        "timestamp": datetime.now().isoformat(),
        "environment": os.environ.get('VERCEL_ENV', 'development'),
        "checks": {}
    }
    
    # 1. Check API key format
    api_key = ANTHROPIC_API_KEY or ""
    api_key_valid_format = api_key.startswith("sk-") and len(api_key) > 30
    results["checks"]["api_key_format"] = {
        "status": "pass" if api_key_valid_format else "fail",
        "details": f"API key {'has' if api_key_valid_format else 'does not have'} valid format"
    }
    
    # 2. Check client initialization
    client_initialized = False
    client_type = str(type(client))
    try:
        client_attrs = dir(client)
        client_initialized = "messages" in client_attrs and hasattr(client, "api_key")
    except Exception as e:
        client_error = str(e)
    
    results["checks"]["client_initialization"] = {
        "status": "pass" if client_initialized else "fail",
        "details": f"Client type: {client_type}",
        "error": client_error if not client_initialized and 'client_error' in locals() else None
    }
    
    # 3. Check internet connectivity (without using the API)
    internet_working = False
    try:
        # Use Python's built-in modules to check internet
        import socket
        socket.create_connection(("anthropic.com", 443), timeout=5)
        internet_working = True
    except Exception as e:
        internet_error = str(e)
    
    results["checks"]["internet_connectivity"] = {
        "status": "pass" if internet_working else "fail",
        "details": "Can connect to anthropic.com" if internet_working else "Cannot connect to anthropic.com",
        "error": internet_error if not internet_working and 'internet_error' in locals() else None
    }
    
    # 4. Verify anthropic package version
    try:
        import anthropic
        package_version = anthropic.__version__
        version_ok = True  # You could add more specific version checks here
    except Exception as e:
        package_version = "unknown"
        version_ok = False
        package_error = str(e)
    
    results["checks"]["package_version"] = {
        "status": "pass" if version_ok else "fail",
        "details": f"anthropic package version: {package_version}",
        "error": package_error if not version_ok and 'package_error' in locals() else None
    }
    
    # 5. Try a minimal API request (but catch all errors)
    api_responsive = False
    try:
        # Create a minimal test message
        test_messages = [{"role": "user", "content": "Test"}]
        # Set a short timeout
        import time
        start_time = time.time()
        
        # Attempt API call but catch all errors
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            system="Test",
            messages=test_messages,
            max_tokens=5
        )
        
        # If we get here, the API is responsive
        api_responsive = True
        response_time = time.time() - start_time
        response_content = "Content received" if hasattr(response, 'content') else "No content"
    except Exception as e:
        api_error = str(e)
        api_error_type = type(e).__name__
    
    results["checks"]["api_responsive"] = {
        "status": "pass" if api_responsive else "fail",
        "details": f"API responded in {response_time:.2f}s" if api_responsive else "API request failed",
        "response": response_content if api_responsive and 'response_content' in locals() else None,
        "error": api_error if not api_responsive and 'api_error' in locals() else None,
        "error_type": api_error_type if not api_responsive and 'api_error_type' in locals() else None
    }
    
    # 6. Collect system info
    import sys
    import platform
    
    results["system_info"] = {
        "python_version": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "python_path": sys.executable
    }
    
    # Calculate overall status
    critical_checks = ["api_key_format", "client_initialization", "internet_connectivity"]
    critical_failures = sum(1 for check in critical_checks if results["checks"][check]["status"] == "fail")
    
    if critical_failures == 0 and api_responsive:
        overall_status = "healthy"
    elif critical_failures == 0:
        overall_status = "degraded"
    else:
        overall_status = "critical"
    
    results["overall_status"] = overall_status
    
    return jsonify(results)

@app.route('/')
def serve_frontend():
    try:
        return send_from_directory('static', 'index.html')
    except Exception as e:
        print(f"Error serving index.html: {str(e)}")
        # Return a basic HTML response in case the static file can't be found
        return '<html><body><h1>Brooks\' Personal AI</h1><p>There was an error loading the application. Please check the server logs.</p></body></html>'


# For local development
# Using port 5001 to avoid conflict with AirPlay Receiver
if __name__ == '__main__':
    app.run(debug=True, port=5001)

# This is needed for Vercel deployment
application = app
