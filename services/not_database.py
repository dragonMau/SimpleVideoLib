from not_blob_list import BlobList
from not_database_types import AlreadyExistsError
from pydantic import BaseModel
from typing import List
import sqlite3
import internetarchive as ia
from config import trusted_uploaders, DB_PATH

class Video(BaseModel):
    id_: int = 0
    title: str = "VideoTitle"
    description: str = "VideoDescription"
    archive_id: str = "archiveid"
    playlists: str = ""
    uploader: str = ""
    def __str__(self):
        return super().__repr__()

class Playlist(BaseModel):
    id_: int =  0
    name: str = "PlaylistName"
    videos_ids: List[int] = [0, ...]
    def __str__(self):
        return super().__repr__()

class Group(BaseModel):
    id_: int = 0
    name: str = "GroupName"
    playlists_ids: List[int] = [0, ...]
    def __str__(self):
        return super().__repr__()

def init_db():
    # Connect to SQLite and create tables
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT, 
            archive_id TEXT,
            playlists_ids BLOB  -- uint32[]
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS playlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            videos_ids BLOB  -- uint32[],
            groups_ids BLOB  -- uint32[]
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            playlists_ids BLOB -- uint32[]
        )
        ''')

def clear_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("DROP TABLE IF EXISTS videos")
        cursor.execute("DROP TABLE IF EXISTS playlists")
        cursor.execute("DROP TABLE IF EXISTS groups")

    print("Database cleared.")

def update_playlist(playlist: str, vidid) -> int | None:
    if not playlist or playlist.endswith(':'):
        return None

    tree = [e for e in playlist.split(':') if e]
    playlist_name = tree.pop() if tree else None
    group_name = tree.pop() if tree else None

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Insert or find playlist
        cursor.execute("SELECT id, videos_ids FROM playlists WHERE name = ?", (playlist_name,))
        row = cursor.fetchone()
        if row:
            playlist_id, videos_ids = row
            blist = BlobList(videos_ids)
            blist.add(vidid)
            cursor.execute(
                "UPDATE playlists SET videos_ids = ? WHERE id = ?",
                (blist.to_bytes(), playlist_id)
            )
        else:
            blist = BlobList()
            blist.add(vidid)
            cursor.execute(
                "INSERT INTO playlists (name, videos_ids) VALUES (?, ?)",
                (playlist_name, blist.to_bytes())
            )
            playlist_id = cursor.lastrowid


        if group_name:
            # Insert or find group
            cursor.execute("SELECT id, playlists_ids FROM groups WHERE name = ?", (group_name,))
            row = cursor.fetchone()
            plist = BlobList()
            if row:
                group_id, blob = row
                plist = BlobList(blob or b'')
            else:
                cursor.execute(
                    "INSERT INTO groups (name, playlists_ids) VALUES (?, ?)",
                    (group_name, b'')
                )
                group_id = cursor.lastrowid

            # Add playlist ID to group if not already there
            if plist.add(playlist_id):
                cursor.execute(
                    "UPDATE groups SET playlists_ids = ? WHERE id = ?",
                    (plist.to_bytes(), group_id)
                )

    return playlist_id

def _add_video(vid: Video):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM videos WHERE archive_id = ?", 
            (vid.archive_id,)
        )
        row = cursor.fetchone()
        print('    duplicates:', row)
        if row:
            vid.id_ = row[0]    
            cursor.execute(
                "UPDATE videos SET title = ?, description = ?, archive_id = ? WHERE id = ?",
                (vid.title, vid.description, vid.archive_id, vid.id_)
            )
        else:
            cursor.execute(
                "INSERT INTO videos (title, description, archive_id) VALUES (?, ?, ?)",
                (vid.title, vid.description, vid.archive_id)
            )
            vid.id_ = cursor.lastrowid
    return vid.id_


def _add_to_db(vid: Video):
    vidid = _add_video(vid)
    for pl in vid.playlists.split(';'):
        if not pl: continue
        update_playlist(pl, vidid)

def _process_result(result):
    id_ = result["identifier"]
    item = ia.get_item(id_)
    print(id_, end=': ')
    vid = Video(**item.metadata, archive_id=id_)
    print(vid)
    if vid.uploader in trusted_uploaders:
        _add_to_db(vid)
        return 1
    else:
        print("    not mine, uploader:", vid.uploader)
        return 0

def update_db():
    query = (
        'Subject:"ChasidusTV" AND '
        'Mediatype:movies'
    )
    fields=[
        'identifier'
    ]
    amount = 0
    print(query)
    search = ia.search_items(
        query, 
        fields=fields,
        max_retries=20,
    )
    print(search)
    for result in search:
        amount += _process_result(result)
    print(f"added {amount} videos")

def print_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        # Loop through all tables and print their contents
        for table in tables:
            table_name = table[0]
            print(f"\n--- Table: {table_name} ---")

            # Get column names
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = [col[1] for col in cursor.fetchall()]
            print("Columns:", columns)

            # Get all rows
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()

            # Print each row
            for row in rows:
                print(row)

def get_videos(playlist_id):  # get videos of a playlist
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Get videos_ids blob
        cursor.execute("SELECT videos_ids FROM playlists WHERE id = ?", (playlist_id,))
        row = cursor.fetchone()
        if not row or not row[0]:
            return None

        blist = BlobList(row[0])
        video_ids = blist.to_list()

        # Use SQL IN to fetch all videos
        cursor.execute(
            f"SELECT id, title, description, archive_id FROM videos WHERE id IN ({','.join('?'*len(video_ids))})"
            (video_ids,)
        )
        rows = cursor.fetchall()

        return [{
            "id_": row[0],
            "title": row[1],
            "description": row[2],
            "archive_id": row[3]
        } for row in rows]

def get_playlists(group_id):  # get playlists of a group
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT playlists_ids FROM groups WHERE id = ?",
            (group_id,)
        )
        row = cursor.fetchone()
        if not row or not row[0]:
            return None

        blist = BlobList(row[0])
        playlist_ids = blist.to_list()

        cursor.execute(
            f"SELECT id, name FROM playlists WHERE id IN ({','.join('?'*len(playlist_ids))})",
            (playlist_ids,)
        )
        rows = cursor.fetchall()

        return [{
            "id_": row[0], 
            "name": row[1]
        } for row in rows]


    
def get_groups(): # all
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM groups")
        rows = cursor.fetchall()
        return [{
            "id_": row[0], 
            "name": row[1]
        } for row in rows]

def get_video(video_id):  # get video data
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor() 

        query = f"SELECT id, title, description, archive_id FROM videos WHERE id IN video_id"
        cursor.execute(query, (video_id,))
        row = cursor.fetchone()

        return {
            "id_": row[0], 
            "title": row[1],
            "description": row[2],
            "archive_id": row[3],
        }

def change_video(video_id, title=None, description=None):
    if title is None and description is None:
        raise ValueError("You must provide at least one field to change")
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor() 
        if title is not None:
            query = f"UPDATE videos SET title = ? WHERE id = ?"
            cursor.execute(query, (title, video_id))
        if description is not None:
            query = f"UPDATE videos SET description = ? WHERE id = ?"
            cursor.execute(query, (description, video_id))

def add_video_to_playlist(video_id, playlist_id):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT title, playlists_ids FROM videos WHERE id = ?", (video_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f'Video with {video_id} does not exist')
        video_playlists = BlobList(row[1] or b'')

        cursor.execute("SELECT videos_ids FROM playlists WHERE id = ?", (playlist_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f'Playlist with {playlist_id} does not exist')
        
        videos_ids = BlobList(row[0] or b'')
        videos_ids.add(video_id)
        cursor.execute(
            "UPDATE playlists SET videos_ids = ? WHERE id = ?",
            (videos_ids.to_bytes(), playlist_id)
        )
        
        # Update video's playlists list
        video_playlists.add(playlist_id)
        cursor.execute(
            "UPDATE videos SET playlists_ids = ? WHERE id = ?",
            (video_playlists.to_bytes(), video_id)
        )

def remove_video_from_playlist(video_id, playlist_id):
    """Remove a video from a playlist by video_id and playlist_id"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT title, playlists_ids FROM videos WHERE id = ?", (video_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f'Video with id {video_id} does not exist')
        video_playlists = BlobList(row[1] or b'')

        cursor.execute("SELECT videos_ids FROM playlists WHERE id = ?", (playlist_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f'Playlist with id {playlist_id} does not exist')
        
        videos_ids = BlobList(row[0] or b'')
        videos_ids.remove(video_id)
        cursor.execute(
            "UPDATE playlists SET videos_ids = ? WHERE id = ?",
            (videos_ids.to_bytes(), playlist_id)
        )
        
        # Update video's playlists list
        video_playlists.remove(playlist_id)
        cursor.execute(
            "UPDATE videos SET playlists_ids = ? WHERE id = ?",
            (video_playlists.to_bytes(), video_id)
        )

def add_playlist_to_group(playlist_id, group_id):
    """Add a playlist to a group by updating both group and playlists tables"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT name, groups_ids FROM playlists WHERE id = ?", (playlist_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f'Playlist with id {playlist_id} does not exist')
        playlist_groups = BlobList(row[1] or b'')

        cursor.execute("SELECT playlists_ids FROM groups WHERE id = ?", (group_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f'Group with id {group_id} does not exist')
        
        playlists_ids = BlobList(row[0] or b'')
        playlists_ids.add(playlist_id)
        cursor.execute(
            "UPDATE groups SET playlists_ids = ? WHERE id = ?",
            (playlists_ids.to_bytes(), group_id)
        )
        
        # Update playlist's groups list
        playlist_groups.add(group_id)
        cursor.execute(
            "UPDATE playlists SET groups_ids = ? WHERE id = ?",
            (playlist_groups.to_bytes(), playlist_id)
        )
    

def remove_playlist_from_group(playlist_id, group_id):
    """Remove a playlist from a group by updating both group and playlists tables"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT name, groups_ids FROM playlists WHERE id = ?", (playlist_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f'Playlist with id {playlist_id} does not exist')
        playlist_groups = BlobList(row[1] or b'')

        cursor.execute("SELECT playlists_ids FROM groups WHERE id = ?", (group_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f'Group with id {group_id} does not exist')
        
        playlists_ids = BlobList(row[0] or b'')
        playlists_ids.remove(playlist_id)
        cursor.execute(
            "UPDATE groups SET playlists_ids = ? WHERE id = ?",
            (playlists_ids.to_bytes(), group_id)
        )
        
        # Update playlist's groups list
        playlist_groups.remove(group_id)
        cursor.execute(
            "UPDATE playlists SET groups_ids = ? WHERE id = ?",
            (playlist_groups.to_bytes(), playlist_id)
        )
        conn.commit()

def create_group(group_name, playlists=[]) -> int:
    """Create a new group with optional playlists and return the group_id"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Check if group with same name already exists
        cursor.execute("SELECT id FROM groups WHERE name = ?", (group_name,))
        if cursor.fetchone():
            raise AlreadyExistsError(f'Group with name {group_name} already exists')
        
        # Create playlist list
        blist = BlobList()
        for playlist_id in playlists:
            blist.add(playlist_id)
        
        cursor.execute(
            "INSERT INTO groups (name, playlists_ids) VALUES (?, ?)",
            (group_name, blist.to_bytes())
        )
        group_id = cursor.lastrowid
        
        # Add this group to each playlist's groups list
        for playlist_id in playlists:
            cursor.execute("SELECT groups_ids FROM playlists WHERE id = ?", (playlist_id,))
            row = cursor.fetchone()
            if row:
                playlist_groups = BlobList(row[0] or b'')
                playlist_groups.add(group_id)
                cursor.execute(
                    "UPDATE playlists SET groups_ids = ? WHERE id = ?",
                    (playlist_groups.to_bytes(), playlist_id)
                )
        
        return group_id

def create_playlist(playlist_name, groups=[], videos=[]) -> int:
    """Create a new playlist with optional groups and videos, return the playlist_id"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Check if playlist with same name already exists
        cursor.execute("SELECT id FROM playlists WHERE name = ?", (playlist_name,))
        if cursor.fetchone():
            raise AlreadyExistsError(f'Playlist with name {playlist_name} already exists')
        
        # Create video list for the playlist
        videos_blist = BlobList()
        for video_id in videos:
            videos_blist.add(video_id)
        
        # Create groups list for the playlist
        groups_blist = BlobList()
        for group_id in groups:
            groups_blist.add(group_id)
        
        cursor.execute(
            "INSERT INTO playlists (name, videos_ids, groups_ids) VALUES (?, ?, ?)",
            (playlist_name, videos_blist.to_bytes(), groups_blist.to_bytes())
        )
        playlist_id = cursor.lastrowid
        
        # Add playlist to each group and update their playlists_ids
        for group_id in groups:
            cursor.execute("SELECT playlists_ids FROM groups WHERE id = ?", (group_id,))
            row = cursor.fetchone()
            if row:
                group_playlists = BlobList(row[0] or b'')
                group_playlists.add(playlist_id)
                cursor.execute(
                    "UPDATE groups SET playlists_ids = ? WHERE id = ?",
                    (group_playlists.to_bytes(), group_id)
                )
        
        # Add playlist to each video's playlists list
        for video_id in videos:
            cursor.execute("SELECT playlists_ids FROM videos WHERE id = ?", (video_id,))
            row = cursor.fetchone()
            if row:
                video_playlists = BlobList(row[0] or b'')
                video_playlists.add(playlist_id)
                cursor.execute(
                    "UPDATE videos SET playlists_ids = ? WHERE id = ?",
                    (video_playlists.to_bytes(), video_id)
                )
        
        return playlist_id

    

def create_video(archive_id, title="", description="") -> int:
    """Create a new video with archive_id, title, and description, return the video_id"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Check if video already exists
        cursor.execute("SELECT id FROM videos WHERE archive_id = ?", (archive_id,))
        row = cursor.fetchone()
        if row:
            raise AlreadyExistsError(f'Video with archive_id {archive_id} already exists', item_id=row[0])
        
        # Initialize empty playlists list
        empty_blist = BlobList().to_bytes()
        
        cursor.execute(
            "INSERT INTO videos (title, description, archive_id, playlists_ids) VALUES (?, ?, ?, ?)",
            (title, description, archive_id, empty_blist)
        )
        video_id = cursor.lastrowid
        conn.commit()
        
        return video_id

def delete_group(group_id):
    """Delete a group by group_id"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT playlists_ids FROM groups WHERE id = ?", (group_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f'Group with id {group_id} does not exist')
        
        # Remove this group from all playlists it was in
        if row[0]:
            playlists_ids = BlobList(row[0]).to_list()
            for playlist_id in playlists_ids:
                cursor.execute("SELECT groups_ids FROM playlists WHERE id = ?", (playlist_id,))
                p_row = cursor.fetchone()
                if p_row and p_row[0]:
                    playlist_groups = BlobList(p_row[0])
                    playlist_groups.remove(group_id)
                    cursor.execute(
                        "UPDATE playlists SET groups_ids = ? WHERE id = ?",
                        (playlist_groups.to_bytes(), playlist_id)
                    )
        
        cursor.execute("DELETE FROM groups WHERE id = ?", (group_id,))

def delete_playlist(playlist_id):
    """Delete a playlist by playlist_id"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT groups_ids, videos_ids FROM playlists WHERE id = ?", (playlist_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f'Playlist with id {playlist_id} does not exist')
        
        # Remove this playlist from all groups it was in
        if row[0]:
            groups_ids = BlobList(row[0]).to_list()
            for group_id in groups_ids:
                cursor.execute("SELECT playlists_ids FROM groups WHERE id = ?", (group_id,))
                g_row = cursor.fetchone()
                if g_row and g_row[0]:
                    group_playlists = BlobList(g_row[0])
                    group_playlists.remove(playlist_id)
                    cursor.execute(
                        "UPDATE groups SET playlists_ids = ? WHERE id = ?",
                        (group_playlists.to_bytes(), group_id)
                    )
        
        # Remove this playlist from all videos it contained
        if row[1]:
            videos_ids = BlobList(row[1]).to_list()
            for video_id in videos_ids:
                cursor.execute("SELECT playlists_ids FROM videos WHERE id = ?", (video_id,))
                v_row = cursor.fetchone()
                if v_row and v_row[0]:
                    video_playlists = BlobList(v_row[0])
                    video_playlists.remove(playlist_id)
                    cursor.execute(
                        "UPDATE videos SET playlists_ids = ? WHERE id = ?",
                        (video_playlists.to_bytes(), video_id)
                    )
        
        cursor.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))

def delete_video(video_id):
    """Delete a video by video_id"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT playlists_ids FROM videos WHERE id = ?", (video_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f'Video with id {video_id} does not exist')
        
        # Remove this video from all playlists it was in
        if row[0]:
            playlists_ids = BlobList(row[0]).to_list()
            for playlist_id in playlists_ids:
                cursor.execute("SELECT videos_ids FROM playlists WHERE id = ?", (playlist_id,))
                p_row = cursor.fetchone()
                if p_row and p_row[0]:
                    playlist_videos = BlobList(p_row[0])
                    playlist_videos.remove(video_id)
                    cursor.execute(
                        "UPDATE playlists SET videos_ids = ? WHERE id = ?",
                        (playlist_videos.to_bytes(), playlist_id)
                    )
        
        cursor.execute("DELETE FROM videos WHERE id = ?", (video_id,))

def get_unlisted_videos():
    """Get all videos that are not in any playlist"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Get all video IDs from playlists
        cursor.execute("SELECT videos_ids FROM playlists")
        rows = cursor.fetchall()
        
        used_video_ids = set()
        for row in rows:
            if row[0]:
                blist = BlobList(row[0])
                used_video_ids.update(blist.to_list())
        
        # Get all videos not in the used set
        if used_video_ids:
            placeholders = ','.join('?' * len(used_video_ids))
            query = f"SELECT id, title, description, archive_id FROM videos WHERE id NOT IN ({placeholders})"
            cursor.execute(query, tuple(used_video_ids))
        else:
            cursor.execute("SELECT id, title, description, archive_id FROM videos")
        
        rows = cursor.fetchall()
        return [{
            "id_": row[0],
            "title": row[1],
            "description": row[2],
            "archive_id": row[3]
        } for row in rows]

def get_unlisted_playlists():
    """Get all playlists that are not in any group"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Get all playlist IDs from groups
        cursor.execute("SELECT playlists_ids FROM groups")
        rows = cursor.fetchall()
        
        used_playlist_ids = set()
        for row in rows:
            if row[0]:
                blist = BlobList(row[0])
                used_playlist_ids.update(blist.to_list())
        
        # Get all playlists not in the used set
        if used_playlist_ids:
            placeholders = ','.join('?' * len(used_playlist_ids))
            query = f"SELECT id, name FROM playlists WHERE id NOT IN ({placeholders})"
            cursor.execute(query, tuple(used_playlist_ids))
        else:
            cursor.execute("SELECT id, name FROM playlists")
        
        rows = cursor.fetchall()
        return [{
            "id_": row[0],
            "name": row[1]
        } for row in rows]

def get_groups_of_playlist(playlist_id):
    """Get all groups that contain a specific playlist"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT groups_ids FROM playlists WHERE id = ?", (playlist_id,))
        row = cursor.fetchone()
        if not row or not row[0]:
            return []
        
        groups_ids = BlobList(row[0]).to_list()
        
        # Get all groups with these IDs
        if groups_ids:
            placeholders = ','.join('?' * len(groups_ids))
            query = f"SELECT id, name FROM groups WHERE id IN ({placeholders})"
            cursor.execute(query, tuple(groups_ids))
        else:
            cursor.execute("SELECT id, name FROM groups WHERE 1=0")
        
        rows = cursor.fetchall()
        return [{
            "id_": row[0],
            "name": row[1]
        } for row in rows]

def get_playlists_of_video(video_id):
    """Get all playlists that contain a specific video"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT playlists_ids FROM videos WHERE id = ?", (video_id,))
        row = cursor.fetchone()
        if not row or not row[0]:
            return []
        
        playlists_ids = BlobList(row[0]).to_list()
        
        # Get all playlists with these IDs
        if playlists_ids:
            placeholders = ','.join('?' * len(playlists_ids))
            query = f"SELECT id, name FROM playlists WHERE id IN ({placeholders})"
            cursor.execute(query, tuple(playlists_ids))
        else:
            cursor.execute("SELECT id, name FROM playlists WHERE 1=0")
        
        rows = cursor.fetchall()
        return [{
            "id_": row[0],
            "name": row[1]
        } for row in rows]

def do_all():
    clear_db()
    init_db()
    update_db()
    # print_db()

if __name__=="__main__":
    # update_db()
    do_all()