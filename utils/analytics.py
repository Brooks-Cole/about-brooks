# utils/analytics.py
import logging
import datetime
from collections import Counter
from typing import Dict, List, Any, Optional, Union

# Import database functions
from utils.db import (
    db, users, platform_tokens, youtube_data, spotify_data, 
    reddit_data, discord_data, chat_interactions
)

# Set up logging
logger = logging.getLogger(__name__)

def get_platform_usage_stats() -> List[Dict[str, Any]]:
    """Get statistics on which platforms are most connected"""
    try:
        pipeline = [
            {'$match': {'platforms': {'$exists': True, '$ne': []}}},
            {'$unwind': '$platforms'},
            {'$group': {
                '_id': '$platforms',
                'count': {'$sum': 1}
            }},
            {'$sort': {'count': -1}}
        ]
        
        results = list(users.aggregate(pipeline))
        return results
    except Exception as e:
        logger.error(f"Error getting platform usage stats: {str(e)}")
        return []

def get_popular_interests(min_confidence: float = 0.5) -> List[Dict[str, Any]]:
    """Identify the most common interests across all users"""
    try:
        pipeline = [
            {'$match': {'interests': {'$exists': True, '$ne': []}}},
            {'$unwind': '$interests'},
            {'$match': {'interests.confidence': {'$gte': min_confidence}}},
            {'$group': {
                '_id': '$interests.topic',
                'count': {'$sum': 1},
                'avg_confidence': {'$avg': '$interests.confidence'},
                'sources': {'$addToSet': '$interests.source'}
            }},
            {'$sort': {'count': -1}},
            {'$limit': 20}
        ]
        
        results = list(users.aggregate(pipeline))
        return results
    except Exception as e:
        logger.error(f"Error getting popular interests: {str(e)}")
        return []

def get_user_engagement_metrics() -> Dict[str, Any]:
    """Get metrics on user engagement with the site"""
    try:
        # Calculate time period for active users (last 7 days)
        one_week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
        
        # Get count of total users
        total_users = users.count_documents({})
        
        # Get count of active users in last 7 days
        active_users = users.count_documents({
            'last_seen': {'$gte': one_week_ago}
        })
        
        # Get count of users who have connected at least one platform
        users_with_platforms = users.count_documents({
            'platforms': {'$exists': True, '$ne': []}
        })
        
        # Calculate average platforms per user
        avg_platforms_result = list(users.aggregate([
            {'$match': {'platforms': {'$exists': True}}},
            {'$project': {'platform_count': {'$size': {'$ifNull': ['$platforms', []]}}}}
        ]))
        
        platform_counts = [doc.get('platform_count', 0) for doc in avg_platforms_result]
        avg_platforms = sum(platform_counts) / len(platform_counts) if platform_counts else 0
        
        # Calculate chat interaction metrics
        total_chats = chat_interactions.count_documents({})
        
        # Calculate average messages per user
        chat_counts_per_user = list(chat_interactions.aggregate([
            {'$group': {
                '_id': '$user_id',
                'count': {'$sum': 1}
            }}
        ]))
        
        message_counts = [doc.get('count', 0) for doc in chat_counts_per_user]
        avg_messages = sum(message_counts) / len(message_counts) if message_counts else 0
        
        return {
            'total_users': total_users,
            'active_users_7d': active_users,
            'active_percentage': (active_users / total_users * 100) if total_users > 0 else 0,
            'users_with_platforms': users_with_platforms,
            'platform_connection_rate': (users_with_platforms / total_users * 100) if total_users > 0 else 0,
            'avg_platforms_per_user': avg_platforms,
            'total_chat_interactions': total_chats,
            'avg_messages_per_user': avg_messages,
            'timestamp': datetime.datetime.now()
        }
    except Exception as e:
        logger.error(f"Error getting user engagement metrics: {str(e)}")
        return {
            'error': str(e),
            'timestamp': datetime.datetime.now()
        }

def get_recent_active_users(days: int = 7, limit: int = 10) -> List[Dict[str, Any]]:
    """Get information about recently active users"""
    try:
        # Calculate cutoff date
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
        
        # Find recently active users
        recent_users = list(users.find(
            {'last_seen': {'$gte': cutoff_date}},
            {
                'user_id': 1,
                'first_seen': 1,
                'last_seen': 1,
                'visit_count': 1,
                'platforms': 1,
                'interests': 1
            }
        ).sort('last_seen', -1).limit(limit))
        
        # Process users for display (limit data for privacy)
        sanitized_users = []
        for user in recent_users:
            # Get top interests for this user
            top_interests = []
            if 'interests' in user and user['interests']:
                sorted_interests = sorted(
                    user['interests'], 
                    key=lambda x: x.get('confidence', 0), 
                    reverse=True
                )[:5]
                top_interests = [interest['topic'] for interest in sorted_interests]
            
            sanitized_users.append({
                'user_id': user['user_id'][:8] + '...',  # Only show first 8 chars
                'first_seen': user.get('first_seen'),
                'last_seen': user.get('last_seen'),
                'visit_count': user.get('visit_count', 0),
                'platforms': user.get('platforms', []),
                'platform_count': len(user.get('platforms', [])),
                'top_interests': top_interests,
                'interest_count': len(user.get('interests', []))
            })
        
        return sanitized_users
    except Exception as e:
        logger.error(f"Error getting recent active users: {str(e)}")
        return []

def get_user_activity_over_time(days: int = 30) -> List[Dict[str, Any]]:
    """Get daily user activity metrics over a specified period"""
    try:
        # Calculate start date
        start_date = datetime.datetime.now() - datetime.timedelta(days=days)
        
        # Group interactions by day
        pipeline = [
            {'$match': {'timestamp': {'$gte': start_date}}},
            {'$group': {
                '_id': {
                    'year': {'$year': '$timestamp'},
                    'month': {'$month': '$timestamp'},
                    'day': {'$dayOfMonth': '$timestamp'}
                },
                'interactions': {'$sum': 1},
                'unique_users': {'$addToSet': '$user_id'}
            }},
            {'$project': {
                'date': {
                    '$dateFromParts': {
                        'year': '$_id.year',
                        'month': '$_id.month',
                        'day': '$_id.day'
                    }
                },
                'interactions': 1,
                'unique_users': {'$size': '$unique_users'}
            }},
            {'$sort': {'date': 1}}
        ]
        
        activity = list(chat_interactions.aggregate(pipeline))
        
        # Format for return
        formatted_activity = []
        for day in activity:
            formatted_activity.append({
                'date': day['date'].strftime('%Y-%m-%d'),
                'interactions': day['interactions'],
                'unique_users': day['unique_users']
            })
        
        return formatted_activity
    except Exception as e:
        logger.error(f"Error getting user activity over time: {str(e)}")
        return []

def get_popular_chat_topics() -> List[Dict[str, Any]]:
    """Analyze common topics in chat interactions"""
    try:
        # Define common topics to look for in messages
        topics = [
            'projects', 'interests', 'hobbies', 'work', 'education', 
            'music', 'movies', 'travel', 'books', 'dating', 
            'finance', 'technology', 'sports', 'food', 'fitness'
        ]
        
        # Get recent chat messages
        recent_messages = list(chat_interactions.find(
            {},
            {'user_message': 1}
        ).sort('timestamp', -1).limit(1000))
        
        # Count topic occurrences
        topic_counts = Counter()
        for message in recent_messages:
            user_msg = message.get('user_message', '').lower()
            for topic in topics:
                if topic.lower() in user_msg:
                    topic_counts[topic] += 1
        
        # Format results
        results = [
            {'topic': topic, 'count': count}
            for topic, count in topic_counts.most_common(10)
        ]
        
        return results
    except Exception as e:
        logger.error(f"Error getting popular chat topics: {str(e)}")
        return []

def get_feedback_metrics() -> Dict[str, Any]:
    """Get metrics on user feedback for chat interactions"""
    try:
        # Get total chat interactions (excluding feedback entries)
        total_chats = chat_interactions.count_documents({'type': {'$ne': 'feedback'}})
        
        # Get feedback metrics
        total_feedback = chat_interactions.count_documents({'type': 'feedback'})
        positive_feedback = chat_interactions.count_documents({'type': 'feedback', 'feedback': 'yes'})
        negative_feedback = chat_interactions.count_documents({'type': 'feedback', 'feedback': 'no'})
        
        # Calculate rates
        feedback_rate = (total_feedback / max(total_chats, 1)) * 100
        positive_rate = (positive_feedback / max(total_feedback, 1)) * 100
        
        return {
            'total_chats': total_chats,
            'total_feedback': total_feedback,
            'positive_feedback': positive_feedback,
            'negative_feedback': negative_feedback,
            'feedback_rate': round(feedback_rate, 1),
            'positive_rate': round(positive_rate, 1)
        }
    except Exception as e:
        logger.error(f"Error getting feedback metrics: {str(e)}")
        return {
            'error': str(e),
            'total_chats': 0,
            'total_feedback': 0
        }

def get_dashboard_summary() -> Dict[str, Any]:
    """Get a summary of key metrics for a dashboard"""
    try:
        # Get engagement metrics
        engagement = get_user_engagement_metrics()
        
        # Get platform stats
        platform_stats = get_platform_usage_stats()
        
        # Get popular interests
        interests = get_popular_interests()
        
        # Get feedback metrics
        feedback = get_feedback_metrics()
        
        # Format for dashboard
        return {
            'user_metrics': {
                'total_users': engagement.get('total_users', 0),
                'active_users_7d': engagement.get('active_users_7d', 0),
                'active_percentage': round(engagement.get('active_percentage', 0), 1),
                'total_chat_interactions': engagement.get('total_chat_interactions', 0)
            },
            'platform_metrics': {
                'users_with_connections': engagement.get('users_with_platforms', 0),
                'connection_rate': round(engagement.get('platform_connection_rate', 0), 1),
                'avg_platforms_per_user': round(engagement.get('avg_platforms_per_user', 0), 1),
                'top_platforms': [
                    {'platform': item.get('_id', 'unknown'), 'count': item.get('count', 0)}
                    for item in platform_stats[:5]
                ]
            },
            'interest_metrics': {
                'top_interests': [
                    {'interest': item.get('_id', 'unknown'), 'count': item.get('count', 0)}
                    for item in interests[:5]
                ]
            },
            'feedback_metrics': {
                'total_feedback': feedback.get('total_feedback', 0),
                'positive_feedback': feedback.get('positive_feedback', 0),
                'feedback_rate': feedback.get('feedback_rate', 0),
                'positive_rate': feedback.get('positive_rate', 0)
            },
            'generated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        logger.error(f"Error getting dashboard summary: {str(e)}")
        return {'error': str(e)}