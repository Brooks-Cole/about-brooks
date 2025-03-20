# utils/db.py
import os
import logging
from pymongo import MongoClient, errors
from dotenv import load_dotenv
import datetime
import hashlib
import json
from flask import request

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Load environment variables
load_dotenv()

# Get MongoDB URI from environment variable
MONGO_URI = os.environ.get('MONGO_URI')

# Database connection handling with error recovery
def get_db_client():
    """Get MongoDB client with connection retry logic"""
    try:
        # Create a MongoDB client with connection timeout
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        # Check connection by listing server info
        client.server_info()
        logger.info("Successfully connected to MongoDB Atlas")
        return client
    except errors.ServerSelectionTimeoutError:
        logger.error("Could not connect to MongoDB Atlas - connection timeout")
        return None
    except errors.ConfigurationError:
        logger.error("MongoDB Atlas configuration error - check connection string")
        return None
    except Exception as e:
        logger.error(f"Unexpected MongoDB connection error: {str(e)}")
        return None

# Create a MongoDB client
client = get_db_client()

# Initialize database and collections if connection successful
if client:
    # Get database
    db = client.aboutBrooks

    # Collection references
    users = db.users
    platform_tokens = db.platform_tokens
    youtube_data = db.youtube_data
    spotify_data = db.spotify_data
    reddit_data = db.reddit_data
    discord_data = db.discord_data
    chat_interactions = db.chat_interactions
    
    # Create indexes for better query performance
    try:
        # Create unique index on user_id for users collection
        users.create_index("user_id", unique=True)
        
        # Compound index for platform tokens
        platform_tokens.create_index([("user_id", 1), ("platform", 1)], unique=True)
        
        # Indexes for platform-specific collections
        youtube_data.create_index("user_id", unique=True)
        spotify_data.create_index("user_id", unique=True)
        reddit_data.create_index("user_id", unique=True)
        discord_data.create_index("user_id", unique=True)
        
        # Index for chat interactions
        chat_interactions.create_index([("user_id", 1), ("timestamp", -1)])
        
        logger.info("MongoDB indexes created successfully")
    except Exception as e:
        logger.error(f"Error creating MongoDB indexes: {str(e)}")
else:
    # Define dummy collections for graceful degradation
    # This allows the application to run even if MongoDB is unavailable
    logger.warning("Using in-memory fallback for database collections")
    
    class DummyCollection:
        """Mock collection that logs operations but doesn't persist data"""
        def __init__(self, name):
            self.name = name
            self.data = []
        
        def insert_one(self, document):
            logger.info(f"[MOCK DB] Would insert into {self.name}: {json.dumps(document, default=str)[:100]}...")
            return type('obj', (object,), {'inserted_id': 'mock_id'})
        
        def find_one(self, query):
            logger.info(f"[MOCK DB] Would query {self.name}: {json.dumps(query, default=str)}")
            return None
        
        def update_one(self, query, update, upsert=False):
            logger.info(f"[MOCK DB] Would update in {self.name}: {json.dumps(query, default=str)} → {json.dumps(update, default=str)[:100]}...")
            return type('obj', (object,), {'modified_count': 0})
        
        def create_index(self, keys, **kwargs):
            if isinstance(keys, list):
                key_str = ', '.join(f"{k[0]}: {k[1]}" for k in keys)
            else:
                key_str = keys
            logger.info(f"[MOCK DB] Would create index on {self.name}: {key_str}")
            return 'mock_index'
    
    # Create dummy collections
    db = type('obj', (object,), {})
    users = DummyCollection('users')
    platform_tokens = DummyCollection('platform_tokens')
    youtube_data = DummyCollection('youtube_data')
    spotify_data = DummyCollection('spotify_data')
    reddit_data = DummyCollection('reddit_data')
    discord_data = DummyCollection('discord_data')
    chat_interactions = DummyCollection('chat_interactions')

# User identification functions
def get_user_identifier(request_obj=None):
    """Generate a stable user identifier from request information"""
    if request_obj is None and 'request' in globals():
        # Use global Flask request object if available
        request_obj = request
    
    if request_obj is None:
        logger.warning("No request object available for user identification")
        return hashlib.sha256(str(datetime.datetime.now().timestamp()).encode()).hexdigest()
    
    # Get IP address (with proxy handling)
    ip = request_obj.remote_addr
    forwarded_for = request_obj.headers.get('X-Forwarded-For')
    if forwarded_for and isinstance(forwarded_for, str):
        ip = forwarded_for.split(',')[0].strip()
    
    # Add user agent for more uniqueness
    user_agent = request_obj.headers.get('User-Agent', '')
    
    # Create a hash using both pieces of information
    salt = os.environ.get('HASH_SALT', 'aboutBrooks2025')
    data = f"{ip}:{user_agent}:{salt}"
    
    # Generate hash
    return hashlib.sha256(data.encode()).hexdigest()

def get_or_create_user(request_obj=None):
    """Get existing user or create new one"""
    user_id = get_user_identifier(request_obj)
    
    try:
        # Try to find existing user
        user = users.find_one({'user_id': user_id})
        
        # If user doesn't exist, create new record
        if not user:
            logger.info(f"Creating new user record for {user_id[:8]}...")
            user = {
                'user_id': user_id,
                'first_seen': datetime.datetime.now(),
                'last_seen': datetime.datetime.now(),
                'visit_count': 1,
                'platforms': [],
                'interests': [],
                'referrer': request_obj.referrer if request_obj else None,
                'is_mobile': _is_mobile_user_agent(request_obj.headers.get('User-Agent', '')) if request_obj else False
            }
            users.insert_one(user)
        else:
            # Update existing user's last seen time and visit count
            logger.debug(f"Updating existing user record for {user_id[:8]}...")
            users.update_one(
                {'user_id': user_id},
                {
                    '$set': {'last_seen': datetime.datetime.now()},
                    '$inc': {'visit_count': 1}
                }
            )
        
        return user_id, user
    except Exception as e:
        logger.error(f"Error in get_or_create_user: {str(e)}")
        return user_id, {'user_id': user_id, 'error': str(e)}

def _is_mobile_user_agent(user_agent):
    """Detect if the user agent is from a mobile device"""
    mobile_indicators = ['mobile', 'android', 'iphone', 'ipad', 'ipod', 'blackberry', 'windows phone']
    user_agent_lower = user_agent.lower()
    return any(indicator in user_agent_lower for indicator in mobile_indicators)

# OAuth token storage functions
def store_platform_token(user_id, platform, token_data):
    """Store OAuth tokens securely"""
    try:
        # Check if token for this platform already exists
        existing = platform_tokens.find_one({
            'user_id': user_id,
            'platform': platform
        })
        
        # Prepare token document
        token_doc = {
            'user_id': user_id,
            'platform': platform,
            'token_data': token_data,
            'updated_at': datetime.datetime.now()
        }
        
        # Update user's platforms list
        users.update_one(
            {'user_id': user_id},
            {'$addToSet': {'platforms': platform}}
        )
        
        # Insert or update token
        if existing:
            platform_tokens.update_one(
                {'_id': existing['_id']},
                {'$set': token_doc}
            )
            logger.info(f"Updated token for user {user_id[:8]} on platform {platform}")
        else:
            platform_tokens.insert_one(token_doc)
            logger.info(f"Stored new token for user {user_id[:8]} on platform {platform}")
        
        return True
    except Exception as e:
        logger.error(f"Error storing platform token: {str(e)}")
        return False

def get_platform_token(user_id, platform):
    """Retrieve stored token data"""
    try:
        token = platform_tokens.find_one({
            'user_id': user_id,
            'platform': platform
        })
        
        return token['token_data'] if token else None
    except Exception as e:
        logger.error(f"Error retrieving platform token: {str(e)}")
        return None

def get_connected_platforms(user_id):
    """Get list of platforms a user has connected"""
    try:
        user = users.find_one({'user_id': user_id})
        if user and 'platforms' in user:
            return user['platforms']
        return []
    except Exception as e:
        logger.error(f"Error retrieving connected platforms: {str(e)}")
        return []

# User interest tracking
def add_user_interest(user_id, interest, source_platform=None, confidence=1.0):
    """Add an interest to user's profile with source and confidence score"""
    try:
        # Prepare interest entry
        interest_entry = {
            'topic': interest.lower().strip(),
            'added_at': datetime.datetime.now(),
            'source': source_platform,
            'confidence': float(confidence)  # 0.0 to 1.0
        }
        
        # Add to user's interests array if not already present with same topic
        result = users.update_one(
            {
                'user_id': user_id,
                'interests.topic': {'$ne': interest_entry['topic']}
            },
            {'$push': {'interests': interest_entry}}
        )
        
        # If interest already exists, update its confidence if new confidence is higher
        if result.modified_count == 0:
            users.update_one(
                {
                    'user_id': user_id,
                    'interests.topic': interest_entry['topic'],
                    'interests.confidence': {'$lt': interest_entry['confidence']}
                },
                {
                    '$set': {
                        'interests.$.confidence': interest_entry['confidence'],
                        'interests.$.source': source_platform,
                        'interests.$.added_at': interest_entry['added_at']
                    }
                }
            )
        
        return True
    except Exception as e:
        logger.error(f"Error adding user interest: {str(e)}")
        return False

def get_user_interests(user_id, min_confidence=0.2, limit=10):
    """Get user's interests ordered by confidence score"""
    try:
        user = users.find_one({'user_id': user_id})
        if not user or 'interests' not in user:
            return []
        
        # Filter by confidence and sort by highest confidence
        interests = [i for i in user['interests'] if i.get('confidence', 0) >= min_confidence]
        interests.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        
        # Return limited results
        return interests[:limit]
    except Exception as e:
        logger.error(f"Error retrieving user interests: {str(e)}")
        return []

# Logging chat interactions
def log_chat_interaction(user_id, user_message, ai_response):
    """Log a chat interaction between user and AI"""
    try:
        interaction = {
            'user_id': user_id,
            'timestamp': datetime.datetime.now(),
            'user_message': user_message,
            'ai_response': ai_response,
            'message_length': len(user_message),
            'response_length': len(ai_response)
        }
        
        chat_interactions.insert_one(interaction)
        logger.debug(f"Logged chat interaction for user {user_id[:8]}")
        return True
    except Exception as e:
        logger.error(f"Error logging chat interaction: {str(e)}")
        return False

# Database health check
def check_db_connection():
    """Verify database connection is working"""
    if client is None:
        return False
    
    try:
        # Ping the database
        client.admin.command('ping')
        return True
    except Exception:
        return False