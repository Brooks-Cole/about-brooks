# Photo database with descriptions and metadata
# Generated on 2025-03-09 22:00:30

import urllib.parse


def url_encode_dict_keys(photos_list):
    """URL encode the id and filename keys in each photo dictionary"""
    for photo in photos_list:
        # URL encode the id and filename
        photo["id"] = urllib.parse.quote(photo["id"])
        photo["filename"] = urllib.parse.quote(photo["filename"])
    return photos_list


PHOTOS = [
    {
        "id": "Blueman Group",
        "filename": "Blueman Group.jpeg",
        "title": "Blueman Group",
        "description": "me dressed up as the blueman group in NYC",
        "category": "other",
        "tags": ["blueman", "group", "other"],
        "last_updated": 1741571445.7431443
    },
    {
        "id": "garden with no veggies",
        "filename": "garden with no veggies.jpeg",
        "title": "Garden With No Veggies",
        "description": "a garden that i built, prior to anything growing",
        "category": "other",
        "tags": ["garden", "with", "veggies", "other"],
        "last_updated": 1741571411.2560549
    },
    {
        "id": "Four Brothers at Andrews Wedding",
        "filename": "Four Brothers at Andrews Wedding.jpeg",
        "title": "Four Brothers At Andrews Wedding",
        "description": "me and my brothers at Andrews wedding",
        "category": "other",
        "tags": ["four", "brothers", "andrews", "wedding", "other"],
        "last_updated": 1741571436.931462
    },
    {
        "id": "NYC",
        "filename": "NYC.jpeg",
        "title": "Nyc",
        "description": "A photo I took while in NYC",
        "category": "other",
        "tags": ["nyc", "other"],
        "last_updated": 1741571428.7342818
    },
    {
        "id": "Brooks and extended family at DCL",
        "filename": "Brooks and extended family at DCL.jpeg",
        "title": "Brooks And Extended Family At Dcl",
        "description": "Brooks with his brothers, grandmother, and cousins at deep creek lake",
        "category": "other",
        "tags": ["brooks", "and", "extended", "family", "dcl", "other"],
        "last_updated": 1741571401.5479133
    },
    {
        "id": "Indians playing polo on elephants",
        "filename": "Indians playing polo on elephants.jpeg",
        "title": "Indians Playing Polo On Elephants",
        "description": "a thrift store find photo of indians playing polo on elephants",
        "category": "other",
        "tags": ["indians", "playing", "polo", "elephants", "other"],
        "last_updated": 1741571425.455137
    },
    {
        "id": "Walking into a volcano",
        "filename": "Walking into a volcano.jpeg",
        "title": "Walking Into A Volcano",
        "description": "me walking towards a volcano in Costa Rica",
        "category": "outdoors",
        "tags": ["walking", "into", "volcano", "outdoors"],
        "last_updated": 1741571424.0942852
    },
    {
        "id": "Garden with veggies",
        "filename": "Garden with veggies.jpeg",
        "title": "Garden With Veggies",
        "description": "The garden with the veggies that I grew",
        "category": "other",
        "tags": ["garden", "with", "veggies", "other"],
        "last_updated": 1741571423.4529316
    },
    {
        "id": "Sharktooth",
        "filename": "Sharktooth.jpeg",
        "title": "Sharktooth",
        "description": "a sharktooth that I found",
        "category": "other",
        "tags": ["sharktooth", "other"],
        "last_updated": 1741571423.1201928
    },
    {
        "id": "Sailfish",
        "filename": "Sailfish.jpeg",
        "title": "Sailfish",
        "description": "a fish I caught in florida",
        "category": "other",
        "tags": ["sailfish", "other"],
        "last_updated": 1741571431.959352
    },
    {
        "id": "Nancy going for the chickens",
        "filename": "Nancy going for the chickens.jpeg",
        "title": "Nancy Going For The Chickens",
        "description": "a picture of nancy chasing the chickens in the backyard",
        "category": "other",
        "tags": ["nancy", "going", "for", "the", "chickens", "other"],
        "last_updated": 1741571432.1815326
    },
    {
        "id": "Workshop",
        "filename": "Workshop.jpeg",
        "title": "Workshop",
        "description": "An image showing the garage/workshop in Wilmington where Brooks builds things",
        "category": "professional",
        "tags": ["workshop", "professional"],
        "last_updated": 1741571409.8471165
    },
    {
        "id": "Back Creek Sunset",
        "filename": "Back Creek Sunset.jpeg",
        "title": "Back Creek Sunset",
        "description": "a photo of the sunset on the water",
        "category": "other",
        "tags": ["back", "creek", "sunset", "other"],
        "last_updated": 1741571425.7538798
    },
    {
        "id": "Truffle",
        "filename": "Truffle.jpeg",
        "title": "Truffle",
        "description": "a truffle in NYC",
        "category": "other",
        "tags": ["truffle", "other"],
        "last_updated": 1741571429.823873
    },
    {
        "id": "Crabs",
        "filename": "Crabs.jpeg",
        "title": "Crabs",
        "description": "some crabs I caught in annapolis",
        "category": "other",
        "tags": ["crabs", "other"],
        "last_updated": 1741571436.692439
    },
    {
        "id": "Bonsai trees",
        "filename": "Bonsai trees.jpeg",
        "title": "Bonsai Trees",
        "description": "a picture of some bonsai trees at the national arboretum in dc",
        "category": "other",
        "tags": ["bonsai", "trees", "other"],
        "last_updated": 1741571436.0382056
    },
    {
        "id": "Veggies from Garden",
        "filename": "Veggies from Garden.jpeg",
        "title": "Veggies From Garden",
        "description": "some veggies from the garden",
        "category": "other",
        "tags": ["veggies", "from", "garden", "other"],
        "last_updated": 1741571411.7043145
    },
    {
        "id": "Fig sleeping on me",
        "filename": "Fig sleeping on me.jpeg",
        "title": "Fig Sleeping On Me",
        "description": "a picture of fig sleeping on me",
        "category": "projects",
        "tags": ["fig", "sleeping", "projects"],
        "last_updated": 1741571433.18482
    },
    {
        "id": "Maine yard",
        "filename": "Maine yard.jpeg",
        "title": "Maine Yard",
        "description": "a photo of maine",
        "category": "other",
        "tags": ["maine", "yard", "other"],
        "last_updated": 1741571419.2606254
    },
    {
        "id": "Hunting Pigeons in Argentina",
        "filename": "Hunting Pigeons in Argentina.jpeg",
        "title": "Hunting Pigeons In Argentina",
        "description": "Pigeons that Brooks shot in Cordoba, Argentina",
        "category": "projects",
        "tags": ["hunting", "pigeons", "argentina", "projects"],
        "last_updated": 1741571399.6508384
    },
    {
        "id": "Me on a boat in Alabama",
        "filename": "Me on a boat in Alabama.jpeg",
        "title": "Me On A Boat In Alabama",
        "description": "me on a wakesurfing boat in Alabama",
        "category": "outdoors",
        "tags": ["boat", "alabama", "outdoors"],
        "last_updated": 1741571436.218695
    },
    {
        "id": "Carnivorous Garden",
        "filename": "Carnivorous Garden.jpeg",
        "title": "Carnivorous Garden",
        "description": "A carnivorous garden I walked around in",
        "category": "other",
        "tags": ["carnivorous", "garden", "other"],
        "last_updated": 1741571423.7662597
    },
    {
        "id": "ASAP Rocky and Ferg",
        "filename": "ASAP Rocky and Ferg.jpeg",
        "title": "Asap Rocky And Ferg",
        "description": "a photo I took of asap ferg and asap rocky",
        "category": "other",
        "tags": ["asap", "rocky", "and", "ferg", "other"],
        "last_updated": 1741571428.416369
    },
    {
        "id": "Mahi Mahi",
        "filename": "Mahi Mahi.jpeg",
        "title": "Mahi Mahi",
        "description": "A Mahi-Mahi that brooks caught in Islamorada",
        "category": "other",
        "tags": ["mahi", "mahi", "other"],
        "last_updated": 1741571400.034814
    },
    {
        "id": "Fox Brown Outfitters Hunting",
        "filename": "Fox Brown Outfitters Hunting.jpeg",
        "title": "Fox Brown Outfitters Hunting",
        "description": "Brooks and Tom hunting at Fox Brown Outfitters",
        "category": "other",
        "tags": ["fox", "brown", "outfitters", "hunting", "other"],
        "last_updated": 1741571399.968269
    },
    {
        "id": "Bay Bridge",
        "filename": "Bay Bridge.jpeg",
        "title": "Bay Bridge",
        "description": "a photo of the Chesapeake Bay Bridge from a boat",
        "category": "other",
        "tags": ["bay", "bridge", "other"],
        "last_updated": 1741571425.9535403
    },
    {
        "id": "Book Vase",
        "filename": "Book Vase.jpeg",
        "title": "Book Vase",
        "description": "a vase I made out of books",
        "category": "hobby",
        "tags": ["book", "vase", "hobby"],
        "last_updated": 1741571431.7066984
    },
    {
        "id": "2-seater",
        "filename": "2-seater.jpeg",
        "title": "2 Seater",
        "description": "Image from a 2-seater plane above Boulder",
        "category": "other",
        "tags": ["seater", "other"],
        "last_updated": 1741571399.8054996
    },
    {
        "id": "Stingray",
        "filename": "Stingray.jpeg",
        "title": "Stingray",
        "description": "A stingray I caught",
        "category": "other",
        "tags": ["stingray", "other"],
        "last_updated": 1741571402.7081506
    },
    {
        "id": "Holly Shelter",
        "filename": "Holly Shelter.jpeg",
        "title": "Holly Shelter",
        "description": "an image of holly shelter, nc, where Brooks did some adventuring outdoors",
        "category": "other",
        "tags": ["holly", "shelter", "other"],
        "last_updated": 1741571410.1522684
    },
    {
        "id": "Brook as a child with Geep",
        "filename": "Brook as a child with Geep.jpeg",
        "title": "Brook As A Child With Geep",
        "description": "Brooks as a child with his grandfather, Geep",
        "category": "other",
        "tags": ["brook", "child", "with", "geep", "other"],
        "last_updated": 1741571409.2643209
    },
    {
        "id": "Brooks selfie with abs",
        "filename": "Brooks selfie with abs.jpeg",
        "title": "Brooks Selfie With Abs",
        "description": "A selfie of Brooks showing his abs",
        "category": "other",
        "tags": ["brooks", "selfie", "with", "abs", "other"],
        "last_updated": 1741571409.5243332
    },
    {
        "id": "Sweetwater 420",
        "filename": "Sweetwater 420.jpeg",
        "title": "Sweetwater 420",
        "description": "me and some friends at a music festival. Blond guy looked like peirce",
        "category": "outdoors",
        "tags": ["sweetwater", "420", "outdoors"],
        "last_updated": 1741571411.3316214
    },
    {
        "id": "Me at Andrews wedding",
        "filename": "Me at Andrews wedding.jpeg",
        "title": "Me At Andrews Wedding",
        "description": "a selfie of me at Andrews Wedding",
        "category": "other",
        "tags": ["andrews", "wedding", "other"],
        "last_updated": 1741571436.743282
    },
    {
        "id": "sharks teeth",
        "filename": "sharks teeth.jpeg",
        "title": "Sharks Teeth",
        "description": "two sharks teeth i found",
        "category": "other",
        "tags": ["sharks", "teeth", "other"],
        "last_updated": 1741571427.6023626
    },
    {
        "id": "bonsai",
        "filename": "bonsai.jpeg",
        "title": "Bonsai",
        "description": "some bonsais at the national arboretum",
        "category": "other",
        "tags": ["bonsai", "other"],
        "last_updated": 1741571435.7246923
    },
    {
        "id": "Tom and Anyura Wedding",
        "filename": "Tom and Anyura Wedding.jpeg",
        "title": "Tom And Anyura Wedding",
        "description": "a photo of Brooks and his brothers holding up Anyura at her wedding",
        "category": "other",
        "tags": ["tom", "and", "anyura", "wedding", "other"],
        "last_updated": 1741571410.188817
    },
    {
        "id": "Volunteering at a youth jail",
        "filename": "Volunteering at a youth jail.jpeg",
        "title": "Volunteering At A Youth Jail",
        "description": "Brooks at a youth jail in Florida, volunteering at a workshop to improve youth prisoners resumes, teach them how to tie ties, and help them come up with a plan to get a job",
        "category": "other",
        "tags": ["volunteering", "youth", "jail", "other"],
        "last_updated": 1741571409.117802
    },
    {
        "id": "Carrier Pigeons",
        "filename": "Carrier Pigeons.jpeg",
        "title": "Carrier Pigeons",
        "description": "some carrier pigeons I bought",
        "category": "projects",
        "tags": ["carrier", "pigeons", "projects"],
        "last_updated": 1741571436.9806945
    },
    {
        "id": "IMG_2694",
        "filename": "IMG_2694.jpeg",
        "title": "Img 2694",
        "description": "Photo of img 2694.",
        "category": "other",
        "tags": ["img", "2694", "other"],
        "last_updated": 1741571423.955107
    },
    {
        "id": "Costa Rica",
        "filename": "Costa Rica.jpeg",
        "title": "Costa Rica",
        "description": "Brooks on vacation in Costa Rica",
        "category": "other",
        "tags": ["costa", "rica", "other"],
        "last_updated": 1741571409.1640916
    },
    {
        "id": "Fort Armistead",
        "filename": "Fort Armistead.jpeg",
        "title": "Fort Armistead",
        "description": "pics I took while adventuring and exploring in fort armistead",
        "category": "other",
        "tags": ["fort", "armistead", "other"],
        "last_updated": 1741571431.907339
    },
    {
        "id": "parasailing",
        "filename": "parasailing.jpeg",
        "title": "Parasailing",
        "description": "a photo of me parasailing in annapolis",
        "category": "other",
        "tags": ["parasailing", "other"],
        "last_updated": 1741571436.3958325
    },
    {
        "id": "Maine scenery",
        "filename": "Maine scenery.jpeg",
        "title": "Maine Scenery",
        "description": "a photo of the water in maine",
        "category": "other",
        "tags": ["maine", "scenery", "other"],
        "last_updated": 1741571418.8284667
    },
    {
        "id": "Mountain and Tree art",
        "filename": "Mountain and Tree art.jpeg",
        "title": "Mountain And Tree Art",
        "description": "a piece of woodworking art that I created, showing a mountain and a tree",
        "category": "other",
        "tags": ["mountain", "and", "tree", "art", "other"],
        "last_updated": 1741571410.9330492
    },
    {
        "id": "Whale",
        "filename": "Whale.jpeg",
        "title": "Whale",
        "description": "a whale that i found on the beach in NC",
        "category": "other",
        "tags": ["whale", "other"],
        "last_updated": 1741571410.5050845
    },
    {
        "id": "Wagyu",
        "filename": "Wagyu.jpeg",
        "title": "Wagyu",
        "description": "a photo of some wagyu in NYC",
        "category": "other",
        "tags": ["wagyu", "other"],
        "last_updated": 1741571428.9102688
    },
    {
        "id": "Fit Brooks",
        "filename": "Fit Brooks.jpeg",
        "title": "Fit Brooks",
        "description": "A photo of brooks with abs",
        "category": "other",
        "tags": ["fit", "brooks", "other"],
        "last_updated": 1741571409.208254
    },
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


# Apply URL encoding to all photo IDs and filenames
PHOTOS = url_encode_dict_keys(PHOTOS)
