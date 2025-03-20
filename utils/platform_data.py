# utils/platform_data.py
import logging
import datetime
import re
from typing import Dict, List, Any, Optional, Union

# Import database functions
from utils.db import (
    youtube_data, spotify_data, reddit_data, discord_data,
    add_user_interest, get_platform_token
)

# Set up logging
logger = logging.getLogger(__name__)

# YouTube data collection and processing
def process_youtube_data(user_id: str, api_data: Dict[str, Any]) -> bool:
    """Process and store YouTube data from API response"""
    try:
        # Check if we have data to process
        if not api_data or not isinstance(api_data, dict):
            logger.warning(f"Invalid YouTube data format for user {user_id[:8]}")
            return False
        
        # Extract playlist data
        playlists = api_data.get('items', [])
        
        # Extract video categories/interests
        categories = []
        playlist_titles = []
        for playlist in playlists:
            if 'snippet' in playlist:
                title = playlist['snippet'].get('title', '')
                description = playlist['snippet'].get('description', '')
                playlist_titles.append(title)
                
                # Add to categories if relevant keywords appear
                for category in [
                    'tech', 'music', 'gaming', 'sports', 'education', 
                    'finance', 'travel', 'cooking', 'fitness', 'science'
                ]:
                    if category.lower() in title.lower() or category.lower() in description.lower():
                        categories.append(category)
        
        # Record specific interests based on playlist names
        interests = extract_interests_from_youtube(playlist_titles)
        
        # Prepare document
        youtube_doc = {
            'user_id': user_id,
            'collected_at': datetime.datetime.now(),
            'playlist_count': len(playlists),
            'categories': list(set(categories)),  # Remove duplicates
            'interests': interests,
            'has_playlists': len(playlists) > 0,
            'raw_data_sample': str(api_data)[:1000] if api_data else None  # Store sample for debugging
        }
        
        # Insert or update
        existing = youtube_data.find_one({'user_id': user_id})
        if existing:
            youtube_data.update_one(
                {'_id': existing['_id']},
                {'$set': youtube_doc}
            )
        else:
            youtube_data.insert_one(youtube_doc)
        
        # Add interests to user profile
        for interest in interests:
            confidence = 0.7  # Medium-high confidence
            add_user_interest(user_id, interest, 'youtube', confidence)
        
        logger.info(f"Processed YouTube data for user {user_id[:8]} - Found {len(interests)} interests")
        return True
    
    except Exception as e:
        logger.error(f"Error processing YouTube data: {str(e)}")
        return False

def extract_interests_from_youtube(playlist_titles: List[str]) -> List[str]:
    """Extract specific interests from YouTube playlist titles"""
    interests = []
    
    # Common interest keywords to look for
    interest_keywords = {
        'music': ['music', 'songs', 'playlist', 'album', 'artist', 'band'],
        'gaming': ['gaming', 'game', 'playthrough', 'minecraft', 'fortnite', 'gameplay'],
        'tech': ['tech', 'technology', 'programming', 'coding', 'computer', 'software', 'hardware'],
        'sports': ['sports', 'football', 'basketball', 'soccer', 'baseball', 'nfl', 'nba', 'fitness'],
        'education': ['education', 'learning', 'tutorial', 'course', 'lecture', 'how to'],
        'finance': ['finance', 'investing', 'money', 'stock', 'crypto', 'bitcoin', 'business'],
        'cooking': ['cooking', 'recipe', 'food', 'baking', 'kitchen', 'chef'],
        'travel': ['travel', 'vacation', 'trip', 'destination', 'tour'],
        'art': ['art', 'painting', 'drawing', 'creative', 'design'],
        'science': ['science', 'physics', 'chemistry', 'biology', 'astronomy'],
    }
    
    # Check each playlist title for keywords
    for title in playlist_titles:
        title_lower = title.lower()
        for interest, keywords in interest_keywords.items():
            if any(keyword in title_lower for keyword in keywords):
                interests.append(interest)
                break
    
    return list(set(interests))  # Remove duplicates

# Spotify data collection and processing
def process_spotify_data(user_id: str, api_data: Dict[str, Any]) -> bool:
    """Process and store Spotify data from API response"""
    try:
        # Check if we have data to process
        if not api_data or not isinstance(api_data, dict):
            logger.warning(f"Invalid Spotify data format for user {user_id[:8]}")
            return False
        
        # Extract recently played tracks
        tracks = api_data.get('items', [])
        
        # Process tracks to find artists and genres
        artists = []
        track_names = []
        
        for track_item in tracks:
            if 'track' in track_item:
                track = track_item['track']
                
                # Get track name
                if 'name' in track:
                    track_names.append(track['name'])
                
                # Get artists
                if 'artists' in track:
                    for artist in track['artists']:
                        if 'name' in artist:
                            artists.append(artist['name'])
        
        # Extract interests based on music
        music_interests = extract_interests_from_spotify(artists, track_names)
        
        # Prepare document
        spotify_doc = {
            'user_id': user_id,
            'collected_at': datetime.datetime.now(),
            'track_count': len(track_names),
            'artists': list(set(artists)),  # Remove duplicates
            'interests': music_interests,
            'raw_data_sample': str(api_data)[:1000] if api_data else None  # Store sample for debugging
        }
        
        # Insert or update
        existing = spotify_data.find_one({'user_id': user_id})
        if existing:
            spotify_data.update_one(
                {'_id': existing['_id']},
                {'$set': spotify_doc}
            )
        else:
            spotify_data.insert_one(spotify_doc)
        
        # Add interests to user profile
        for interest in music_interests:
            confidence = 0.8  # High confidence from music tastes
            add_user_interest(user_id, interest, 'spotify', confidence)
        
        logger.info(f"Processed Spotify data for user {user_id[:8]} - Found {len(music_interests)} interests")
        return True
    
    except Exception as e:
        logger.error(f"Error processing Spotify data: {str(e)}")
        return False

def extract_interests_from_spotify(artists: List[str], track_names: List[str]) -> List[str]:
    """Extract interests from Spotify listening habits"""
    interests = []
    
    # Common genre mappings
    genre_artists = {
        'rock': ['queen', 'led zeppelin', 'ac/dc', 'rolling stones', 'nirvana', 'metallica'],
        'pop': ['taylor swift', 'ariana grande', 'ed sheeran', 'justin bieber', 'katy perry'],
        'rap': ['drake', 'kendrick lamar', 'eminem', 'kanye west', 'j. cole', 'travis scott'],
        'indie': ['arctic monkeys', 'tame impala', 'vampire weekend', 'bon iver', 'the strokes'],
        'classical': ['mozart', 'beethoven', 'bach', 'chopin', 'debussy'],
        'jazz': ['miles davis', 'john coltrane', 'louis armstrong', 'ella fitzgerald'],
        'electronic': ['daft punk', 'deadmau5', 'calvin harris', 'the chemical brothers'],
        'country': ['johnny cash', 'dolly parton', 'kenny rogers', 'garth brooks'],
        'r&b': ['beyoncé', 'the weeknd', 'frank ocean', 'usher', 'alicia keys']
    }
    
    # Check for genre matches in artists
    artists_lower = [artist.lower() for artist in artists]
    for genre, genre_artists_list in genre_artists.items():
        if any(artist in artists_lower for artist in genre_artists_list):
            interests.append(f"{genre} music")
    
    # Add generic music interest if we have tracks but no specific genre
    if track_names and not interests:
        interests.append('music')
    
    return list(set(interests))  # Remove duplicates

# Reddit data collection and processing
def process_reddit_data(user_id: str, api_data: Dict[str, Any]) -> bool:
    """Process and store Reddit data from API response"""
    try:
        # Check if we have data to process
        if not api_data or not isinstance(api_data, dict):
            logger.warning(f"Invalid Reddit data format for user {user_id[:8]}")
            return False
        
        # Extract basic user info
        username = api_data.get('name', 'unknown')
        karma = api_data.get('total_karma', 0)
        account_created = api_data.get('created_utc', 0)
        
        # Convert Unix timestamp to datetime
        if account_created:
            account_created = datetime.datetime.fromtimestamp(account_created)
        else:
            account_created = datetime.datetime.now()
        
        # Calculate account age in days
        account_age_days = (datetime.datetime.now() - account_created).days
        
        # For a complete integration, we would need to make additional API calls
        # to get the user's subscribed subreddits or post history
        subreddits = []  # This would be populated with actual data in a full implementation
        
        # Extract interests based on Reddit activity
        reddit_interests = extract_interests_from_reddit(subreddits)
        
        # Prepare document
        reddit_doc = {
            'user_id': user_id,
            'collected_at': datetime.datetime.now(),
            'username': username,
            'karma': karma,
            'account_age_days': account_age_days,
            'subreddits': subreddits,
            'interests': reddit_interests,
            'raw_data_sample': str(api_data)[:1000] if api_data else None  # Store sample for debugging
        }
        
        # Insert or update
        existing = reddit_data.find_one({'user_id': user_id})
        if existing:
            reddit_data.update_one(
                {'_id': existing['_id']},
                {'$set': reddit_doc}
            )
        else:
            reddit_data.insert_one(reddit_doc)
        
        # Add interests to user profile
        for interest in reddit_interests:
            confidence = 0.9  # Very high confidence from Reddit subscriptions
            add_user_interest(user_id, interest, 'reddit', confidence)
        
        logger.info(f"Processed Reddit data for user {user_id[:8]} - Found {len(reddit_interests)} interests")
        return True
    
    except Exception as e:
        logger.error(f"Error processing Reddit data: {str(e)}")
        return False

def extract_interests_from_reddit(subreddits: List[str]) -> List[str]:
    """Extract interests from Reddit subreddit subscriptions"""
    interests = []
    
    # Map of subreddits to interest categories
    subreddit_mapping = {
        'technology': ['technology', 'tech', 'programming', 'python', 'webdev', 'compsci'],
        'gaming': ['gaming', 'games', 'pcgaming', 'ps5', 'xbox', 'nintendoswitch'],
        'entertainment': ['movies', 'television', 'anime', 'books', 'music'],
        'science': ['science', 'askscience', 'space', 'physics', 'chemistry', 'biology'],
        'finance': ['personalfinance', 'investing', 'stocks', 'wallstreetbets', 'cryptocurrency'],
        'sports': ['sports', 'nfl', 'nba', 'soccer', 'baseball', 'formula1'],
        'fitness': ['fitness', 'running', 'weightlifting', 'bodybuilding', 'nutrition'],
        'food': ['food', 'cooking', 'baking', 'recipes', 'mealprep'],
        'travel': ['travel', 'backpacking', 'solotravel', 'camping', 'hiking'],
        'art': ['art', 'drawing', 'painting', 'design', 'photography']
    }
    
    # Check for interest matches in subreddits
    subreddits_lower = [subreddit.lower() for subreddit in subreddits]
    
    for interest, related_subs in subreddit_mapping.items():
        if any(sub in subreddits_lower for sub in related_subs):
            interests.append(interest)
    
    return list(set(interests))  # Remove duplicates

# Discord data collection and processing
def process_discord_data(user_id: str, api_data: Dict[str, Any]) -> bool:
    """Process and store Discord data from API response"""
    try:
        # Check if we have data to process
        if not api_data or not isinstance(api_data, dict):
            logger.warning(f"Invalid Discord data format for user {user_id[:8]}")
            return False
        
        # Extract basic user info
        username = api_data.get('username', 'unknown')
        discriminator = api_data.get('discriminator', '0000')
        avatar = api_data.get('avatar')
        
        # Format full username
        full_username = f"{username}#{discriminator}" if discriminator != '0' else username
        
        # For a complete integration, additional API calls would be needed
        # to get user's guilds (servers) and their topics
        guilds = []  # This would be populated with actual data in a full implementation
        
        # Extract interests based on Discord activity
        discord_interests = extract_interests_from_discord(guilds)
        
        # Prepare document
        discord_doc = {
            'user_id': user_id,
            'collected_at': datetime.datetime.now(),
            'username': full_username,
            'has_avatar': bool(avatar),
            'guilds': guilds,
            'interests': discord_interests,
            'raw_data_sample': str(api_data)[:1000] if api_data else None  # Store sample for debugging
        }
        
        # Insert or update
        existing = discord_data.find_one({'user_id': user_id})
        if existing:
            discord_data.update_one(
                {'_id': existing['_id']},
                {'$set': discord_doc}
            )
        else:
            discord_data.insert_one(discord_doc)
        
        # Add interests to user profile
        for interest in discord_interests:
            confidence = 0.75  # High confidence from Discord communities
            add_user_interest(user_id, interest, 'discord', confidence)
        
        logger.info(f"Processed Discord data for user {user_id[:8]} - Found {len(discord_interests)} interests")
        return True
    
    except Exception as e:
        logger.error(f"Error processing Discord data: {str(e)}")
        return False

def extract_interests_from_discord(guilds: List[Dict[str, Any]]) -> List[str]:
    """Extract interests from Discord guild memberships"""
    interests = []
    
    # Common guild topics
    guild_keywords = {
        'gaming': ['gaming', 'game', 'play', 'players', 'minecraft', 'fortnite'],
        'technology': ['tech', 'programming', 'coding', 'developers', 'software'],
        'music': ['music', 'musicians', 'producers', 'artists', 'beats'],
        'art': ['art', 'artists', 'drawing', 'creative', 'design'],
        'anime': ['anime', 'manga', 'weeb', 'otaku', 'japan'],
        'education': ['learning', 'students', 'university', 'college', 'school'],
    }
    
    # Extract guild names from guild objects
    guild_names = []
    for guild in guilds:
        if 'name' in guild:
            guild_names.append(guild['name'].lower())
    
    # Match guild names to interests
    for interest, keywords in guild_keywords.items():
        for guild_name in guild_names:
            if any(keyword in guild_name for keyword in keywords):
                interests.append(interest)
                break
    
    return list(set(interests))  # Remove duplicates

# Process data from any platform
def process_platform_data(user_id: str, platform: str, api_data: Dict[str, Any]) -> bool:
    """Process data from a specific platform using the appropriate handler"""
    platform_handlers = {
        'youtube': process_youtube_data,
        'spotify': process_spotify_data,
        'reddit': process_reddit_data,
        'discord': process_discord_data,
        # Add more platforms as they are implemented
    }
    
    if platform in platform_handlers:
        return platform_handlers[platform](user_id, api_data)
    else:
        logger.warning(f"No data processor for platform: {platform}")
        return False