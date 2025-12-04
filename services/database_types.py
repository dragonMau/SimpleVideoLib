from pydantic import BaseModel, ConfigDict
from typing import List

class Video(BaseModel):
    # model_config = ConfigDict(arbitrary_types_allowed=True)
    id_: int = 0
    title: str = "VideoTitle"
    description: str = "VideoDescription"
    archive_id: str = "archiveid"
    playlists_ids: List[int] = []
    uploader: str = ""

    def json(self, show_playlists=False):
        j = {
            "id_": self.id_,
            "title": self.title,
            "description": self.description,
            "archive_id": self.archive_id
        }
        if show_playlists: j["playlists_ids"] = self.playlists_ids
        return j
    
    def __str__(self):
        return super().__repr__()

class Playlist(BaseModel):
    # model_config = ConfigDict(arbitrary_types_allowed=True)
    id_: int =  0
    name: str = "PlaylistName"
    videos_ids: List[int] = []
    groups_ids: List[int] = []

    def json(self, show_videos_ids=False, show_groups_ids=False):
        j = {
            "id_": self.id_,
            "name": self.name,
        }
        if show_videos_ids: j["videos_ids"] = self.videos_ids
        if show_groups_ids: j["groups_ids"] = self.groups_ids
        return j

    def __str__(self):
        return super().__repr__()

class Group(BaseModel):
    # model_config = ConfigDict(arbitrary_types_allowed=True)
    id_: int = 0
    name: str = "GroupName"
    playlists_ids: List[int] = []

    def json(self, show_playlists_ids=False):
        j = {
            "id_": self.id_,
            "name": self.name
        }
        if show_playlists_ids: j["playlists_ids"] = self.playlists_ids
        return j

    def __str__(self):
        return super().__repr__()

