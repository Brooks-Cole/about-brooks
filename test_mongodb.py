#!/usr/bin/env python3
"""
Test script for MongoDB connection and basic operations.
Run this script to verify your MongoDB Atlas configuration.
"""

import os
import sys
import datetime
import json
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_mongodb_connection():
    """Test connection to MongoDB Atlas and perform basic operations"""
    try:
        # Load environment variables
        load_dotenv()
        
        # Check for MongoDB URI
        mongo_uri = os.environ.get('MONGO_URI')
        if not mongo_uri:
            logger.error("No MONGO_URI found in environment variables")
            return False
        
        # Import pymongo (with error handling in case it's not installed)
        try:
            import pymongo
            from pymongo import MongoClient
            from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
            logger.info(f"PyMongo version: {pymongo.__version__}")
        except ImportError:
            logger.error("PyMongo not installed. Install with: pip install pymongo")
            return False
        
        # Connect to MongoDB with timeout
        logger.info(f"Connecting to MongoDB Atlas... URI begins with: {mongo_uri[:20]}...")
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        
        # Verify connection
        logger.info("Testing connection...")
        client.admin.command('ping')
        logger.info("Connection successful!")
        
        # List databases
        dbs = client.list_database_names()
        logger.info(f"Available databases: {dbs}")
        
        # Use aboutBrooks database (creates it if it doesn't exist)
        db = client.aboutBrooks
        logger.info("Using 'aboutBrooks' database")
        
        # List collections
        collections = db.list_collection_names()
        logger.info(f"Existing collections: {collections}")
        
        # Test insertion
        test_doc = {
            'type': 'connection_test',
            'timestamp': datetime.datetime.now(),
            'message': 'Testing MongoDB connection from aboutBrooks',
            'environment': {
                'python': sys.version,
                'platform': sys.platform,
                'mongodb_driver': pymongo.__version__
            }
        }
        
        logger.info("Inserting test document...")
        result = db.test_collection.insert_one(test_doc)
        logger.info(f"Document inserted with ID: {result.inserted_id}")
        
        # Test retrieval
        logger.info("Retrieving document...")
        retrieved = db.test_collection.find_one({'_id': result.inserted_id})
        if retrieved:
            logger.info("Document successfully retrieved")
            # Convert ObjectId to string for JSON serialization
            retrieved['_id'] = str(retrieved['_id'])
            # Convert datetime to string
            retrieved['timestamp'] = retrieved['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            # Pretty print the document
            logger.info(f"Retrieved document:\n{json.dumps(retrieved, indent=2)}")
        else:
            logger.error("Failed to retrieve document")
        
        # Clean up
        logger.info("Cleaning up test document...")
        db.test_collection.delete_one({'_id': result.inserted_id})
        
        # Set up required collections and indexes
        logger.info("Setting up collections and indexes...")
        
        # Users collection
        db.users.create_index("user_id", unique=True)
        logger.info("Created unique index on users.user_id")
        
        # Platform tokens collection
        db.platform_tokens.create_index([("user_id", 1), ("platform", 1)], unique=True)
        logger.info("Created compound index on platform_tokens")
        
        # Platform data collections
        for collection in ['youtube_data', 'spotify_data', 'reddit_data', 'discord_data']:
            db[collection].create_index("user_id", unique=True)
            logger.info(f"Created unique index on {collection}.user_id")
        
        # Chat interactions collection
        db.chat_interactions.create_index([("user_id", 1), ("timestamp", -1)])
        logger.info("Created index on chat_interactions")
        
        logger.info("\n✅ MongoDB connection and setup successful! Your database is ready to use.")
        return True
    
    except ServerSelectionTimeoutError:
        logger.error("❌ Could not connect to MongoDB Atlas - connection timeout")
        logger.error("Please check your network connection and MongoDB Atlas cluster status")
        return False
    
    except ConnectionFailure:
        logger.error("❌ Connection to MongoDB Atlas failed")
        logger.error("Please check your MongoDB URI and network settings")
        return False
    
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def insert_test_user():
    """Insert a test user record with sample interests"""
    try:
        # Import pymongo and utils
        import pymongo
        from pymongo import MongoClient
        from utils.db import get_db_client, users, add_user_interest
        
        # Either use function from utils or create new connection
        try:
            client = get_db_client()
            if not client:
                raise ValueError("Could not get database client from utils")
        except Exception:
            logger.info("Using direct MongoDB connection for test user...")
            mongo_uri = os.environ.get('MONGO_URI')
            client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        
        # Use database
        db = client.aboutBrooks
        
        # Create test user ID
        import hashlib
        test_user_id = hashlib.sha256(f"test_user_{datetime.datetime.now().isoformat()}".encode()).hexdigest()
        
        # Create test user document
        test_user = {
            'user_id': test_user_id,
            'first_seen': datetime.datetime.now(),
            'last_seen': datetime.datetime.now(),
            'visit_count': 1,
            'platforms': ['youtube', 'spotify'],
            'interests': [],
            'is_test_user': True
        }
        
        # Insert user
        logger.info("Inserting test user...")
        result = db.users.insert_one(test_user)
        logger.info(f"Test user inserted with ID: {test_user_id[:8]}...")
        
        # Add some test interests
        test_interests = [
            ('music', 'spotify', 0.9),
            ('gaming', 'youtube', 0.8),
            ('technology', 'youtube', 0.7),
            ('sports', 'reddit', 0.6),
            ('travel', 'instagram', 0.5)
        ]
        
        # Try to use the function from utils
        try:
            for interest, platform, confidence in test_interests:
                add_user_interest(test_user_id, interest, platform, confidence)
            logger.info(f"Added {len(test_interests)} test interests using utils.db functions")
        except Exception as e:
            logger.warning(f"Could not use utils.db.add_user_interest: {str(e)}")
            # Fall back to direct database update
            interest_entries = []
            for interest, platform, confidence in test_interests:
                interest_entries.append({
                    'topic': interest,
                    'added_at': datetime.datetime.now(),
                    'source': platform,
                    'confidence': confidence
                })
            
            db.users.update_one(
                {'user_id': test_user_id},
                {'$set': {'interests': interest_entries}}
            )
            logger.info(f"Added {len(test_interests)} test interests using direct database update")
        
        # Add platform data
        youtube_data = {
            'user_id': test_user_id,
            'collected_at': datetime.datetime.now(),
            'playlist_count': 5,
            'categories': ['gaming', 'technology', 'education'],
            'interests': ['gaming', 'technology'],
            'has_playlists': True,
            'is_test_data': True
        }
        
        spotify_data = {
            'user_id': test_user_id,
            'collected_at': datetime.datetime.now(),
            'track_count': 10,
            'artists': ['Taylor Swift', 'The Weeknd', 'Drake'],
            'interests': ['pop music', 'r&b music'],
            'is_test_data': True
        }
        
        # Insert platform data
        db.youtube_data.insert_one(youtube_data)
        db.spotify_data.insert_one(spotify_data)
        logger.info("Added test platform data")
        
        # Simulate some chat interactions
        chat_messages = [
            "Hello there!",
            "Tell me about Brooks' projects",
            "What kind of music does Brooks like?",
            "Does he have any pets?",
            "What's his investment philosophy?"
        ]
        
        for msg in chat_messages:
            chat_entry = {
                'user_id': test_user_id,
                'timestamp': datetime.datetime.now(),
                'user_message': msg,
                'ai_response': f"This is a simulated AI response to: '{msg}'",
                'message_length': len(msg),
                'response_length': 50,
                'is_test_data': True
            }
            db.chat_interactions.insert_one(chat_entry)
        
        logger.info(f"Added {len(chat_messages)} test chat interactions")
        
        logger.info("\n✅ Test user data created successfully!")
        logger.info(f"Test user ID: {test_user_id}")
        return test_user_id
    
    except Exception as e:
        logger.error(f"❌ Error creating test user: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def run_analytics_test(test_user_id=None):
    """Test analytics functions on the database"""
    try:
        # Import analytics functions
        sys.path.insert(0, '.')  # Ensure current directory is in path
        from utils.analytics import (
            get_platform_usage_stats,
            get_popular_interests,
            get_user_engagement_metrics,
            get_recent_active_users,
            get_dashboard_summary
        )
        
        logger.info("\n=== Running Analytics Tests ===")
        
        # Test platform usage stats
        logger.info("\nTesting platform usage stats...")
        platform_stats = get_platform_usage_stats()
        logger.info(f"Platform stats: {json.dumps(platform_stats, default=str)}")
        
        # Test popular interests
        logger.info("\nTesting popular interests...")
        interests = get_popular_interests()
        logger.info(f"Popular interests: {json.dumps(interests, default=str)}")
        
        # Test user engagement metrics
        logger.info("\nTesting user engagement metrics...")
        metrics = get_user_engagement_metrics()
        logger.info(f"User engagement metrics: {json.dumps(metrics, default=str)}")
        
        # Test recent active users
        logger.info("\nTesting recent active users...")
        recent_users = get_recent_active_users()
        logger.info(f"Recent active users: {json.dumps(recent_users, default=str)}")
        
        # Test dashboard summary
        logger.info("\nTesting dashboard summary...")
        dashboard = get_dashboard_summary()
        logger.info(f"Dashboard summary: {json.dumps(dashboard, default=str)}")
        
        logger.info("\n✅ Analytics tests completed successfully!")
        return True
    
    except Exception as e:
        logger.error(f"❌ Error running analytics tests: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def cleanup_test_data():
    """Remove all test data from the database"""
    try:
        # Load environment variables
        load_dotenv()
        
        # Import pymongo
        from pymongo import MongoClient
        
        # Connect to MongoDB
        mongo_uri = os.environ.get('MONGO_URI')
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        db = client.aboutBrooks
        
        # Clean up test data from all collections
        logger.info("Cleaning up test data...")
        
        # Remove test users
        result = db.users.delete_many({'is_test_user': True})
        logger.info(f"Removed {result.deleted_count} test users")
        
        # Remove test platform data
        for collection in ['youtube_data', 'spotify_data', 'reddit_data', 'discord_data']:
            result = db[collection].delete_many({'is_test_data': True})
            logger.info(f"Removed {result.deleted_count} test records from {collection}")
        
        # Remove test chat interactions
        result = db.chat_interactions.delete_many({'is_test_data': True})
        logger.info(f"Removed {result.deleted_count} test chat interactions")
        
        logger.info("✅ Test data cleanup completed successfully!")
        return True
    
    except Exception as e:
        logger.error(f"❌ Error cleaning up test data: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n🌟 MongoDB Atlas Connection Test for aboutBrooks 🌟\n")
    print("This script will test your MongoDB connection and basic operations.\n")
    
    connection_ok = test_mongodb_connection()
    
    if connection_ok:
        # Ask user if they want to insert test data
        print("\nConnection test successful! Would you like to:")
        print("1. Insert test user data and run analytics tests")
        print("2. Clean up any existing test data")
        print("3. Exit without further action")
        
        choice = input("\nEnter your choice (1-3): ")
        
        if choice == '1':
            test_user_id = insert_test_user()
            if test_user_id:
                print("\nTest user created successfully!")
                run_analytics_test(test_user_id)
                print("\nWould you like to clean up the test data now?")
                cleanup = input("Clean up test data? (y/n): ")
                if cleanup.lower() == 'y':
                    cleanup_test_data()
        elif choice == '2':
            cleanup_test_data()
        else:
            print("\nExiting without further action.")
    
    else:
        print("\n❌ MongoDB connection test failed.")
        print("Please check your MongoDB URI and network settings.")