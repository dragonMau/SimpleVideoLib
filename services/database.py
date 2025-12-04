from functools import wraps
from database_types import Video, Playlist, Group
from database_exceptions import *
from pydantic import BaseModel, ConfigDict
from typing import List
import sqlite3
import internetarchive as ia
from config import trusted_uploaders, DB_PATH, DB_URI


def connected(func):
    @wraps(func)
    def wrapper(self: "DBManager | DBItem", *args, **kwargs):
        with sqlite3.connect(self.db_path, uri=self.db_uri) as conn:
            cursor = conn.cursor()
            return func(self, *args, cursor=cursor, **kwargs)
    return wrapper

class DBManager:
    log_level = 1

    def __init__(self, db_path=None, db_uri=None):
        self.db_path = db_path if db_path is not None else DB_PATH
        self.db_uri = db_uri if db_path is not None else DB_URI
    
    def log(self, *message, **kwargs):
        if self.log_level == 1:
            print('DBMan:', *message, **kwargs)
    
    
    @connected
    def init_db(self, cursor: sqlite3.Cursor):
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT DEFAULT '',
            description TEXT DEFAULT '', 
            archive_id TEXT NOT NULL
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS playlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT DEFAULT ''
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT DEFAULT ''
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS playlist_videos (
            playlist_id INTEGER NOT NULL,
            video_id INTEGER NOT NULL,
            PRIMARY KEY (playlist_id, video_id),
            FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
            FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE
        );
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS group_playlists (
            group_id INTEGER NOT NULL,
            playlist_id INTEGER NOT NULL,
            PRIMARY KEY (group_id, playlist_id),
            FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
            FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE
        );
        ''')
    
    @connected
    def clear_db(self, cursor: sqlite3.Cursor):
        cursor.execute("DROP TABLE IF EXISTS videos")
        cursor.execute("DROP TABLE IF EXISTS playlists")
        cursor.execute("DROP TABLE IF EXISTS groups")

        self.log("Database cleared.")

    @connected
    def print_db(self, cursor: sqlite3.Cursor):
        # Get list of tables in the DB
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
        tables = [r[0] for r in cursor.fetchall()]

        def format_table(table_name: str):
            # get column info
            cursor.execute(f"PRAGMA table_info({table_name})")
            cols = [c[1] for c in cursor.fetchall()]  # name is at index 1

            # fetch rows
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()

            # compute column widths
            col_widths = [len(c) for c in cols]
            for row in rows:
                for i, cell in enumerate(row):
                    s = '' if cell is None else str(cell)
                    if len(s) > col_widths[i]:
                        col_widths[i] = len(s)

            # compute full width and draw header
            sep = ' | '
            header = sep.join(col.ljust(col_widths[i]) for i, col in enumerate(cols))
            title = ('= '+table_name.title()+' =').center(len(header), '=')
            total_width = len(title)

            print(f"=={title}==")
            print('| ' + header.ljust(total_width, ' ') + ' |')
            print('|-' + '-'*total_width + '-|')
            for row in rows:
                cells = [ ('' if c is None else str(c)).ljust(col_widths[i]) for i, c in enumerate(row) ]
                print('| ' + sep.join(cells).ljust(total_width, ' ')+' |')
            print(f"=={'='*total_width}==")

        for t in tables:
            format_table(t)

    @connected
    def create_video(self, archive_id, title="", description="", cursor: sqlite3.Cursor=None) -> int:
        """Create a new video with archive_id, title, and description, return the video_id"""
        # record archive video to database.            
        # Check if video already exists
        cursor.execute("SELECT id FROM videos WHERE archive_id = ?", (archive_id,))
        row = cursor.fetchone()
        if row:
            raise AlreadyExistsError(f'Video with archive_id {archive_id} already exists', item_id=row[0])
        
        cursor.execute(
            "INSERT INTO videos (title, description, archive_id) VALUES (?, ?, ?)",
            (title, description, archive_id)
        )
        video_id = cursor.lastrowid            
        return video_id

    @connected
    def create_playlist(self, playlist_name, cursor: sqlite3.Cursor) -> int:
        """Create a new playlist"""
        # make playlist label
        # Check if playlist with same name already exists
        cursor.execute("SELECT id FROM playlists WHERE name = ?", (playlist_name,))
        if cursor.fetchone():
            raise AlreadyExistsError(f'Playlist with name {playlist_name} already exists')
        
        cursor.execute(
            "INSERT INTO playlists (name) VALUES (?)",
            (playlist_name,)
        )
        playlist_id = cursor.lastrowid            
        return playlist_id
    
    @connected
    def create_group(self, group_name, cursor: sqlite3.Cursor) -> int:
        """Create a new group and return the group_id"""
        # Check if group with same name already exists
        cursor.execute("SELECT id FROM groups WHERE name = ?", (group_name,))
        if cursor.fetchone():
            raise AlreadyExistsError(f'Group with name {group_name} already exists')
        
        cursor.execute(
            "INSERT INTO groups (name) VALUES (?)",
            (group_name,)
        )
        group_id = cursor.lastrowid
        return group_id
    

class DBItem:
    """Base mixin describing DB item operations and context-manager support.

    Subclasses should implement `create`, `load`, `save`, `delete`.
    Using `with DBX(id) as obj:` will yield the object and call `save()` on exit
    if no exception occurred.
    """
    # model_config = ConfigDict(arbitrary_types_allowed=True)
    # db_man: DataBaseManager
    db_path: str = ""
    db_uri: bool = ""
    def __init__(self, dbman: DBManager = None):
        # self.db_man = dbman
        self.db_path = dbman.db_path if dbman is not None else DB_PATH
        self.db_uri = dbman.db_uri if dbman is not None else DB_URI
        print("i", self.db_path, self.db_uri)

    __pydantic_fields_set__ = set()
    @classmethod
    def create(cls, *args, **kwargs):
        raise NotImplementedError()

    def load(self):
        raise NotImplementedError()

    def save(self):
        raise NotImplementedError()

    def delete(self):
        raise NotImplementedError()

    def __enter__(self):
        # ensure loaded if load exists
        try:
            self.load()
        except Exception:
            pass
        return self

    def __exit__(self, exc_type, exc, tb):
        # on successful exit, persist
        if exc_type is None:
            try:
                self.save()
            except Exception:
                pass
        # do not suppress exceptions
        return False

class DBVideo(DBItem, Video):
    _original_playlists_ids: List[int]
    def __init__(self, id_: int, dbman: DBManager = None):
        DBItem.__init__(self, dbman)
        Video.__init__(self)
        self.id_ = id_
        print("d",dbman.db_path, dbman.db_uri)
        print("s",self.db_path, self.db_uri)
        self.load()

    @classmethod
    def create(cls, dbman: DBManager, archive_id):
        return cls(dbman.create_video(archive_id), dbman)

    @connected
    def load(self, cursor: sqlite3.Cursor=None):
        video_id = self.id_
        cursor.execute(
            "SELECT title, description, archive_id FROM videos WHERE id = ?",
            (video_id,)
        )
        row = cursor.fetchone()
        if row is None:
            raise ItemNotExistsError(f"Item with {video_id=} is not in database")
        
        self.title = row[0]
        self.description = row[1]
        self.archive_id = row[2]

        cursor.execute(
            "SELECT playlist_id FROM playlist_videos WHERE video_id = ?",
            (video_id,)
        )
        self.playlists_ids = [row[0] for row in cursor.fetchall()]

        self._original_playlists_ids = self.playlists_ids.copy()
    
    @connected
    def save(self, cursor: sqlite3.Cursor=None):
        # add myself to where i was not and now i am
        # remove myself from where i was and now i am not
        old_set = set(self._original_playlists_ids)
        new_set = set(self.playlists_ids)

        # to add: insert into playlist_videos
        for playlist_id in new_set - old_set:
            cursor.execute(
                "INSERT OR IGNORE INTO playlist_videos (playlist_id, video_id) VALUES (?, ?)",
                (playlist_id, self.id_)
            )

        # to remove: delete from playlist_videos
        for playlist_id in old_set - new_set:
            cursor.execute(
                "DELETE FROM playlist_videos WHERE playlist_id = ? AND video_id = ?",
                (playlist_id, self.id_)
            )

        # update core video fields
        cursor.execute(
            "UPDATE videos SET title = ?, description = ?, archive_id = ? WHERE id = ?",
            (self.title, self.description, self.archive_id, self.id_)
        )
        # refresh original
        self._original_playlists_ids = list(self.playlists_ids)
    
    
    @connected
    def delete(self, cursor: sqlite3.Cursor):
        # remove join-table entries and delete the video
        cursor.execute("DELETE FROM playlist_videos WHERE video_id = ?", (self.id_,))
        cursor.execute("DELETE FROM videos WHERE id = ?", (self.id_,))


# continue with adding DBPlaylist, DBGroup
# then add other functions for api.
class DBPlaylist(DBItem, Playlist):
    _original_videos_ids: List[int]
    _original_groups_ids: List[int]
    def __init__(self, id_: int, dbman: DBManager = None):
        DBItem.__init__(self, dbman)
        Playlist.__init__(self)
        self.id_ = id_
        self.load()

    @classmethod
    def create(cls, dbman: DBManager, name: str):
        return cls(dbman.create_playlist(name), dbman)

    @connected
    def load(self, cursor: sqlite3.Cursor=None):
        cursor.execute("SELECT name FROM playlists WHERE id = ?", (self.id_,))
        row = cursor.fetchone()
        if row is None:
            raise ItemNotExistsError(f"Playlist {self.id_} not found")
        self.name = row[0]
        cursor.execute("SELECT video_id FROM playlist_videos WHERE playlist_id = ?", (self.id_,))
        self.videos_ids = [r[0] for r in cursor.fetchall()]
        cursor.execute("SELECT group_id FROM group_playlists WHERE playlist_id = ?", (self.id_,))
        self.groups_ids = [r[0] for r in cursor.fetchall()]
        self._original_videos_ids = list(self.videos_ids)
        self._original_groups_ids = list(self.groups_ids)

    @connected
    def save(self, cursor: sqlite3.Cursor=None):
        cursor.execute("UPDATE playlists SET name = ? WHERE id = ?", (self.name, self.id_))
        # sync videos
        old_v = set(self._original_videos_ids)
        new_v = set(self.videos_ids)
        for vid in new_v - old_v:
            cursor.execute("INSERT OR IGNORE INTO playlist_videos (playlist_id, video_id) VALUES (?, ?)", (self.id_, vid))
        for vid in old_v - new_v:
            cursor.execute("DELETE FROM playlist_videos WHERE playlist_id = ? AND video_id = ?", (self.id_, vid))
        # sync groups
        old_g = set(self._original_groups_ids)
        new_g = set(self.groups_ids)
        for gid in new_g - old_g:
            cursor.execute("INSERT OR IGNORE INTO group_playlists (group_id, playlist_id) VALUES (?, ?)", (gid, self.id_))
        for gid in old_g - new_g:
            cursor.execute("DELETE FROM group_playlists WHERE group_id = ? AND playlist_id = ?", (gid, self.id_))
        self._original_videos_ids = list(self.videos_ids)
        self._original_groups_ids = list(self.groups_ids)

    @connected
    def delete(self, cursor: sqlite3.Cursor=None):
        cursor.execute("DELETE FROM playlist_videos WHERE playlist_id = ?", (self.id_,))
        cursor.execute("DELETE FROM group_playlists WHERE playlist_id = ?", (self.id_,))
        cursor.execute("DELETE FROM playlists WHERE id = ?", (self.id_,))


class DBGroup(DBItem, Group):
    _original_playlists_ids: List[int]
    def __init__(self, id_: int, dbman: DBManager = None):
        DBItem.__init__(self, dbman)
        Group.__init__(self)
        self.id_ = id_
        self.load()

    @classmethod
    def create(cls, dbman: DBManager, name: str):
        return cls(dbman.create_group(name), dbman)

    @connected
    def load(self, cursor: sqlite3.Cursor=None):
        cursor.execute("SELECT name FROM groups WHERE id = ?", (self.id_,))
        row = cursor.fetchone()
        if row is None:
            raise ItemNotExistsError(f"Group {self.id_} not found")
        self.name = row[0]
        cursor.execute("SELECT playlist_id FROM group_playlists WHERE group_id = ?", (self.id_,))
        self.playlists_ids = [r[0] for r in cursor.fetchall()]
        self._original_playlists_ids = list(self.playlists_ids)

    @connected
    def save(self, cursor: sqlite3.Cursor=None):
        cursor.execute("UPDATE groups SET name = ? WHERE id = ?", (self.name, self.id_))
        old_set = set(self._original_playlists_ids)
        new_set = set(self.playlists_ids)
        for pid in new_set - old_set:
            cursor.execute("INSERT OR IGNORE INTO group_playlists (group_id, playlist_id) VALUES (?, ?)", (self.id_, pid))
        for pid in old_set - new_set:
            cursor.execute("DELETE FROM group_playlists WHERE group_id = ? AND playlist_id = ?", (self.id_, pid))
        self._original_playlists_ids = list(self.playlists_ids)

    @connected
    def delete(self, cursor: sqlite3.Cursor=None):
        cursor.execute("DELETE FROM group_playlists WHERE group_id = ?", (self.id_,))
        cursor.execute("DELETE FROM groups WHERE id = ?", (self.id_,))





class Hmm:
    def link_video_playlist(self, video_id, playlist_id): ...
    def link_playlist_group(self, playlist_id, group_id): ...

    def get_video_by_id(self, video_id): ...
    def get_playlist_by_id(self, playlist_id): ...
    def get_group_by_id(self, group_id): ...

    def get_videos_by_playlist(self, playlist_id=None): ... # None = unlinked videos
    def get_playlists_by_video(self, video_id=None): ... # None = empty playlists
    def get_playlists_by_group(self, group_id=None): ... # None = unlinked playlists
    def get_groups_by_playlist(self, playlist_id=None): ... # None = empty groups
    def get_all_videos(self): ...
    def get_all_playlists(self): ...
    def get_all_groups(self): ...



if __name__ == "__main__":
    dbman = DBManager()
    dbman.init_db()
    ply1 = dbman.create_playlist("ply1")
    print("adding video\n")
    # dbman.print_db()
    # print()

    # DBVideo.create(dbman, "vid0")
    # dbman.video.create("vid0")
    with DBVideo.create(dbman, "vid0") as vid:
        vid.title = "Hello"
        vid.description = "Very longer description"
        vid.playlists_ids.append(ply1)

    with DBVideo.create(dbman, "vid1") as vid:
        try:
            vid.title = "World!"
            vid.playlists_ids.append(3) # should just raise when invalid playlist, when attmpting to save, not immediately
            vid2 = vid.id_
        except Exception as e:
            print(e)

    dbman.print_db()
    print()
    with DBVideo(vid2) as vid:
        print(vid.playlists_ids)
        # also i need some methods to list videos and groups with their names, like get_videos() methods ig
    