from flask import Flask, jsonify, make_response, request, send_from_directory, abort
import os
from pythings import BlobList
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List
import sqlite3
import internetarchive as ia

load_dotenv()

trusted_uploaders = [
    "m.seligey321@gmail.com"
]

class Video(BaseModel):
    id_: int = 0
    title: str = "VideoTitle"
    description: str = "VideoDescription"
    archive_id: str = "archiveid"
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
    with sqlite3.connect("archive.db") as conn:
        cursor = conn.cursor()

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT, 
            archive_id TEXT
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS playlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            videos_ids BLOB -- int32[]
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            playlists_ids BLOB -- int32[]
        )
        ''')

def clear_db():
    with sqlite3.connect("archive.db") as conn:
        cursor = conn.cursor()

        cursor.execute("DELETE FROM videos")
        cursor.execute("DELETE FROM playlists")
        cursor.execute("DELETE FROM groups")

    print("Database cleared.")

def update_playlist(playlist: str, vidid) -> int | None:
    if not playlist or playlist.endswith(':'):
        return None

    tree = [e for e in playlist.split(':') if e]
    playlist_name = tree.pop() if tree else None
    group_name = tree.pop() if tree else None

    with sqlite3.connect("archive.db") as conn:
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

def add_video(vid: Video):
    with sqlite3.connect("archive.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM videos WHERE archive_id = ?", 
            (vid.archive_id,)
        )
        row = cursor.fetchone()
        print('add video exists:', row)
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


def add_to_db(vid: Video, playlists: str):
    vidid = add_video(vid)
    for pl in playlists.split(';'):
        if not pl: continue
        update_playlist(pl, vidid)
        
def update_db():
    query = (
        'Subject:"chasidusTV" AND '
        # 'Uploader:"m.seligey321@gmail.com" AND '
        'Mediatype:movies'
    )
    fields=[
        'identifier',
        'title',
        'creator',
        'date',
        'mediatype',
        'subject',
        'description'
    ]
    params = {
    'fl[]': fields,  # fields to fetch
    'rows': 10,      # number of results per page
    'page': 1        # starting page
}
    while True:
        print(query)
        search = ia.search_items(
            query, 
            params=params
        )
        print(search)
        results = list(search)
        if not results: break
        params['page'] += 1
        for s in results:
            id_ = s["identifier"]
            print(id_, end=': ')
            item = ia.get_item(id_)
            vid = Video(**(item.metadata | s), archive_id=id_)
            playlists = item.metadata.get("playlists")
            print(vid)
            print('playlists:', playlists)
            if item.metadata.get("uploader") in trusted_uploaders:
                add_to_db(vid, playlists)
            else:
                print("not mine, uploader:", item.metadata.get("uploader"))

def print_db():
    with sqlite3.connect('archive.db') as conn:
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
            cursor.execute(f"SELECT * FROM {table_name};")
            rows = cursor.fetchall()

            # Print each row
            for row in rows:
                print(row)

def get_videos(playlist_id):  # get videos of a playlist
    with sqlite3.connect("archive.db") as conn:
        cursor = conn.cursor()

        # Get videos_ids blob
        cursor.execute("SELECT videos_ids FROM playlists WHERE id = ?", (playlist_id,))
        row = cursor.fetchone()
        if not row or not row[0]:
            return []

        blist = BlobList(row[0])
        video_ids = blist.to_list()

        # Use SQL IN to fetch all videos
        query = f"SELECT id, title, description, archive_id FROM videos WHERE id IN ({','.join('?' for _ in video_ids)})"
        cursor.execute(query, video_ids)
        rows = cursor.fetchall()

        return [{
            "id_": row[0],
            "title": row[1],
            "description": row[2],
            "archive_id": row[3]
        } for row in rows]

def get_playlists(group_id):  # get playlists of a group
    with sqlite3.connect("archive.db") as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT playlists_ids FROM groups WHERE id = ?", (group_id,))
        row = cursor.fetchone()
        if not row or not row[0]:
            return []

        blist = BlobList(row[0])
        playlist_ids = blist.to_list()

        query = f"SELECT id, name FROM playlists WHERE id IN ({','.join('?' for _ in playlist_ids)})"
        cursor.execute(query, playlist_ids)
        rows = cursor.fetchall()

        return [{
            "id_": row[0], 
            "name": row[1]
        } for row in rows]


    
def get_groups(): # al
    with sqlite3.connect("archive.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM groups")
        rows = cursor.fetchall()
        return [{
            "id_": row[0], 
            "name": row[1]
        } for row in rows]

def do_all():
    init_db()
    clear_db()
    update_db()
    # print_db()

if __name__=="__main__":
    do_all()