"""
Improved Photo Database Generator

This script generates a photo_database.py file that:
1. Reads metadata from images exported from Apple Photos
2. Updates existing entries rather than duplicating them
3. Preserves custom descriptions/tags you've added manually

Place this script in your project root directory and run it:
python improved_photo_database_generator.py
"""

import os
import re
import json
import time
from datetime import datetime
import sys
import importlib.util
from PIL import Image
from PIL.ExifTags import TAGS

# Configuration
IMAGE_DIR = "static/images"
OUTPUT_FILE = "utils/photo_database.py"
BACKUP_DIR = "utils/backups"
SUPPORTED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp']

# Make sure directories exist
os.makedirs("utils", exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)


def backup_existing_database():
    """Create a backup of the existing database if it exists"""
    if os.path.exists(OUTPUT_FILE):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(
            BACKUP_DIR, f"photo_database_{timestamp}.py")

        with open(OUTPUT_FILE, 'r') as src, open(backup_file, 'w') as dst:
            dst.write(src.read())

        print(f"Created backup: {backup_file}")
        return True
    return False


def load_existing_database():
    """Load the existing photo database if it exists"""
    if os.path.exists(OUTPUT_FILE):
        try:
            # Import the module dynamically
            spec = importlib.util.spec_from_file_location(
                "photo_database", OUTPUT_FILE)
            if spec is not None and spec.loader is not None:  # Add null checks to fix type errors
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Get the PHOTOS list
                if hasattr(module, 'PHOTOS'):
                    return module.PHOTOS
        except Exception as e:
            print(f"Error loading existing database: {e}")

    return []


def extract_metadata_from_image(file_path):
    """Extract metadata from image file, including EXIF data"""
    metadata = {}

    try:
        with Image.open(file_path) as img:
            # Get basic image info
            metadata["width"] = img.width
            metadata["height"] = img.height
            metadata["format"] = img.format

            # Extract EXIF data if available
            if hasattr(img, '_getexif') and img._getexif():
                exif_data = {}
                for tag, value in img._getexif().items():
                    tag_name = TAGS.get(tag, tag)
                    exif_data[tag_name] = str(value)

                # Look for specific useful EXIF data
                if "ImageDescription" in exif_data:
                    metadata["description"] = exif_data["ImageDescription"]

                if "DateTimeOriginal" in exif_data:
                    metadata["date_taken"] = exif_data["DateTimeOriginal"]

                if "UserComment" in exif_data:
                    metadata["user_comment"] = exif_data["UserComment"]

                if "XPKeywords" in exif_data:
                    # XPKeywords often contains tags from Apple Photos
                    keywords = exif_data["XPKeywords"]
                    if keywords:
                        metadata["keywords"] = keywords.split(';')

                if "XPTitle" in exif_data:
                    metadata["title"] = exif_data["XPTitle"]

                if "XPComment" in exif_data:
                    metadata["comment"] = exif_data["XPComment"]

                if "XPSubject" in exif_data:
                    metadata["subject"] = exif_data["XPSubject"]

                if "GPSInfo" in exif_data:
                    metadata["has_location"] = True
    except Exception as e:
        print(f"Warning: Could not extract metadata from {file_path}: {e}")

    return metadata


def extract_info_from_filename(filename, file_path):
    """Extract base name and tags from filename and file metadata"""
    base_name, ext = os.path.splitext(filename)

    # Replace hyphens and underscores with spaces for a clean name
    clean_name = base_name.replace('-', ' ').replace('_', ' ')

    # Get metadata from the image file
    metadata = extract_metadata_from_image(file_path)

    # Try to get title from metadata, fallback to filename
    title = metadata.get("title", None)
    if not title:
        title_words = [word.capitalize() for word in clean_name.split()]
        title = ' '.join(title_words)

    # Try to get description from metadata, fallback to basic one
    description = metadata.get(
        "description",
        None) or metadata.get(
        "comment",
        None) or metadata.get(
            "user_comment",
        None)
    if not description:
        description = f"Photo of {clean_name.lower()}."

    # Get tags from keywords metadata or generate from filename
    tags = []
    if "keywords" in metadata:
        tags = metadata["keywords"]
    else:
        # Split into words for tags
        words = clean_name.split()
        tags = [word.lower() for word in words if len(word) > 2]

    # Try to extract a category
    category_patterns = {
        'projects': [
            'project',
            'cannon',
            'engine',
            'flipper',
            'raspberry',
            'pi',
            'blowdart',
            'gun',
            'diy',
            'maker'],
        'outdoors': [
            'fishing',
            'beach',
            'boat',
            'water',
            'outdoor',
            'nature',
            'hike',
            'dog',
            'walk'],
        'tech': [
            'tech',
            'flipper',
            'zero',
            'raspberry',
            'pi',
            'camera',
            'gadget',
            'device',
            'electronic'],
        'hobby': [
            'hobby',
            'telescope',
            'book',
            'read',
            'camera',
            'photo',
            'astronomy',
            'celestron'],
        'professional': [
            'work',
            'finance',
            'analysis',
            'professional',
            'office',
            'desk',
            'business']}

    category = 'other'

    # First check tags
    for tag in tags:
        for cat, patterns in category_patterns.items():
            if any(pattern == tag.lower() for pattern in patterns):
                category = cat
                break

    # If no category found from tags, check filename
    if category == 'other':
        for cat, patterns in category_patterns.items():
            if any(pattern in clean_name.lower() for pattern in patterns):
                category = cat
                break

    # Add the category to tags if not already there
    if category not in tags:
        tags.append(category)

    return {
        "id": base_name,
        "filename": filename,
        "title": title,
        "description": description,
        "category": category,
        "tags": tags,
        "metadata": metadata  # Store additional metadata
    }


def generate_database(existing_photos=[]):
    """Generate the photo database by scanning the image directory"""
    photos = []
    existing_photo_map = {photo["filename"]                          : photo for photo in existing_photos}
    processed_filenames = set()

    if not os.path.exists(IMAGE_DIR):
        print(
            f"Warning: Image directory {IMAGE_DIR} does not exist. Creating it.")
        os.makedirs(IMAGE_DIR)
        return []

    # Scan the image directory
    for filename in os.listdir(IMAGE_DIR):
        file_path = os.path.join(IMAGE_DIR, filename)
        if os.path.isfile(file_path):
            # Check if it's an image file
            ext = os.path.splitext(filename)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                processed_filenames.add(filename)

                # Check if this file already exists in our database
                if filename in existing_photo_map:
                    # Use existing entry but check if the file has been
                    # modified
                    file_mtime = os.path.getmtime(file_path)

                    # Check if the entry has a last_updated field
                    existing_entry = existing_photo_map[filename]
                    last_updated = existing_entry.get("last_updated", 0)

                    if file_mtime > last_updated:
                        # File has been modified, update the entry
                        print(f"Updating entry for modified file: {filename}")
                        photo_info = extract_info_from_filename(
                            filename, file_path)

                        # Preserve any manually added fields
                        for key, value in existing_entry.items():
                            if key not in photo_info or (
                                key == "description" and photo_info[key] == f"Photo of {
                                    photo_info['id'].lower().replace(
                                        '-',
                                        ' ').replace(
                                        '_',
                                        ' ')}."):
                                photo_info[key] = value

                        # Update the last_updated timestamp
                        photo_info["last_updated"] = file_mtime
                        photos.append(photo_info)
                    else:
                        # File hasn't been modified, use existing entry
                        photos.append(existing_entry)
                else:
                    # New file, create a new entry
                    print(f"Adding new entry for: {filename}")
                    photo_info = extract_info_from_filename(
                        filename, file_path)
                    photo_info["last_updated"] = os.path.getmtime(file_path)
                    photos.append(photo_info)

    # Check for files that were in the database but no longer exist in the
    # image directory
    for filename, photo in existing_photo_map.items():
        if filename not in processed_filenames:
            print(
                f"Warning: File {filename} in database but not found in image directory")
            # Optionally, you could still include these entries with a warning flag
            # photo["missing"] = True
            # photos.append(photo)

    return photos


def write_database_file(photos):
    """Write the database file with the photo information"""
    with open(OUTPUT_FILE, 'w') as f:
        f.write("# Photo database with descriptions and metadata\n")
        f.write(
            f"# Generated on {
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("PHOTOS = [\n")

        for photo in photos:
            f.write("    {\n")
            f.write(f'        "id": "{photo["id"]}",\n')
            f.write(f'        "filename": "{photo["filename"]}",\n')
            f.write(f'        "title": "{photo["title"]}",\n')
            f.write(f'        "description": "{photo["description"]}",\n')
            f.write(f'        "category": "{photo["category"]}",\n')

            # Format tags
            tags_str = ', '.join([f'"{tag}"' for tag in photo["tags"]])
            f.write(f'        "tags": [{tags_str}],\n')

            # Add last_updated timestamp
            f.write(
                f'        "last_updated": {
                    photo.get(
                        "last_updated",
                        time.time())}\n')

            f.write("    },\n")

        f.write("]\n\n")

        # Fix for the triple quotes issue - replace these lines in the script:

        # Add search functions
        f.write('''
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
            return [photo for photo in PHOTOS if photo["category"].lower() == category.lower()][:limit]

        def get_all_categories():
            """Get list of all unique categories"""
            return list(set(photo["category"] for photo in PHOTOS))
        ''')

    print(f"Generated {OUTPUT_FILE} with {len(photos)} photos")


def main():
    print("Starting improved photo database generator...")

    # Check for required libraries
    try:
        import PIL
    except ImportError:
        print("Error: The Pillow library is required for this script.")
        print("Please install it with: pip install Pillow")
        return

    # Backup existing database if it exists
    existing_db = backup_existing_database()

    # Load existing database if it exists
    existing_photos = load_existing_database()
    if existing_photos:
        print(f"Loaded {len(existing_photos)} existing entries from database")

    print("Scanning image directory...")
    photos = generate_database(existing_photos)

    if not photos:
        print("No photos found in the image directory. Please add some images first.")
        return

    print(f"Found {len(photos)} photos total")
    write_database_file(photos)

    print("\nDone! The database has been updated.")
    print("\nTips for further improvement:")
    print("1. Review categories - make sure they're correct")
    print("2. Enhance descriptions - add more details if needed")
    print("3. Add more specific tags - this improves search relevance")


if __name__ == "__main__":
    main()
