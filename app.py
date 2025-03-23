from flask import Flask, render_template, request, jsonify, session, send_from_directory, redirect, url_for, render_template_string, make_response
from flask_cors import CORS
import anthropic
from anthropic.types import MessageParam, ContentBlock
from typing import Literal
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Union, Optional
from utils.personal_profile import PERSONAL_PROFILE
from prompts.system_prompt import get_system_prompt
from utils.investment_philosophy import INVESTMENT_PHILOSOPHY
from utils.s3_utils import s3_image_url
from authlib.integrations.flask_client import OAuth
import secrets
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from utils.db import MONGO_URI, get_or_create_user, store_platform_token, get_user_interests, log_chat_interaction
from utils.platform_data import process_platform_data
from admin_dashboard import admin

# Environment variables for configuration
env_loaded = False

# Create a new MongoDB client and connect to the server
mongodb_client = MongoClient(MONGO_URI, server_api=ServerApi('1'))

# Send a ping to confirm a successful connection
try:
    mongodb_client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(f"MongoDB connection error: {e}")
    # Set to None if connection fails
    mongodb_client = None

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
    Configure sessions using MongoDB for storage
    """
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.environ.get('FLASK_SECRET_KEY', secrets.token_urlsafe(16)))
    
    # Configure Flask-Session for MongoDB storage
    app.config['SESSION_TYPE'] = 'mongodb'
    app.config['SESSION_MONGODB'] = mongodb_client
    app.config['SESSION_MONGODB_DB'] = 'aboutBrooks'
    app.config['SESSION_MONGODB_COLLECT'] = 'sessions'  # String, not a collection object
    app.config['SESSION_PERMANENT'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
    app.config['SESSION_COOKIE_NAME'] = 'session'
    app.config['SESSION_COOKIE_SECURE'] = False  # False for local dev
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_USE_SIGNER'] = True
    app.config['SESSION_KEY_PREFIX'] = 'session:'
    
    # Monkey patch MongoDBSessionInterface for pymongo 4.x compatibility
    try:
        from flask_session import Session
        from flask_session.sessions import MongoDBSessionInterface

        # Fix the save_session method for pymongo 4.x compatibility
        from flask.helpers import want_bytes
        original_save_session = MongoDBSessionInterface.save_session
        
        def patched_save_session(self, app, session, response):
            domain = self.get_cookie_domain(app)
            path = self.get_cookie_path(app)
            
            if not session:
                if session.modified:
                    # Use delete_one for pymongo 4.x
                    self.store.delete_one({'id': session.sid})
                    response.delete_cookie(app.config['SESSION_COOKIE_NAME'],
                                          domain=domain, path=path)
                return

            # Get all cookie parameters
            conditional_cookie_kwargs = {}
            httponly = self.get_cookie_httponly(app)
            secure = self.get_cookie_secure(app)
            if hasattr(self, 'has_same_site_capability') and self.has_same_site_capability:
                conditional_cookie_kwargs["samesite"] = self.get_cookie_samesite(app)
            expires = self.get_expiration_time(app, session)
            val = self.serializer.dumps(dict(session))
            
            # Use update_one instead of update for pymongo 4.x
            store_id = session.sid
            self.store.update_one(
                {'id': store_id},
                {'$set': {'id': store_id, 'val': val, 'expiration': expires}},
                upsert=True
            )
            
            # Set the cookie
            if self.use_signer:
                session_id = self._get_signer(app).sign(want_bytes(session.sid))
            else:
                session_id = session.sid
            response.set_cookie(app.config["SESSION_COOKIE_NAME"], session_id,
                               expires=expires, httponly=httponly,
                               domain=domain, path=path, secure=secure,
                               **conditional_cookie_kwargs)

        # Apply the monkey patch
        MongoDBSessionInterface.save_session = patched_save_session
        
        # Initialize the session with our patched method
        Session(app)
        print("Flask-Session initialized with MongoDB storage (with pymongo 4.x patch)")
    except ImportError:
        print("Flask-Session not available, falling back to default sessions")
    except Exception as e:
        print(f"Error initializing Flask-Session: {str(e)}")

    return app


app = Flask(__name__)
app = configure_sessions(app)  # Configure sessions
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching for static files

# Set up logging
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Register blueprints
app.register_blueprint(admin)

# Configure CORS with more specific settings
CORS(app, resources={
    r"/*": {
        "origins": ["*"],  # Allow all origins for now
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Initialize OAuth
oauth = OAuth(app)

# Platform configurations (replace with your actual client IDs/secrets)
PLATFORMS = {
    'x': {
        'client_id': os.environ.get('X_CLIENT_ID', 'your_x_client_id'),
        'client_secret': os.environ.get('X_CLIENT_SECRET', 'your_x_client_secret'),
        'authorize_url': 'https://twitter.com/i/oauth2/authorize',
        'token_url': 'https://api.twitter.com/2/oauth2/token',
        'scopes': ['tweet.read', 'users.read', 'offline.access'],
        'pkce': True
    },
    'instagram': {
        'client_id': os.environ.get('INSTAGRAM_CLIENT_ID', 'your_instagram_client_id'),
        'client_secret': os.environ.get('INSTAGRAM_CLIENT_SECRET', 'your_instagram_client_secret'),
        'authorize_url': 'https://api.instagram.com/oauth/authorize',
        'token_url': 'https://api.instagram.com/oauth/access_token',
        'scopes': ['user_profile', 'user_media']
    },
    'spotify': {
        'client_id': os.environ.get('SPOTIFY_CLIENT_ID', 'your_spotify_client_id'),
        'client_secret': os.environ.get('SPOTIFY_CLIENT_SECRET', 'your_spotify_client_secret'),
        'authorize_url': 'https://accounts.spotify.com/authorize',
        'token_url': 'https://accounts.spotify.com/api/token',
        'scopes': ['user-read-recently-played', 'user-top-read']
    },
    'youtube': {
        'client_id': os.environ.get('YOUTUBE_CLIENT_ID', 'your_youtube_client_id'),
        'client_secret': os.environ.get('YOUTUBE_CLIENT_SECRET', 'your_youtube_client_secret'),
        'authorize_url': 'https://accounts.google.com/o/oauth2/v2/auth',
        'token_url': 'https://oauth2.googleapis.com/token',
        'scopes': ['https://www.googleapis.com/auth/youtube.readonly', 
                  'https://www.googleapis.com/auth/youtube.force-ssl',
                  'https://www.googleapis.com/auth/youtubepartner']
    },
    'facebook': {
        'client_id': os.environ.get('FACEBOOK_CLIENT_ID', 'your_facebook_client_id'),
        'client_secret': os.environ.get('FACEBOOK_CLIENT_SECRET', 'your_facebook_client_secret'),
        'authorize_url': 'https://www.facebook.com/v12.0/dialog/oauth',
        'token_url': 'https://graph.facebook.com/v12.0/oauth/access_token',
        'scopes': ['public_profile']
    },
    'linkedin': {
        'client_id': os.environ.get('LINKEDIN_CLIENT_ID', 'your_linkedin_client_id'),
        'client_secret': os.environ.get('LINKEDIN_CLIENT_SECRET', 'your_linkedin_client_secret'),
        'authorize_url': 'https://www.linkedin.com/oauth/v2/authorization',
        'token_url': 'https://www.linkedin.com/oauth/v2/accessToken',
        'scopes': ['r_liteprofile']
    },
    'tiktok': {
        'client_id': os.environ.get('TIKTOK_CLIENT_ID', 'your_tiktok_client_key'),
        'client_secret': os.environ.get('TIKTOK_CLIENT_SECRET', 'your_tiktok_client_secret'),
        'authorize_url': 'https://www.tiktok.com/v2/auth/authorize',
        'token_url': 'https://open.tiktokapis.com/v2/oauth/token/',
        'scopes': ['user.info.basic'],
        'pkce': True,
        'token_endpoint_auth_method': 'client_secret_post'
    },
    'reddit': {
        'client_id': os.environ.get('REDDIT_CLIENT_ID', 'your_reddit_client_id'),
        'client_secret': os.environ.get('REDDIT_CLIENT_SECRET', 'your_reddit_client_secret'),
        'authorize_url': 'https://www.reddit.com/api/v1/authorize',
        'token_url': 'https://www.reddit.com/api/v1/access_token',
        'scopes': ['identity', 'read']
    },
    'discord': {
        'client_id': os.environ.get('DISCORD_CLIENT_ID', 'your_discord_client_id'),
        'client_secret': os.environ.get('DISCORD_CLIENT_SECRET', 'your_discord_client_secret'),
        'authorize_url': 'https://discord.com/api/oauth2/authorize',
        'token_url': 'https://discord.com/api/oauth2/token',
        'scopes': ['identify']
    }
}

# Register OAuth clients
for platform, config in PLATFORMS.items():
    client_kwargs = {
        'scope': ' '.join(config['scopes']),
        'token_endpoint_auth_method': config.get('token_endpoint_auth_method', 'client_secret_basic')
    }
    if config.get('pkce'):
        client_kwargs['code_challenge_method'] = 'S256'
    oauth.register(
        name=platform,
        client_id=config['client_id'],
        client_secret=config['client_secret'],
        authorize_url=config['authorize_url'],
        access_token_url=config['token_url'],
        client_kwargs=client_kwargs
    )

# Add debug routes to check if backend is responding
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
            "AWS_ACCESS_KEY_ID": bool(os.environ.get('AWS_ACCESS_KEY_ID'))
        }
    })
        
@app.route('/api/simple-chat', methods=['POST', 'OPTIONS'])
def simple_chat():
    """Simple chat endpoint for fallback functionality"""
    if request.method == 'OPTIONS':
        # Handle CORS preflight request
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        data = request.json
        user_input = data.get('user_input', '')
        user_data = data.get('user_data', None)
        
        # Get API key
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            return jsonify({"error": "API key not configured"}), 500

        # Initialize Claude client
        client = anthropic.Anthropic(api_key=api_key)
        
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
        
        return jsonify({"response": assistant_response})
        
    except Exception as e:
        app.logger.error(f"Error in simple chat endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Add a simpler test endpoint
@app.route('/test', methods=['GET'])
def test_route():
    """Super simple test endpoint"""
    return "API is working"

# Serve privacy policy
@app.route('/privacy', methods=['GET'])
def privacy_policy():
    """Serve the privacy policy page"""
    return send_from_directory('static', 'PrivacyStatement.html')

# Feedback endpoint for chat messages
@app.route('/api/feedback', methods=['POST'])
def feedback():
    try:
        data = request.get_json()
        message = data.get('message', '')
        feedback = data.get('feedback', '')
        
        # Log feedback to MongoDB
        user_id, _ = get_or_create_user(request)
        
        # Get the database reference
        db = mongodb_client.aboutBrooks if mongodb_client else None
        
        if db:
            # Store feedback in chat_interactions collection
            db.chat_interactions.insert_one({
                'user_id': user_id,
                'timestamp': datetime.now(),
                'message': message,
                'feedback': feedback,
                'type': 'feedback'
            })
            
            logger.info(f"Feedback recorded: {feedback} for message from user {user_id[:8]}")
        else:
            logger.warning("Cannot store feedback: MongoDB not available")
        
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Error logging feedback: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Endpoint to provide S3 image URLs
@app.route('/api/s3-images', methods=['GET'])
def s3_images():
    """Get S3 image URLs for the frontend"""
    try:
        # Get the S3 bucket name
        s3_bucket = os.environ.get('AWS_S3_BUCKET', 'aboutbrooks')
        
        # Don't need AWS credentials to generate URLs for public objects
        # Generate S3 URLs
        region = os.environ.get('AWS_REGION', 'us-east-1')
        base_url = f"https://{s3_bucket}.s3.{region}.amazonaws.com"
        
        # URLs for key images - directly from bucket root
        images = {
            "profileImage": f"{base_url}/Me%20on%20a%20boat%20in%20Alabama.jpeg",
            "workshop": f"{base_url}/Workshop.jpeg",
            "fishing": f"{base_url}/Sailfish.jpeg",
            "reading": f"{base_url}/Book%20Vase.jpeg",
            "projects": f"{base_url}/Carrier%20Pigeons.jpeg",
            "bucketInfo": {
                "name": s3_bucket,
                "region": region,
                "baseUrl": base_url
            }
        }
        
        return jsonify(images)
    except Exception as e:
        print(f"Error in s3_images endpoint: {str(e)}")
        return jsonify({
            "error": str(e),
            "bucketInfo": {
                "name": os.environ.get('AWS_S3_BUCKET', 'aboutbrooks'),
                "region": os.environ.get('AWS_REGION', 'us-east-1')
            }
        }), 500

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

# Initialize Anthropic client as None first
anthropic_client = None

try:
    # Print key info for debugging
    if ANTHROPIC_API_KEY != "MISSING_API_KEY" and len(ANTHROPIC_API_KEY) > 8:
        print(f"Initializing Anthropic client with API key: {ANTHROPIC_API_KEY[:8]}...")
    
    # Force re-read of environment variable in case it was updated
    env_api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if env_api_key:
        key_preview = env_api_key[:8] if len(env_api_key) > 8 else env_api_key
        print(f"Using API key from environment: {key_preview}...")
        anthropic_client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
    else:
        anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    # Test if client was successfully initialized
    if hasattr(anthropic_client, 'api_key'):
        print("Successfully initialized Anthropic client")
    else:
        print("Warning: Client initialized but may not have proper configuration")
        
except Exception as e:
    print(f"Error initializing Anthropic client: {str(e)}")
    import traceback
    traceback.print_exc()
    anthropic_client = None


def truncate_history(history, max_messages=20):
    """Truncate conversation history to avoid token limits"""
    if len(history) > max_messages:
        # Keep the most recent messages
        return history[-max_messages:]
    return history


def enhance_prompt_with_user_data(user_id, system_prompt):
    """Enhance the system prompt with user data from MongoDB"""
    try:
        # Get user's interests from MongoDB
        interests = get_user_interests(user_id, min_confidence=0.3, limit=10)
        
        if interests:
            # Format interests for the prompt
            interest_section = "\n\n# User Interests\n"
            interest_section += "Based on the user's data, they have shown interest in:\n"
            
            for interest in interests:
                topic = interest.get('topic', '')
                source = interest.get('source', 'unknown')
                confidence = interest.get('confidence', 0)
                if topic and confidence >= 0.3:  # Only include interests with decent confidence
                    interest_section += f"- {topic.title()} (source: {source}, confidence: {confidence:.1f})\n"
            
            # Add recommendation to reference interests
            interest_section += "\nTry to personalize responses to these interests when appropriate."
            
            # Add the interest section to the system prompt
            system_prompt += interest_section
            
            logger.debug(f"Enhanced prompt with {len(interests)} user interests")
        
        return system_prompt
    
    except Exception as e:
        logger.error(f"Error enhancing prompt with user data: {str(e)}")
        return system_prompt  # Return the original prompt on error


def safe_api_call(client, url, token, headers=None, params=None):
    """Make an API call with robust error handling and logging
    
    Args:
        client: The OAuth client instance
        url: API endpoint to call
        token: OAuth token for authentication
        headers: Optional additional headers
        params: Optional query parameters
        
    Returns:
        tuple: (success, data, status_code, error_message)
    """
    try:
        # Combine headers if provided
        call_headers = headers or {}
        
        # Add timeout for all API calls
        start_time = datetime.now()
        response = client.get(url, token=token, headers=call_headers, params=params, timeout=10)
        elapsed = (datetime.now() - start_time).total_seconds()
        
        # Log API call details
        status = response.status_code
        log_prefix = f"API call to {url.split('?')[0]}"
        
        if status == 200:
            print(f"{log_prefix} succeeded in {elapsed:.2f}s")
            try:
                data = response.json()
                return True, data, status, None
            except ValueError as json_err:
                error_msg = f"Invalid JSON response: {str(json_err)}"
                print(f"{log_prefix} returned invalid JSON: {error_msg}")
                return False, None, status, error_msg
        else:
            error_msg = f"Status {status}"
            try:
                error_data = response.json()
                if isinstance(error_data, dict):
                    error_detail = error_data.get('error', {})
                    if isinstance(error_detail, dict):
                        error_msg = f"{error_msg}: {error_detail.get('message', 'Unknown error')}"
                    elif isinstance(error_detail, str):
                        error_msg = f"{error_msg}: {error_detail}"
            except Exception:
                # Use response text if JSON parsing fails
                if response.text:
                    error_msg = f"{error_msg}: {response.text[:100]}"
            
            print(f"{log_prefix} failed with {error_msg}")
            return False, None, status, error_msg
            
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        print(f"Error calling {url}: {error_type} - {error_msg}")
        
        # Classify error for better logging
        if "timeout" in error_msg.lower() or error_type == "Timeout":
            print(f"API call to {url} timed out")
            return False, None, 408, "Request timed out"
        elif "connection" in error_msg.lower():
            print(f"Connection error to {url}")
            return False, None, 503, "Connection error"
        else:
            print(f"Unknown error calling {url}: {error_type} - {error_msg}")
            return False, None, 500, f"{error_type}: {error_msg}"


def fetch_platform_data(platform, client, token):
    """Centralized function to fetch data from various social platforms
    
    Args:
        platform: The social platform name ('x', 'spotify', 'youtube', etc.)
        client: The OAuth client instance for the platform
        token: The OAuth token for the authenticated user
        
    Returns:
        String with formatted platform-specific data
    """
    try:
        # First check if token is valid
        if not token:
            return f"  - Connected to {platform.capitalize()} (no valid token)\n"
        if client is None:
            logger.error(f"Client is None for platform: {platform}")
            return f"  - Connected to {platform.capitalize()} (client not found)\n"
            
        # Platform-specific implementations
        if platform == 'x':
            # Get X (Twitter) data
            success, data, status, error = safe_api_call(
                client, 'https://api.twitter.com/2/users/me', token)
                
            if success and data:
                twitter_data = data.get('data', {})
                return f"  - X Username: @{twitter_data.get('username', 'unknown')}\n"
            else:
                return f"  - Connected to X (error: {error or f'status {status}'})\n"
        
        elif platform == 'spotify':
            # Get Spotify data with error handling
            success, data, status, error = safe_api_call(
                client, 'https://api.spotify.com/v1/me/player/recently-played', token)
                
            if success and data:
                spotify_data = data.get('items', [])
                if spotify_data:
                    track = spotify_data[0].get('track', {})
                    if not track:
                        return f"  - Connected to Spotify (no recent tracks)\n"
                        
                    track_name = track.get('name', 'unknown')
                    artists = track.get('artists', [{}])
                    artist_name = artists[0].get('name', 'unknown') if artists else 'unknown'
                    return f"  - Recently played: {track_name} by {artist_name}\n"
                else:
                    # Try profile data as fallback
                    success, profile_data, profile_status, profile_error = safe_api_call(
                        client, 'https://api.spotify.com/v1/me', token)
                    
                    if success and profile_data:
                        display_name = profile_data.get('display_name', 'unknown user')
                        return f"  - Spotify User: {display_name} (no recent tracks)\n"
                    else:
                        return f"  - Connected to Spotify (no playback data available)\n"
            else:
                # Try profile data as fallback
                success, profile_data, profile_status, profile_error = safe_api_call(
                    client, 'https://api.spotify.com/v1/me', token)
                
                if success and profile_data:
                    display_name = profile_data.get('display_name', 'unknown user')
                    return f"  - Spotify User: {display_name}\n"
                else:
                    return f"  - Connected to Spotify (error: {error or f'status {status}'})\n"
        
        elif platform == 'reddit':
            # Get Reddit data with error handling
            success, data, status, error = safe_api_call(
                client, 'https://oauth.reddit.com/api/v1/me', token, 
                headers={'User-Agent': 'BrooksChatbot/1.0 (by /u/yourusername)'})
                
            if success and data:
                return (f"  - Reddit Username: u/{data.get('name', 'unknown')}\n"
                        f"  - Karma: {data.get('total_karma', 0)}\n")
            else:
                return f"  - Connected to Reddit (error: {error or f'status {status}'})\n"
        
        elif platform == 'discord':
            # Get Discord data with error handling
            success, data, status, error = safe_api_call(
                client, 'https://discord.com/api/users/@me', token)
                
            if success and data:
                discord_info = f"  - Discord Username: {data.get('username', 'unknown')}\n"
                # Check for discriminator - some newer Discord accounts don't have one
                if 'discriminator' in data and data['discriminator'] != '0':
                    discord_info += f"  - Discord Tag: #{data.get('discriminator', '0000')}\n"
                return discord_info
            else:
                return f"  - Connected to Discord (error: {error or f'status {status}'})\n"
        
        elif platform == 'youtube':
            youtube_info = []
            data_retrieved = False
            
            # Get YouTube channel info with error handling
            success, channel_data, status, error = safe_api_call(
                client, 'https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics&mine=true', token)
                
            if success and channel_data:
                channels = channel_data.get('items', [])
                if channels:
                    channel = channels[0]
                    channel_title = channel.get('snippet', {}).get('title', 'unknown')
                    subscribers = channel.get('statistics', {}).get('subscriberCount', '0')
                    youtube_info.append(f"  - YouTube Channel: {channel_title} ({subscribers} subscribers)\n")
                    data_retrieved = True
                else:
                    youtube_info.append(f"  - YouTube: No channel data found\n")
            else:
                youtube_info.append(f"  - YouTube: Channel data unavailable ({error or f'status {status}'})\n")
            
            # Try YouTube watch history with graceful fallbacks
            history_retrieved = False
            
            # Step 1: Try watch history
            try:
                success, history_data, history_status, history_error = safe_api_call(
                    client, 'https://www.googleapis.com/youtube/v3/history?maxResults=5', token)
                    
                if success and history_data:
                    videos = history_data.get('items', [])
                    if videos:
                        youtube_info.append("  - Recently watched videos:\n")
                        for video in videos:
                            title = video.get('snippet', {}).get('title', 'Unknown video')
                            youtube_info.append(f"    • {title}\n")
                        history_retrieved = True
                        data_retrieved = True
            except Exception as e:
                print(f"History API error: {str(e)} - falling back to liked videos")
            
            # Step 2: If history fails, try liked videos
            if not history_retrieved:
                try:
                    success, liked_data, liked_status, liked_error = safe_api_call(
                        client, 'https://www.googleapis.com/youtube/v3/videos?part=snippet&myRating=like&maxResults=3', token)
                        
                    if success and liked_data:
                        videos = liked_data.get('items', [])
                        if videos:
                            youtube_info.append("  - Recently liked videos:\n")
                            for video in videos:
                                title = video.get('snippet', {}).get('title', 'Unknown video')
                                youtube_info.append(f"    • {title}\n")
                            history_retrieved = True
                            data_retrieved = True
                except Exception as e:
                    print(f"Liked videos API error: {str(e)} - falling back to subscriptions")
            
            # Step 3: If history and likes fail, try subscriptions
            if not history_retrieved:
                try:
                    success, subs_data, subs_status, subs_error = safe_api_call(
                        client, 'https://www.googleapis.com/youtube/v3/subscriptions?part=snippet&mine=true&maxResults=3', token)
                        
                    if success and subs_data:
                        subscriptions = subs_data.get('items', [])
                        if subscriptions:
                            youtube_info.append("  - Channel subscriptions:\n")
                            for sub in subscriptions:
                                channel_name = sub.get('snippet', {}).get('title', 'Unknown channel')
                                youtube_info.append(f"    • {channel_name}\n")
                            data_retrieved = True
                except Exception as e:
                    print(f"Subscriptions API error: {str(e)}")
            
            return ''.join(youtube_info) if youtube_info else f"  - Connected to YouTube (no data available)\n"
        
        elif platform == 'facebook':
            # Get Facebook data with error handling
            success, data, status, error = safe_api_call(
                client, 'https://graph.facebook.com/v12.0/me?fields=name,id', token)
                
            if success and data:
                return f"  - Facebook Name: {data.get('name', 'unknown')}\n"
            else:
                return f"  - Connected to Facebook (error: {error or f'status {status}'})\n"
        
        elif platform == 'instagram':
            # Get Instagram data with error handling
            success, data, status, error = safe_api_call(
                client, 'https://graph.instagram.com/me?fields=username,account_type', token)
                
            if success and data:
                return f"  - Instagram Username: {data.get('username', 'unknown')}\n"
            else:
                return f"  - Connected to Instagram (error: {error or f'status {status}'})\n"
        
        elif platform == 'linkedin':
            # Get LinkedIn data with error handling
            success, data, status, error = safe_api_call(
                client, 'https://api.linkedin.com/v2/me', token)
                
            if success and data:
                first_name = data.get('localizedFirstName', '')
                last_name = data.get('localizedLastName', '')
                if first_name or last_name:
                    return f"  - LinkedIn: {first_name} {last_name}\n"
                else:
                    return f"  - LinkedIn: Connected (no name data available)\n"
            else:
                return f"  - Connected to LinkedIn (error: {error or f'status {status}'})\n"
        
        elif platform == 'tiktok':
            # Get TikTok data with error handling
            success, data, status, error = safe_api_call(
                client, 'https://open.tiktokapis.com/v2/user/info/', token)
                
            if success and data:
                user_data = data.get('data', {}).get('user', {})
                return f"  - TikTok Username: {user_data.get('display_name', 'unknown')}\n"
            else:
                return f"  - Connected to TikTok (error: {error or f'status {status}'})\n"
        
        # Default return if platform not specifically handled
        return f"  - Connected to {platform.capitalize()} (platform not fully supported)\n"
        
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        print(f"Error in fetch_platform_data for {platform}: {error_type} - {error_msg}")
        
        # Add stack trace for unexpected errors
        import traceback
        traceback.print_exc()
        
        return f"  - Connected to {platform.capitalize()} (error: {error_type})\n"


def get_all_connected_platforms_data(session_data, oauth_instance):
    """Fetch data from all connected social platforms for a user
    
    Args:
        session_data: The Flask session containing OAuth tokens
        oauth_instance: The OAuth instance for creating clients
        
    Returns:
        String with formatted data from all connected platforms
    """
    # Initialize result
    social_data = "\n\n# User Social Data\n"
    
    # Check if user has any connected platforms
    if 'connected_platforms' not in session_data or not session_data['connected_platforms']:
        return ""
    
    # Fetch data for each connected platform
    for platform in session_data['connected_platforms']:
        if f'{platform}_token' in session_data:
            social_data += f"- Connected to {platform.capitalize()}\n"
            
            # Fetch platform-specific data
            try:
                client = oauth_instance.create_client(platform)
                if client is None:
                    social_data += f"  - Error: OAuth client not found for {platform}\n"
                    continue
                token = session_data[f'{platform}_token']
                platform_data = fetch_platform_data(platform, client, token)
                if platform_data:
                    social_data += platform_data
            except Exception as e:
                print(f"Error setting up client for {platform}: {str(e)}")
                social_data += f"  - Error connecting to {platform}\n"
    
    return social_data if social_data != "\n\n# User Social Data\n" else ""


# Main page with consent and connect links
@app.route('/oauth')
def oauth_index():
    if 'connected_platforms' not in session:
        session['connected_platforms'] = []
    return render_template('oauth.html', platforms=PLATFORMS.keys(), connected=session['connected_platforms'])

# Initiate OAuth for a platform
@app.route('/connect/<platform>')
def connect(platform):
    if platform not in PLATFORMS:
        return "Invalid platform", 400
    if 'consent' not in session or not session['consent']:
        return redirect(url_for('oauth_index'))
    redirect_uri = url_for('callback', platform=platform, _external=True)
    client = oauth.create_client(platform)
    if client is None:
        logger.error(f"Failed to create OAuth client for platform: {platform}")
        return "OAuth client not found", 500
    
    # Get the complete redirect URI
    base_url = request.url_root.rstrip('/')
    if base_url.endswith(':5001'):
        # Local development
        complete_redirect_uri = f"{base_url}/callback/{platform}"
    else:
        # Production
        complete_redirect_uri = f"{base_url}/callback/{platform}"
    
    logger.info(f"OAuth redirect for {platform} using redirect_uri: {complete_redirect_uri}")
    return client.authorize_redirect(complete_redirect_uri)

# Handle OAuth callback
@app.route('/callback/<platform>')
def callback(platform):
    if platform not in PLATFORMS:
        return "Invalid platform", 400
    
    # Check for consent
    if 'consent' not in session or not session['consent']:
        return redirect(url_for('oauth_index'))
    
    # Get user ID from request
    user_id, user = get_or_create_user(request)
    
    try:
        # Complete OAuth flow and get token
        client = oauth.create_client(platform)
        if client is None:
            logger.error(f"Failed to create OAuth client for platform: {platform}")
            return "OAuth client not found", 500
        token = client.authorize_access_token()
        
        # Store token in MongoDB
        store_platform_token(user_id, platform, token)
        
        # Add platform to session data
        if 'connected_platforms' not in session:
            session['connected_platforms'] = []
        
        if platform not in session['connected_platforms']:
            session['connected_platforms'].append(platform)
        
        # Collect platform-specific data
        try:
            # YouTube data collection
            if platform == 'youtube':
                resp = client.get('https://www.googleapis.com/youtube/v3/playlists?part=snippet&mine=true', token=token)
                if resp.status_code == 200:
                    # Process and store the data
                    process_platform_data(user_id, platform, resp.json())
                else:
                    logger.warning(f"Failed to fetch YouTube data: {resp.status_code}")
            
            # Spotify data collection
            elif platform == 'spotify':
                # Get recently played tracks
                resp = client.get('https://api.spotify.com/v1/me/player/recently-played?limit=20', token=token)
                if resp.status_code == 200:
                    # Process and store the data
                    process_platform_data(user_id, platform, resp.json())
                else:
                    logger.warning(f"Failed to fetch Spotify data: {resp.status_code}")
            
            # Reddit data collection
            elif platform == 'reddit':
                # Get user profile data
                resp = client.get('https://oauth.reddit.com/api/v1/me', token=token, 
                                 headers={'User-Agent': 'aboutBrooks/1.0 (by /u/yourredditusername)'})
                if resp.status_code == 200:
                    # Process and store the data
                    process_platform_data(user_id, platform, resp.json())
                else:
                    logger.warning(f"Failed to fetch Reddit data: {resp.status_code}")
            
            # Discord data collection
            elif platform == 'discord':
                # Get user profile data
                resp = client.get('https://discord.com/api/users/@me', token=token)
                if resp.status_code == 200:
                    # Process and store the data
                    process_platform_data(user_id, platform, resp.json())
                else:
                    logger.warning(f"Failed to fetch Discord data: {resp.status_code}")
            
            # Add more platforms as needed...
            
        except Exception as data_err:
            logger.error(f"Error while collecting {platform} data: {str(data_err)}")
            # Continue with the OAuth flow even if data collection fails
        
        session.modified = True
        return redirect(url_for('oauth_index'))
    
    except Exception as e:
        logger.error(f"OAuth callback error for {platform}: {str(e)}")
        return f"Authentication error: {str(e)}", 500

@app.route('/api/platforms')
def platform_data():
    """Get data from all connected social platforms as JSON"""
    try:
        # Initialize response with timestamp and request ID
        request_id = datetime.now().strftime('%Y%m%d%H%M%S') + str(hash(str(session.sid)))[-4:]
        platforms_info = {
            "request_id": request_id,
            "timestamp": datetime.now().isoformat(),
            "connected_platforms": session.get('connected_platforms', []),
            "platform_data": {}
        }
        
        # Check if user has connected platforms
        if 'connected_platforms' not in session or not session['connected_platforms']:
            return jsonify(platforms_info)
        
        # Fetch data for each connected platform
        for platform in session['connected_platforms']:
            if f'{platform}_token' not in session:
                platforms_info["platform_data"][platform] = {
                    "status": "error",
                    "error": "No valid token found"
                }
                continue
                
            platforms_info["platform_data"][platform] = {"status": "connected"}
            
            # Get client and token
            try:
                client = oauth.create_client(platform)
                if client is None:
                    platforms_info["platform_data"][platform].update({
                        "status": "error",
                        "error": "OAuth client not found"
                    })
                    continue
                token = session[f'{platform}_token']
                
                if not token:
                    platforms_info["platform_data"][platform].update({
                        "status": "error",
                        "error": "Empty token"
                    })
                    continue
                
                # Platform-specific data fetching with our robust error handling
                if platform == 'x':
                    success, data, status, error = safe_api_call(
                        client, 'https://api.twitter.com/2/users/me', token)
                    
                    platforms_info["platform_data"][platform].update({
                        "status": "success" if success else "error",
                        "data": data,
                        "status_code": status,
                        "error": error
                    })
                        
                elif platform == 'spotify':
                    # Try recently played first
                    success, recently_played, status, error = safe_api_call(
                        client, 'https://api.spotify.com/v1/me/player/recently-played', token)
                    
                    # Also get profile data as backup
                    profile_success, profile_data, profile_status, profile_error = safe_api_call(
                        client, 'https://api.spotify.com/v1/me', token)
                    
                    # Combine data
                    spotify_data = {}
                    if success:
                        spotify_data["recently_played"] = recently_played
                    if profile_success:
                        spotify_data["profile"] = profile_data
                        
                    platforms_info["platform_data"][platform].update({
                        "status": "success" if (success or profile_success) else "error",
                        "data": spotify_data,
                        "status_code": status,
                        "error": error if not success and not profile_success else None
                    })
                    
                elif platform == 'reddit':
                    success, data, status, error = safe_api_call(
                        client, 'https://oauth.reddit.com/api/v1/me', token,
                        headers={'User-Agent': 'BrooksChatbot/1.0 (by /u/yourusername)'})
                    
                    platforms_info["platform_data"][platform].update({
                        "status": "success" if success else "error",
                        "data": data,
                        "status_code": status,
                        "error": error
                    })
                    
                elif platform == 'discord':
                    success, data, status, error = safe_api_call(
                        client, 'https://discord.com/api/users/@me', token)
                    
                    platforms_info["platform_data"][platform].update({
                        "status": "success" if success else "error",
                        "data": data,
                        "status_code": status,
                        "error": error
                    })
                
                elif platform == 'youtube':
                    # Get combined YouTube data with robust error handling
                    youtube_data = {
                        "metadata": {
                            "request_id": request_id,
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                    overall_success = False
                    
                    # Channel info
                    channel_success, channel_data, channel_status, channel_error = safe_api_call(
                        client, 'https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics&mine=true', token)
                    
                    if channel_success:
                        youtube_data['channel'] = channel_data
                        overall_success = True
                    else:
                        youtube_data['channel_error'] = {
                            "status_code": channel_status,
                            "error": channel_error
                        }
                    
                    # Try to get watch history (with appropriate error handling)
                    history_success, history_data, history_status, history_error = safe_api_call(
                        client, 'https://www.googleapis.com/youtube/v3/history?maxResults=5', token)
                    
                    if history_success:
                        youtube_data['history'] = history_data
                        overall_success = True
                    else:
                        youtube_data['history_error'] = {
                            "status_code": history_status,
                            "error": history_error
                        }
                    
                    # Get liked videos (with error handling)
                    liked_success, liked_data, liked_status, liked_error = safe_api_call(
                        client, 'https://www.googleapis.com/youtube/v3/videos?part=snippet&myRating=like&maxResults=3', token)
                    
                    if liked_success:
                        youtube_data['liked'] = liked_data
                        overall_success = True
                    else:
                        youtube_data['liked_error'] = {
                            "status_code": liked_status,
                            "error": liked_error
                        }
                    
                    # Get subscriptions (with error handling)
                    subs_success, subs_data, subs_status, subs_error = safe_api_call(
                        client, 'https://www.googleapis.com/youtube/v3/subscriptions?part=snippet&mine=true&maxResults=3', token)
                    
                    if subs_success:
                        youtube_data['subscriptions'] = subs_data
                        overall_success = True
                    else:
                        youtube_data['subscriptions_error'] = {
                            "status_code": subs_status,
                            "error": subs_error
                        }
                    
                    platforms_info["platform_data"][platform].update({
                        "status": "success" if overall_success else "partial_success" if channel_success else "error",
                        "data": youtube_data,
                        "status_code": channel_status,
                        "error": None if overall_success else channel_error
                    })
                
                elif platform == 'facebook':
                    success, data, status, error = safe_api_call(
                        client, 'https://graph.facebook.com/v12.0/me?fields=name,id', token)
                    
                    platforms_info["platform_data"][platform].update({
                        "status": "success" if success else "error",
                        "data": data,
                        "status_code": status,
                        "error": error
                    })
                
                elif platform == 'instagram':
                    success, data, status, error = safe_api_call(
                        client, 'https://graph.instagram.com/me?fields=username,account_type', token)
                    
                    platforms_info["platform_data"][platform].update({
                        "status": "success" if success else "error",
                        "data": data,
                        "status_code": status,
                        "error": error
                    })
                
                elif platform == 'linkedin':
                    success, data, status, error = safe_api_call(
                        client, 'https://api.linkedin.com/v2/me', token)
                    
                    platforms_info["platform_data"][platform].update({
                        "status": "success" if success else "error",
                        "data": data,
                        "status_code": status,
                        "error": error
                    })
                
                elif platform == 'tiktok':
                    success, data, status, error = safe_api_call(
                        client, 'https://open.tiktokapis.com/v2/user/info/', token)
                    
                    platforms_info["platform_data"][platform].update({
                        "status": "success" if success else "error",
                        "data": data,
                        "status_code": status,
                        "error": error
                    })
                
                else:
                    # Unsupported platform
                    platforms_info["platform_data"][platform].update({
                        "status": "error",
                        "error": "Platform not supported by API"
                    })
                
            except Exception as e:
                error_type = type(e).__name__
                error_message = str(e)
                print(f"Error processing platform {platform}: {error_type} - {error_message}")
                
                # Log full error details
                import traceback
                traceback.print_exc()
                
                platforms_info["platform_data"][platform].update({
                    "status": "error",
                    "error": f"{error_type}: {error_message}",
                    "error_type": error_type
                })
        
        # Add summary info
        success_count = sum(1 for p in platforms_info["platform_data"].values() 
                          if p.get("status") == "success")
        error_count = sum(1 for p in platforms_info["platform_data"].values() 
                         if p.get("status") == "error")
        partial_count = sum(1 for p in platforms_info["platform_data"].values() 
                           if p.get("status") == "partial_success")
        
        platforms_info["summary"] = {
            "total_platforms": len(platforms_info["connected_platforms"]),
            "success_count": success_count,
            "error_count": error_count,
            "partial_success_count": partial_count,
            "success_rate": f"{(success_count + 0.5 * partial_count) / max(1, len(platforms_info['connected_platforms'])) * 100:.1f}%"
        }
        
        return jsonify(platforms_info)
    except Exception as e:
        error_type = type(e).__name__
        error_message = str(e)
        print(f"Global error in platform_data: {error_type} - {error_message}")
        
        # Log full error details
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "error": f"{error_type}: {error_message}",
            "error_type": error_type,
            "status": "error",
            "timestamp": datetime.now().isoformat()
        }), 500

# Consent endpoint (for frontend to toggle)
@app.route('/set-consent', methods=['POST'])
def set_consent():
    # Set both consent and age verification with the same checkbox
    consent_value = request.json.get('consent', False) if request.json else False
    session['consent'] = consent_value
    session['age_verified'] = consent_value  # Age verification is now part of the consent checkbox
    session.modified = True
    return {'status': 'success'}

@app.route('/chat', methods=['POST'])
def chat():
    try:
        # Initialize session if not already set
        if 'history' not in session:
            print("Initializing new session")
            session['history'] = []

        # Get user ID from request for MongoDB
        user_id, user = get_or_create_user(request)
        
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

            # Log this interaction in MongoDB
            log_chat_interaction(user_id, user_input, welcome_message)

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
                photo_context += f"- {photo['title']}: {photo['description']}. Filename: {photo['filename']}\n"
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
        
        # Get the base system prompt
        system_prompt = get_system_prompt(enriched_profile)
        
        # Add photo context to the system prompt dynamically
        if photo_context:
            system_prompt += f"\n\n# Relevant Photos for This Query\n{photo_context}\n"
        
        # Enhance the prompt with user data from MongoDB
        system_prompt = enhance_prompt_with_user_data(user_id, system_prompt)

        # Add social platform data if available
        social_data = ""
        # Check if we're using a connected social platform
        if 'connected_platforms' in session and session['connected_platforms']:
            social_data = "\n\n# User Social Data\n"
            for platform in session['connected_platforms']:
                if f'{platform}_token' in session:
                    social_data += f"- Connected to {platform.capitalize()}\n"
                    # Fetch platform-specific data
                    try:
                        client = oauth.create_client(platform)
                        if client is None:
                            logger.error(f"Failed to create OAuth client for platform: {platform}")
                            social_data += f"  - Error: OAuth client not found for {platform}\n"
                            continue
                        token = session[f'{platform}_token']
                        
                        if platform == 'x':
                            # Get X (Twitter) data if connected
                            resp = client.get('https://api.twitter.com/2/users/me', token=token)
                            if resp.status_code == 200:
                                twitter_data = resp.json().get('data', {})
                                social_data += f"  - X Username: @{twitter_data.get('username', 'unknown')}\n"
                        
                        elif platform == 'spotify':
                            # Get Spotify data if connected
                            resp = client.get('https://api.spotify.com/v1/me/player/recently-played', token=token)
                            if resp.status_code == 200:
                                spotify_data = resp.json().get('items', [])
                                if spotify_data:
                                    track = spotify_data[0]['track']
                                    social_data += f"  - Recently played: {track.get('name', 'unknown')} by {track.get('artists', [{}])[0].get('name', 'unknown')}\n"
                        
                        elif platform == 'reddit':
                            # Get Reddit data if connected
                            resp = client.get('https://oauth.reddit.com/api/v1/me', token=token, headers={'User-Agent': 'BrooksChatbot/1.0 (by /u/yourusername)'})
                            if resp.status_code == 200:
                                user_data = resp.json()
                                social_data += f"  - Reddit Username: u/{user_data.get('name', 'unknown')}\n"
                                social_data += f"  - Karma: {user_data.get('total_karma', 0)}\n"
                        
                        elif platform == 'discord':
                            # Get Discord data if connected
                            resp = client.get('https://discord.com/api/users/@me', token=token)
                            if resp.status_code == 200:
                                user_data = resp.json()
                                social_data += f"  - Discord Username: {user_data.get('username', 'unknown')}\n"
                                if 'discriminator' in user_data and user_data['discriminator'] != '0':
                                    social_data += f"  - Discord Tag: #{user_data.get('discriminator', '0000')}\n"
                    
                    except Exception as e:
                        print(f"Error fetching social data for {platform}: {str(e)}")
            
            # If we have platform data, include it in the system prompt
            if social_data:
                system_prompt += social_data

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
            response = None
            error_occurred = False
            default_response = ""
            
            if anthropic_client is not None:
                try:
                    # Ensure messages are properly typed
                    # Only convert if messages is a list of dicts and not already MessageParam objects
                    if messages and isinstance(messages, list) and isinstance(messages[0], dict):
                        typed_messages = []
                        for msg in messages:
                            if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                                # Ensure role is either 'user' or 'assistant'
                                role = msg["role"]
                                # Cast to allowed roles
                                if role not in ('user', 'assistant'):
                                    role = 'user' if role == 'human' else 'assistant'
                                typed_messages.append(MessageParam(role=role, content=msg["content"]))
                            else:
                                # Skip invalid messages
                                continue
                    else:
                        typed_messages = messages
                        
                    response = anthropic_client.messages.create(
                        model="claude-3-5-sonnet-20241022",  # Updated to newer model
                        system=system_prompt,
                        messages=typed_messages,
                        max_tokens=4000,  # Increased from 1500 to 4000
                        temperature=0.7
                    )
                    print("\nAPI call successful!")
                except Exception as e:
                    print(f"Error calling Anthropic API: {str(e)}")
                    error_occurred = True
                    # Set a default error response
                    default_response = "I'm sorry, there was an error processing your request. Please try again later."
            else:
                print("Anthropic client is not initialized")
                error_occurred = True
                # Set a default error response
                default_response = "I'm sorry, the AI service is currently unavailable. Please try again later."
            
            # Only print response info if we got a valid response
            if response is not None:
                print(f"Response type: {type(response)}")
                print(f"Response attributes: {dir(response)[:10]}...")
            
            # Get response text safely with type checking
            assistant_response = default_response if error_occurred else ""
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

            # Log the chat interaction in MongoDB
            log_chat_interaction(user_id, user_input, assistant_response)
                
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
                    last_message = messages[-1]
                    if isinstance(last_message, dict):
                        print(f"Last message role: {last_message.get('role', 'unknown')}")
                        content_preview = str(last_message.get('content', ''))[:50]
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
        elif "database" in error_str or "mongo" in error_str:
            # Database connection issues
            user_error_message = "There was an issue with our database. Your message was received but couldn't be stored."
            # Continue without database features

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
        models = anthropic_client.models.list() if anthropic_client else None
        model_names = [
            model.id for model in models.data] if models and hasattr(
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
        print(f"Client type: {type(anthropic_client)}")
        print(f"Client API base URL: {anthropic_client.base_url if anthropic_client and hasattr(anthropic_client, 'base_url') else 'unknown'}")
        
        # Make API call
        print("Making test API call...")
        response = None
        if anthropic_client is not None:
            # Ensure messages are properly typed
            # Only convert if messages is a list of dicts and not already MessageParam objects
            if messages and isinstance(messages, list) and isinstance(messages[0], dict):
                typed_messages = []
                for msg in messages:
                    if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                        # Ensure role is either 'user' or 'assistant'
                        role = msg["role"]
                        # Cast to allowed roles
                        if role not in ('user', 'assistant'):
                            role = 'user' if role == 'human' else 'assistant'
                        typed_messages.append(MessageParam(role=role, content=msg["content"]))
                    else:
                        # Skip invalid messages
                        continue
            else:
                typed_messages = messages
                
            response = anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",  # Updated model
                system="Please respond with only the word 'Connected'",
                messages=typed_messages,
                max_tokens=10
            )
        else:
            print("ERROR: Anthropic client is not initialized")
        
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
def simple_chat_endpoint():
    """Simplified chat endpoint for testing without sessions"""
    try:
        data = request.get_json()
        user_input = data.get('user_input', '')

        print(f"Received user input: {user_input}")

        # Get simple system prompt
        simple_system = "You are a helpful assistant for Brooks. Keep your responses brief and friendly."
        
        # Optionally add social data if requested in the query
        if 'social' in user_input.lower() or 'platform' in user_input.lower():
            try:
                social_data = get_all_connected_platforms_data(session, oauth)
                if social_data:
                    simple_system += social_data
            except Exception as social_err:
                print(f"Error including social data: {str(social_err)}")

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
            print(f"Client instance type: {type(anthropic_client)}")
            # Safely get client attributes
            client_attrs = dir(anthropic_client) if anthropic_client else []
            attr_preview = client_attrs[:10] if client_attrs else []
            print(f"Client attributes: {attr_preview}...")
            
            response = None
            if anthropic_client is not None:
                # Ensure messages are properly typed
                # Only convert if messages is a list of dicts and not already MessageParam objects
                if messages and isinstance(messages, list) and isinstance(messages[0], dict):
                    typed_messages = []
                    for msg in messages:
                        if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                            # Ensure role is either 'user' or 'assistant'
                            role = msg["role"]
                            # Cast to allowed roles
                            if role not in ('user', 'assistant'):
                                role = 'user' if role == 'human' else 'assistant'
                            typed_messages.append(MessageParam(role=role, content=msg["content"]))
                        else:
                            # Skip invalid messages
                            continue
                else:
                    typed_messages = messages
                
                response = anthropic_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    system=simple_system,
                    messages=typed_messages,
                    max_tokens=4000,
                    temperature=0.7
                )
            else:
                print("ERROR: Anthropic client is not initialized")

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
                    'response_length': len(assistant_response) if assistant_response else 0,
                    'social_data_included': 'social' in simple_system.lower()
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
    
    # 2. Check Anthropic client initialization
    client_initialized = False
    client_type = str(type(anthropic_client)) if anthropic_client is not None else "NoneType"
    try:
        if anthropic_client is not None:
            client_attrs = dir(anthropic_client)
            client_initialized = "messages" in client_attrs and hasattr(anthropic_client, "api_key")
        else:
            client_error = "Anthropic client is None"
    except Exception as e:
        client_error = str(e)
    
    results["checks"]["anthropic_client_initialization"] = {
        "status": "pass" if client_initialized else "fail",
        "details": f"Client type: {client_type}",
        "error": client_error if not client_initialized and 'client_error' in locals() else None
    }
    
    # Also check MongoDB client
    mongodb_initialized = False
    mongodb_type = str(type(mongodb_client)) if mongodb_client is not None else "NoneType"
    try:
        if mongodb_client is not None:
            mongodb_initialized = True
            mongodb_status = "Connected"
        else:
            mongodb_error = "MongoDB client is None"
            mongodb_status = "Not connected"
    except Exception as e:
        mongodb_error = str(e)
        mongodb_status = f"Error: {str(e)}"
    
    results["checks"]["mongodb_initialization"] = {
        "status": "pass" if mongodb_initialized else "fail",
        "details": f"MongoDB client type: {mongodb_type}, Status: {mongodb_status}",
        "error": mongodb_error if not mongodb_initialized and 'mongodb_error' in locals() else None
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
        response = None
        if anthropic_client is not None:
            # Convert messages to the correct type - role must be 'user' or 'assistant'
            typed_messages = []
            for msg in test_messages:
                role = msg["role"]
                # Cast to allowed roles
                if role not in ('user', 'assistant'):
                    role = 'user' if role == 'human' else 'assistant'
                typed_messages.append(MessageParam(role=role, content=msg["content"]))
            
            response = anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                system="Test",
                messages=typed_messages,
                max_tokens=5
            )
        else:
            raise Exception("Anthropic client is not initialized")
        
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
    
    # 6. Check OAuth client registration
    oauth_status = False
    registered_platforms = []
    try:
        for platform in PLATFORMS:
            client = oauth.create_client(platform)
            if client is None:
                logger.error(f"Failed to create OAuth client for platform: {platform}")
                continue
            registered_platforms.append(platform)
        oauth_status = len(registered_platforms) > 0
    except Exception as e:
        oauth_error = str(e)
        
    results["checks"]["oauth_setup"] = {
        "status": "pass" if oauth_status else "fail",
        "details": f"OAuth registered platforms: {', '.join(registered_platforms) if registered_platforms else 'none'}",
        "error": oauth_error if not oauth_status and 'oauth_error' in locals() else None
    }
    
    # 7. Collect system info
    import sys
    import platform
    
    results["system_info"] = {
        "python_version": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "python_path": sys.executable
    }
    
    # Calculate overall status
    critical_checks = ["api_key_format", "anthropic_client_initialization", "internet_connectivity"]
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

# Add explicit routes for static assets
@app.route('/styles.css')
def serve_css():
    return send_from_directory('static', 'styles.css')

@app.route('/script.js')
def serve_js():
    return send_from_directory('static', 'script.js')

@app.route('/privacy')
def privacy_policy():
    return send_from_directory('static', 'PrivacyStatement.html')


# For local development
# Using port 5001 to avoid conflict with AirPlay Receiver
if __name__ == '__main__':
    # Run the app locally, allowing external access
    app.run(debug=True, port=5001, host='0.0.0.0')

# This is needed for Vercel deployment
application = app