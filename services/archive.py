"""
Internet Archive service layer.
Handles all interactions with archive.org.
"""
import os
import re
from datetime import datetime
from werkzeug.datastructures import FileStorage
from internetarchive import get_session as ia
from typing import Dict, Optional

import requests
from . import database as db
from config import trusted_uploaders, TEST


# ============================================================================
# Metadata Operations
# ============================================================================

def fetch_metadata_from_archive(archive_id: str) -> Dict:
    """
    Fetch video metadata from Internet Archive.
    Returns dict with title, description, uploader.
    """
    item = ia().get_item(archive_id)
    metadata = item.metadata
    return {
        "title": metadata.get("title", "Untitled"),
        "description": metadata.get("description", ""),
        "uploader": metadata.get("uploader", ""),
        "archive_id": archive_id
    }


# ============================================================================
# Video Upload/Update Operations
# ============================================================================

def check_item(id):
    status = requests.get("https://archive.org/details/"+id).status_code 
    if status == 200:
        return True
    elif status == 404:
        return False
    else:
        raise Exception(f"Unexpected response checking item {id}: {status}")
        return None
    
def generate_archive_id(title: str) -> str:
    # Step 1: Clean the title
    clean_title = re.sub(r'[^a-zA-Z0-9_]', '_', title.lower())

    # Step 2: Generate timestamp components
    now = datetime.now()
    timestamp_parts = [
        "",  # empty for first check (just the title)
        now.strftime("_%Y%m"),  # year + month
        now.strftime("%d"),      # day
        now.strftime("_%H%M"),  # hour + minute
        now.strftime("%S"),      # second
        f"_{now.microsecond}"    # microsecond
    ]

    # Step 3: Try appending progressively until unique
    candidate = clean_title
    for part in timestamp_parts:
        if not check_item(candidate):
            return candidate
        candidate += part

    raise Exception("Could not generate unique archive ID")


def create_video_item_on_archive(md: Dict, file: FileStorage) -> int:
    """
    Upload a new video to Internet Archive.
    
    Args:
        metadata: Dict with 'title', 'description', etc.
    
    Returns:
        archive_id of the newly created item
    """
    archive_id = generate_archive_id(md['title'])

    # Upload streamed file to new archive item
    ias = ia()
    item = ias.get_item(archive_id, item_metadata=md)
    item.upload(file.stream)   
     
    # Save to local db
    id_ = db.create_video(md['title'], md['description'], archive_id)
    return id_


def update_video_file_on_archive(archive_id: str, new_video_file_path: str):
    """
    Replace the video file on an existing Archive.org item.
    Keeps the same archive_id and metadata.
    """
    ias = ia()
    item = ias.get_item(archive_id)
    
    # Delete old video files (you might need to adjust file matching logic)
    for file in item.files:
        if file['name'].endswith(('.mp4', '.avi', '.mov', '.mkv')):
            ias.delete(file['name'])
    
    # Upload new file
    item.upload(new_video_file_path)


# ============================================================================
# One-Time Migration from Archive.org
# ============================================================================

def migrate_from_archive():
    """
    ONE-TIME MIGRATION: Scan Archive.org for ChasidusTV videos
    and populate the database.
    
    This replaces your old update_db() function.
    Run this once, then never again.
    """
    query = 'Subject:"ChasidusTV" AND Mediatype:movies'
    fields = ['identifier']
    
    print(f"Scanning Archive.org: {query}")
    search = ia().search_items(query, fields=fields, max_retries=20)
    
    added_count = 0
    skipped_count = 0
    
    for result in search:
        archive_id = result["identifier"]
        
        # Check if already in database
        existing = db.get_video_by_archive_id(archive_id)
        if existing:
            print(f"  SKIP (exists): {archive_id}")
            skipped_count += 1
            continue
        
        # Fetch metadata
        try:
            metadata = ia().get_item(archive_id).metadata
            print(f"  FOUND: {archive_id} - {metadata['title']}")
        except Exception as e:
            print(f"  ERROR fetching {archive_id}: {e}")
            continue
        
        # Filter by trusted uploaders
        if metadata["uploader"] not in trusted_uploaders:
            print(f"    SKIP (untrusted uploader): {metadata['uploader']}")
            skipped_count += 1
            continue
        
        # Add to database
        video_id = db.create_video(
            title=metadata["title"],
            description=metadata["description"],
            archive_id=archive_id
        )
        
        # Parse hierarchical playlist structure from metadata if it exists
        # (This is the old "GroupName:PlaylistName" logic)
        playlists_str = metadata.get("playlists", "")
        if playlists_str:
            _assign_video_from_legacy_format(video_id, playlists_str)
        
        added_count += 1

        if TEST:
            if added_count > 3:
                print("  TEST MODE: stopping after 3 additions")
                break
    
    print(f"\nMigration complete: {added_count} added, {skipped_count} skipped")


def _assign_video_from_legacy_format(video_id: int, playlists_str: str):
    """
    Helper function to parse old "Group:Playlist;Group2:Playlist2" format
    and create the proper database relations.
    """
    for entry in playlists_str.split(';'):
        entry = entry.strip()
        if not entry or entry.endswith(':'):
            continue
        
        parts = [p for p in entry.split(':') if p]
        if len(parts) == 0:
            continue
        
        playlist_name = parts[-1]
        group_name = parts[-2] if len(parts) >= 2 else None
        
        # Get or create playlist
        with db.get_db() as conn:
            row = conn.execute(
                'SELECT id FROM playlists WHERE name = ?',
                (playlist_name,)
            ).fetchone()
            
            if row:
                playlist_id = row["id"]
            else:
                playlist_id = db.create_playlist(playlist_name)
        
        # Get or create group if specified
        if group_name:
            with db.get_db() as conn:
                row = conn.execute(
                    'SELECT id FROM groups WHERE name = ?',
                    (group_name,)
                ).fetchone()
                
                if row:
                    group_id = row["id"]
                else:
                    group_id = db.create_group(group_name)
            
            db.assign_playlist_to_group(group_id, playlist_id)
        
        # Assign video to playlist
        db.assign_video_to_playlist(playlist_id, video_id)
