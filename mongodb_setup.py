#!/usr/bin/env python3
"""
MongoDB setup script for aboutBrooks.
This script verifies the MongoDB connection and creates the required collections and indexes.
"""

import os
import sys
import logging
from dotenv import load_dotenv
import pymongo
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("mongodb_setup")

def setup_mongodb():
    """Set up MongoDB collections and indexes"""
    logger.info("Starting MongoDB setup for aboutBrooks")
    
    # Load environment variables
    load_dotenv()
    logger.info("Loaded environment variables")
    
    # Check for MongoDB URI
    mongo_uri = os.environ.get('MONGO_URI')
    if not mongo_uri:
        logger.error("MONGO_URI environment variable not found")
        logger.error("Please add MONGO_URI to your .env file")
        return False
    
    # Connect to MongoDB
    try:
        # Add network connectivity check
        import socket
        logger.info("Testing network connectivity to MongoDB Atlas servers...")
        atlas_hosts = [
            "aboutbrookscluster-shard-00-00.6o6pn.mongodb.net",
            "aboutbrookscluster-shard-00-01.6o6pn.mongodb.net",
            "aboutbrookscluster-shard-00-02.6o6pn.mongodb.net"
        ]
        
        for host in atlas_hosts:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2)
                result = s.connect_ex((host, 27017))
                s.close()
                if result == 0:
                    logger.info(f"Network connection to {host}:27017 succeeded")
                else:
                    logger.warning(f"Network connection to {host}:27017 failed with error code {result}")
            except Exception as socket_err:
                logger.error(f"Socket test to {host} failed: {str(socket_err)}")
                
        logger.info(f"Connecting to MongoDB using URI beginning with: {mongo_uri[:15]}...")
        logger.info("IMPORTANT: Make sure your IP address is allowed in MongoDB Atlas Network Access settings")
        logger.info("See: https://www.mongodb.com/docs/atlas/security/ip-access-list/")
        
        # Try with SSL configurations that might work around TLS issues
        try:
            logger.info("Attempting connection with default settings...")
            client = MongoClient(mongo_uri, serverSelectionTimeoutMS=10000)
        except Exception as conn_err:
            logger.warning(f"Default connection failed: {str(conn_err)}")
            logger.info("Trying alternative SSL settings...")
            
            # Try with tlsAllowInvalidCertificates
            try:
                client = MongoClient(
                    mongo_uri, 
                    serverSelectionTimeoutMS=10000,
                    tlsAllowInvalidCertificates=True
                )
                logger.info("Connected with tlsAllowInvalidCertificates=True")
            except Exception:
                # Fall back to non-SRV connection if all else fails
                logger.warning("SSL settings didn't help, check your Atlas IP access list")
                raise
        
        # Test connection
        client.admin.command('ping')
        logger.info("Successfully connected to MongoDB")
        
        # Set up database
        db = client.aboutBrooks
        logger.info("Using 'aboutBrooks' database")
        
        # Create collections and indexes
        
        # Users collection
        logger.info("Setting up 'users' collection...")
        db.users.create_index("user_id", unique=True)
        logger.info("Created unique index on users.user_id")
        
        # Platform tokens collection
        logger.info("Setting up 'platform_tokens' collection...")
        db.platform_tokens.create_index([("user_id", 1), ("platform", 1)], unique=True)
        logger.info("Created compound index on platform_tokens.user_id and platform_tokens.platform")
        
        # Platform data collections
        for collection_name in ['youtube_data', 'spotify_data', 'reddit_data', 'discord_data']:
            logger.info(f"Setting up '{collection_name}' collection...")
            db[collection_name].create_index("user_id", unique=True)
            logger.info(f"Created unique index on {collection_name}.user_id")
        
        # Chat interactions collection
        logger.info("Setting up 'chat_interactions' collection...")
        db.chat_interactions.create_index([("user_id", 1), ("timestamp", -1)])
        logger.info("Created compound index on chat_interactions.user_id and chat_interactions.timestamp")
        
        # Add TTL index for automatic data cleanup
        logger.info("Setting up TTL indexes for data retention...")
        
        # Users inactive for more than 90 days
        db.users.create_index("last_seen", expireAfterSeconds=7776000)  # 90 days
        logger.info("Created TTL index on users.last_seen (90 days)")
        
        # Chat interactions older than 30 days
        db.chat_interactions.create_index("timestamp", expireAfterSeconds=2592000)  # 30 days
        logger.info("Created TTL index on chat_interactions.timestamp (30 days)")
        
        logger.info("MongoDB setup completed successfully!")
        return True
        
    except ServerSelectionTimeoutError:
        logger.error("Could not connect to MongoDB - server selection timeout")
        logger.error("Please check your MongoDB URI and network connectivity")
        return False
        
    except ConnectionFailure:
        logger.error("Failed to connect to MongoDB")
        logger.error("Please check your MongoDB URI and network settings")
        return False
        
    except Exception as e:
        logger.error(f"Unexpected error during MongoDB setup: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n🔧 MongoDB Setup for aboutBrooks 🔧\n")
    
    # Check for pymongo
    try:
        import pymongo
        print(f"✓ PyMongo is installed (version {pymongo.__version__})")
    except ImportError:
        print("✗ PyMongo is not installed")
        print("Please install it with: pip install pymongo")
        sys.exit(1)
    
    # Run setup
    if setup_mongodb():
        print("\n✅ MongoDB setup completed successfully!")
        print("Your database is now ready to use with aboutBrooks.")
    else:
        print("\n❌ MongoDB setup failed.")
        print("Please check the logs for details.")
        sys.exit(1)