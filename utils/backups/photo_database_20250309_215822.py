# Photo database with descriptions and metadata

PHOTOS = [
    {
        "id": "mini-cannon-1",
        "filename": "mini-cannon-1.jpg",
        "title": "Mini Desk Cannon",
        "description": "My fully functional miniature desk cannon that can shoot small projectiles. Built this as a weekend project.",
        "category": "projects",
        "tags": ["mini desk cannon", "maker", "project", "desk", "cannon", "DIY", "hobby"]
    },
    {
        "id": "sterling-engine-1",
        "filename": "sterling-engine-1.jpg",
        "title": "Sterling Engine",
        "description": "A sterling engine I built that runs on temperature differentials. It can be powered just by placing it on a hot cup of coffee.",
        "category": "projects",
        "tags": ["sterling engine", "thermodynamics", "physics", "maker", "project", "engine", "hobby"]
    },
    {
        "id": "fishing-1",
        "filename": "fishing-1.jpg",
        "title": "Fishing at Sunset",
        "description": "Evening fishing trip in Annapolis. One of my favorite ways to unwind after work.",
        "category": "outdoors",
        "tags": ["fishing", "outdoors", "sunset", "annapolis", "boat", "water", "hobby"]
    },
    {
        "id": "flipper-zero-1",
        "filename": "flipper-zero-1.jpg",
        "title": "Flipper Zero",
        "description": "My Flipper Zero device that I use for various hardware hacking and security projects.",
        "category": "tech",
        "tags": ["flipper zero", "tech", "hardware", "hacking", "security", "project", "gadget"]
    },
    {
        "id": "beach-dog-1",
        "filename": "beach-dog-1.jpg",
        "title": "Beach Walk with My Dog",
        "description": "Taking my dog for a walk along the beach. One of our regular weekend activities.",
        "category": "outdoors",
        "tags": ["beach", "dog", "walking", "outdoors", "weekend", "relaxation"]
    },
    {
        "id": "raspberry-pi-1",
        "filename": "raspberry-pi-1.jpg",
        "title": "Raspberry Pi Project",
        "description": "Working on a Raspberry Pi project to automate some home functions. This is the prototype board setup.",
        "category": "tech",
        "tags": ["raspberry pi", "tech", "programming", "hardware", "project", "automation"]
    },
    {
        "id": "telescope-1",
        "filename": "telescope-1.jpg",
        "title": "Celestron Telescope Stargazing",
        "description": "Setting up my Celestron telescope for a night of stargazing. This was taken during the last meteor shower.",
        "category": "hobby",
        "tags": ["telescope", "celestron", "astronomy", "stars", "night", "hobby", "space"]
    },
    {
        "id": "books-1",
        "filename": "books-1.jpg",
        "title": "Favorite Books Collection",
        "description": "Some of my favorite books on behavioral economics, including works by Kahneman, Taleb, and Ariely.",
        "category": "interests",
        "tags": ["books", "reading", "kahneman", "taleb", "behavioral economics", "psychology", "hobby"]
    },
    {
        "id": "blowdart-1",
        "filename": "blowdart-1.jpg",
        "title": "Handmade Blowdart Gun",
        "description": "Traditional style blowdart gun I crafted. It's surprisingly accurate at short distances.",
        "category": "projects",
        "tags": ["blowdart", "gun", "craft", "handmade", "project", "hobby"]
    },
    {
        "id": "finance-1",
        "filename": "finance-1.jpg",
        "title": "Financial Analysis Dashboard",
        "description": "A sample of the type of financial analysis dashboard I work with. This is a simplified version with dummy data.",
        "category": "professional",
        "tags": ["finance", "analysis", "dashboard", "professional", "data", "work"]
    },
    {
        "id": "camera-1",
        "filename": "camera-1.jpg",
        "title": "Canon Rebel T7",
        "description": "My Canon Rebel T7 camera that I use for photography, especially outdoors and nature shots.",
        "category": "hobby",
        "tags": ["camera", "canon", "rebel", "photography", "hobby", "tech"]
    },
    {
        "id": "brooks-books-1",
        "filename": "brooks-books-1.jpg",
        "title": "Brooks' Books Project",
        "description": "Early prototype of my Brooks' Books project, which aims to encourage community reading.",
        "category": "projects",
        "tags": ["brooks books", "reading", "community", "project", "books", "social"]
    }
    # Add as many photos as you like with this format
]


def search_photos(query, limit=3):
    """
    Search photos by query string matching against descriptions and tags

    Args:
        query (str): The search query
        limit (int): Maximum number of results to return

    Returns:
        list: Matching photo objects
    """
    query = query.lower()
    results = []

    # Break the query into individual words for better matching
    query_terms = query.split()

    # Score each photo based on how well it matches the query
    scored_photos = []
    for photo in PHOTOS:
        score = 0

        # Check description
        desc_lower = photo["description"].lower()
        for term in query_terms:
            if term in desc_lower:
                score += 3  # Higher weight for description matches

        # Check title
        title_lower = photo["title"].lower()
        for term in query_terms:
            if term in title_lower:
                score += 5  # Highest weight for title matches

        # Check tags
        for tag in photo["tags"]:
            for term in query_terms:
                if term in tag.lower():
                    score += 2  # Medium weight for tag matches

        # Check category
        if any(term in photo["category"].lower() for term in query_terms):
            score += 4  # High weight for category matches

        # Add to results if there's any match
        if score > 0:
            scored_photos.append((score, photo))

    # Sort by score (highest first) and take top results
    scored_photos.sort(reverse=True, key=lambda x: x[0])
    results = [photo for score, photo in scored_photos[:limit]]

    return results


def get_photos_by_category(category, limit=3):
    """Get photos filtered by category"""
    return [photo for photo in PHOTOS if photo["category"].lower() ==
            category.lower()][:limit]


def get_all_categories():
    """Get list of all unique categories"""
    return list(set(photo["category"] for photo in PHOTOS))
