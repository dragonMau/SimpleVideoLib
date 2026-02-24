"""
Video library database - Pure data layer with no external dependencies.
Supports hierarchical organization: Groups → Playlists → Videos
"""

import sqlite3
from typing import List, Dict, Optional
from contextlib import contextmanager
from config import DB_PATH


# ============================================================================
# Database Connection
# ============================================================================

@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ============================================================================
# Schema Initialization
# ============================================================================

def init_db():
    """Initialize database schema with proper junction tables."""
    with get_db() as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS playlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                archive_id TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS playlist_groups (
                playlist_id INTEGER NOT NULL,
                group_id INTEGER NOT NULL,
                PRIMARY KEY (playlist_id, group_id),
                FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
                FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS video_playlists (
                video_id INTEGER NOT NULL,
                playlist_id INTEGER NOT NULL,
                PRIMARY KEY (video_id, playlist_id),
                FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
                FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_playlist_groups_group ON playlist_groups(group_id);
            CREATE INDEX IF NOT EXISTS idx_video_playlists_playlist ON video_playlists(playlist_id);
        ''')


def clear_db():
    """Drop all tables. USE WITH CAUTION."""
    with get_db() as conn:
        conn.executescript('''
            DROP TABLE IF EXISTS video_playlists;
            DROP TABLE IF EXISTS playlist_groups;
            DROP TABLE IF EXISTS videos;
            DROP TABLE IF EXISTS playlists;
            DROP TABLE IF EXISTS groups;
        ''')


# ============================================================================
# Groups - CRUD
# ============================================================================

def get_groups() -> List[Dict]:
    """Get all groups."""
    with get_db() as conn:
        rows = conn.execute('SELECT id, name FROM groups ORDER BY name').fetchall()
        return [{"id_": row["id"], "name": row["name"]} for row in rows]


def create_group(name: str) -> int:
    """Create a new group. Returns group_id."""
    with get_db() as conn:
        cursor = conn.execute('INSERT INTO groups (name) VALUES (?)', (name,))
        if cursor.lastrowid is None:
            raise Exception("Failed to create group")
        return cursor.lastrowid


def update_group(group_id: int, name: str):
    """Rename a group."""
    with get_db() as conn:
        conn.execute('UPDATE groups SET name = ? WHERE id = ?', (name, group_id))


def delete_group(group_id: int):
    """Delete a group (associations are cascade deleted)."""
    with get_db() as conn:
        conn.execute('DELETE FROM groups WHERE id = ?', (group_id,))

def assign_playlist_to_group(group_id: int, playlist_id: int):
    """Add a playlist to a group (many-to-many)."""
    with get_db() as conn:
        conn.execute(
            'INSERT OR IGNORE INTO playlist_groups (playlist_id, group_id) VALUES (?, ?)',
            (playlist_id, group_id)
        )

def remove_playlist_from_group(group_id: int, playlist_id: int):
    """Remove a playlist from a group."""
    with get_db() as conn:
        conn.execute(
            'DELETE FROM playlist_groups WHERE playlist_id = ? AND group_id = ?',
            (playlist_id, group_id)
        )

# ============================================================================
# Playlists - CRUD
# ============================================================================

def get_playlists(group_id: int) -> List[Dict]:
    """Get all playlists in a specific group."""
    with get_db() as conn:
        rows = conn.execute('''
            SELECT p.id, p.name
            FROM playlists p
            JOIN playlist_groups pg ON p.id = pg.playlist_id
            WHERE pg.group_id = ?
            ORDER BY p.name
        ''', (group_id,)).fetchall()
        return [{"id_": row["id"], "name": row["name"]} for row in rows]


def get_orphaned_playlists() -> List[Dict]:
    """Get playlists not assigned to any group."""
    with get_db() as conn:
        rows = conn.execute('''
            SELECT p.id, p.name
            FROM playlists p
            LEFT JOIN playlist_groups pg ON p.id = pg.playlist_id
            WHERE pg.group_id IS NULL
            ORDER BY p.name
        ''').fetchall()
        return [{"id_": row["id"], "name": row["name"]} for row in rows]


def create_playlist(name: str) -> int:
    """Create a new playlist. Returns playlist_id."""
    with get_db() as conn:
        cursor = conn.execute('INSERT INTO playlists (name) VALUES (?)', (name,))
        if cursor.lastrowid is None:
            raise Exception("Failed to create playlist")
        return cursor.lastrowid


def update_playlist(playlist_id: int, name: str):
    """Rename a playlist."""
    with get_db() as conn:
        conn.execute('UPDATE playlists SET name = ? WHERE id = ?', (name, playlist_id))


def delete_playlist(playlist_id: int):
    """Delete a playlist (associations are cascade deleted)."""
    with get_db() as conn:
        conn.execute('DELETE FROM playlists WHERE id = ?', (playlist_id,))



def assign_video_to_playlist(playlist_id: int, video_id: int):
    """Add a video to a playlist (many-to-many)."""
    with get_db() as conn:
        conn.execute(
            'INSERT OR IGNORE INTO video_playlists (video_id, playlist_id) VALUES (?, ?)',
            (video_id, playlist_id)
        )


def remove_video_from_playlist(playlist_id: int, video_id: int):
    """Remove a video from a playlist."""
    with get_db() as conn:
        conn.execute(
            'DELETE FROM video_playlists WHERE video_id = ? AND playlist_id = ?',
            (video_id, playlist_id)
        )


# ============================================================================
# Videos - CRUD
# ============================================================================

def get_videos(playlist_id: int) -> List[Dict]:
    """Get all videos in a specific playlist."""
    with get_db() as conn:
        rows = conn.execute('''
            SELECT v.id, v.title, v.description, v.archive_id
            FROM videos v
            JOIN video_playlists vp ON v.id = vp.video_id
            WHERE vp.playlist_id = ?
            ORDER BY v.title
        ''', (playlist_id,)).fetchall()
        return [{
            "id_": row["id"],
            "title": row["title"],
            "description": row["description"],
            "archive_id": row["archive_id"]
        } for row in rows]


def get_orphaned_videos() -> List[Dict]:
    """Get videos not assigned to any playlist."""
    with get_db() as conn:
        rows = conn.execute('''
            SELECT v.id, v.title, v.description, v.archive_id
            FROM videos v
            LEFT JOIN video_playlists vp ON v.id = vp.video_id
            WHERE vp.playlist_id IS NULL
            ORDER BY v.title
        ''').fetchall()
        return [{
            "id_": row["id"],
            "title": row["title"],
            "description": row["description"],
            "archive_id": row["archive_id"]
        } for row in rows]


def create_video(title: str, description: str, archive_id: str) -> int:
    """Create a new video. Returns video_id."""
    with get_db() as conn:
        cursor = conn.execute(
            'INSERT INTO videos (title, description, archive_id) VALUES (?, ?, ?)',
            (title, description, archive_id)
        )
        if cursor.lastrowid is None:    
            raise Exception("Failed to create video")
        return cursor.lastrowid


def update_video(video_id: int, title: Optional[str] = None, 
                 description: Optional[str] = None, archive_id: Optional[str] = None):
    """Update video metadata. Only updates provided fields."""
    updates = []
    params = []
    
    if title is not None:
        updates.append('title = ?')
        params.append(title)
    if description is not None:
        updates.append('description = ?')
        params.append(description)
    if archive_id is not None:
        updates.append('archive_id = ?')
        params.append(archive_id)
    
    if not updates:
        return
    
    params.append(video_id)
    with get_db() as conn:
        conn.execute(
            f'UPDATE videos SET {", ".join(updates)} WHERE id = ?',
            params
        )


def delete_video(video_id: int):
    """Delete a video (associations are cascade deleted)."""
    with get_db() as conn:
        conn.execute('DELETE FROM videos WHERE id = ?', (video_id,))


# ============================================================================
# Utility Functions
# ============================================================================

def get_video_by_archive_id(archive_id: str) -> Optional[Dict]:
    """Find a video by its archive_id."""
    with get_db() as conn:
        row = conn.execute(
            'SELECT id, title, description, archive_id FROM videos WHERE archive_id = ?',
            (archive_id,)
        ).fetchone()
        
        if row:
            return {
                "id_": row["id"],
                "title": row["title"],
                "description": row["description"],
                "archive_id": row["archive_id"]
            }
        return None


def get_all_videos() -> List[Dict]:
    """Get all videos (for admin panel)."""
    with get_db() as conn:
        rows = conn.execute(
            'SELECT id, title, description, archive_id FROM videos ORDER BY title'
        ).fetchall()
        return [{
            "id_": row["id"],
            "title": row["title"],
            "description": row["description"],
            "archive_id": row["archive_id"]
        } for row in rows]


if __name__ == "__main__":
    print("Database service is to meant to be standalone")