async function fetchData(url) {
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`Failed to fetch content from ${url}`);
    }
    const data = await response.json();
    return data;
}
async function postData(url, data) {
    const csrf_token = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrf_token,
            },
            body: JSON.stringify(data)
        }
    )
    if (!response.ok) {
        throw new Error(`Failed to post content to ${url}`);
    }
    const answer = await response.json();
    return answer; 
}

// Function to create group elements
function createGroupElement(groupsList, groupTemplate, group_id, group_name) {
    const groupItem = groupTemplate.cloneNode(true);
    groupItem.id = `group_${group_id}`;
    const groupName = groupItem.querySelector(".group-item-name");
    const groupCheckbox = groupItem.querySelector(".group-dropdown");
    groupName.textContent = group_name;

    const playlistsWrap = groupItem.querySelector(".playlists");
    const playlistsList = groupItem.querySelector(".playlists-list");

    groupCheckbox.addEventListener("change", async () => {
        if (groupCheckbox.checked) {
            document.querySelectorAll(".group-dropdown").forEach((otherCheckbox) => {
                if (otherCheckbox !== groupCheckbox && otherCheckbox.checked) {
                    otherCheckbox.checked = false;
                    otherCheckbox.dispatchEvent(new Event("change", { bubbles: true }));
                }
            });

            const loadingIndicator = document
                .getElementById("loading_indicator_template")
                .content.firstElementChild
                .cloneNode(true);
            playlistsList.appendChild(loadingIndicator);
            playlistsWrap.style.height = playlistsList.scrollHeight+1 + "px";
            
            await initPlaylistElements(playlistsList, group_id);
            
            loadingIndicator.remove();
            playlistsWrap.style.height = playlistsList.scrollHeight+1 + "px";

        } else {
            playlistsWrap.style.height = "0";
        }
    });

    groupName.addEventListener("click", () => {
        groupCheckbox.checked = !groupCheckbox.checked;
        groupCheckbox.dispatchEvent(new Event("change", { bubbles: true }));
    });
    
    playlistsWrap.addEventListener('transitionend', function handler(e) {
        if (e.propertyName === 'height' && !groupCheckbox.checked) {
            playlistsList.innerHTML = '';
        }
    });
    groupsList.appendChild(groupItem);
}

// createPlaylistElement(playlistsList, playlistTemplate, playlist.id_, playlist.name)
function createPlaylistElement(playlistsList, playlistTemplate, playlist_id, playlist_name) {
    const playlistItem = playlistTemplate.cloneNode(true);
    playlistItem.id = `playlist_${playlist_id}`;
    const playlistName = playlistItem.querySelector(".playlist-item-name");
    playlistName.innerHTML = `${playlist_name}`;

    playlistItem.addEventListener("click", async () => {

        const videoHead = document.querySelector("#videos_title");
        const group_name = playlistItem.closest(".group-item").querySelector(".group-item-name").textContent;
        
        playlistName.innerHTML = `${playlist_name} <span class="spinner"></spinner>`;
        await initVideoElemetns(playlist_id);
        videoHead.textContent = `${group_name} → ${playlist_name}`;
        playlistName.innerHTML = `${playlist_name}`;

        document.querySelectorAll(".selected").forEach(e => {
            e.classList.remove("selected");
        });
        playlistItem.classList.add("selected");
        
        videoHead.scrollIntoView({
            behavior: "smooth",
            block: "start",
        });
    });

    playlistsList.appendChild(playlistItem);
}

//createVideoElement(videoList, videoTemplate, video.id_, video.title, video.description, video.archive_id )
function createVideoElement(videoList, videoTemplate, video_id, video_title, video_description, archive_id) {
    const videoItem = videoTemplate.cloneNode(true);
    videoItem.id = `video_${video_id}`;
    const videoTitle = videoItem.querySelector(".video-item-title");
    videoTitle.textContent = video_title; // then change to title
    const videoDescription = videoItem.querySelector(".video-item-description");
    videoDescription.textContent = video_description;
    const videoImage = videoItem.querySelector(".video-item-image");

    videoImage.src = `/thumb/${archive_id}`;

    videoItem.dataset.archive_id = archive_id;

    videoItem.addEventListener("click", () => {
        selectVideo(videoItem);
    });

    videoList.appendChild(videoItem);
}

function selectVideo(videoItem) {
    const videoPathText = document.getElementById("video_path_text");

    videoPathText.textContent = document.getElementById("videos_title").textContent;
    videoPathText.href = "#";

    const playerIframe = document.getElementById("player_iframe");    
    playerIframe.scrollIntoView({
        behavior: "smooth",
        block: "center",
    });
    playerIframe.src = `https://archive.org/embed/${videoItem.dataset.archive_id}&autoplay=1`;
    const videoName = document.getElementById("video_name");
    videoName.textContent = videoItem.querySelector('.video-item-title').textContent;
    const videoDescription = document.getElementById("video_description");
    videoDescription.textContent = videoItem.querySelector('.video-item-description').textContent;
}

async function initVideoElemetns(playlist_id) {
    const video_data = await fetchData(`/playlists/${playlist_id}/videos`);
    /*{
        "type": "videos list",
        "items": [
            {
                "id_": 0,
                "title": "VideoTitle",
                "description": "VideoDEscription".
                "archive_id": "archiveid"
            }
        ]
    }*/
    const videoList = document.getElementById("videos_list");
    const videoTemplate = document.getElementById("video_item_template").content.firstElementChild;
    videoList.innerHTML = '';
    video_data.items.forEach(video => {
        createVideoElement(videoList, videoTemplate, 
            video.id_, video.title, video.description, video.archive_id
        )
    });
}

async function initPlaylistElements(playlistsList, group_id) {
    const playlist_data = await fetchData(`/groups/${group_id}/playlists`);
    /*{
        "type": "playlists list",
        "items": [
            {
                "id_": 0,
                "name": "PlaylistName",
            }
        ]
    }*/
    const playlistTemplate = document.getElementById("playlist_item_template").content.firstElementChild;
    playlistsList.innerHTML = '';
    playlist_data.items.forEach(playlist => {
        createPlaylistElement(playlistsList, playlistTemplate, 
            playlist.id_, playlist.name);
    });
}
async function initGroups() {
    const groups_data = await fetchData('/groups');
    /*{
        "type": "groups list",
        "items": [
            {
                "id_": 0,
                "name": "GroupName"
            },
        ]
    }*/
    const groupsList = document.getElementById("groups_list");
    const groupTemplate = document.getElementById("group_item_template").content.firstElementChild;
    groupsList.innerHTML = '';
    groups_data.items.forEach(group => {
        createGroupElement(groupsList, groupTemplate, group.id_, group.name);
    });
}
function getWeekSeededRandomItem(array, offset = 0) {
    if (!array || array.length === 0) return undefined;
    const now = new Date();
    const week = Math.floor(now.getTime() / (1000 * 60 * 60 * 24 * 7));
    const index = (week + offset) % array.length;
    return array[index];
}

async function selectVideoTree(video_path) {
    let group_id, playlist_id, video_id;

    if (!Array.isArray(video_path) || video_path.length !== 3) {
        console.warn("No valid video_path provided. Using fallback random values.");
        group_id = playlist_id = video_id = undefined;
    } else {
        [group_id, playlist_id, video_id] = video_path;
    }

    // 1. Resolve group
    let groupItem;
    if (group_id) {
        groupItem = document.getElementById(group_id.startsWith("group_") ? group_id : `group_${group_id}`);
    }
    if (!groupItem) {
        const groups = Array.from(document.querySelectorAll(".group-item"));
        groupItem = getWeekSeededRandomItem(groups, 0);
        group_id = groupItem?.id.split("_")[1];
    }
    if (!groupItem) return;

    const groupCheckbox = groupItem.querySelector(".group-dropdown");
    const playlistsWrap = groupItem.querySelector(".playlists");
    const playlistsList = groupItem.querySelector(".playlists-list");

    // Collapse others
    document.querySelectorAll(".group-dropdown").forEach(cb => {
        if (cb !== groupCheckbox && cb.checked) {
            cb.checked = false;
            cb.dispatchEvent(new Event("change", { bubbles: true }));
        }
    });

    // Expand this group and await playlists
    groupCheckbox.checked = true;
    await initPlaylistElements(playlistsList, group_id);
    playlistsWrap.style.height = playlistsList.scrollHeight + 1 + "px";

    // 2. Resolve playlist
    let playlistItem;
    if (playlist_id) {
        playlistItem = document.getElementById(playlist_id.startsWith("playlist_") ? playlist_id : `playlist_${playlist_id}`);
    }
    if (!playlistItem) {
        const playlists = Array.from(playlistsList.querySelectorAll(".playlist-item"));
        playlistItem = getWeekSeededRandomItem(playlists, 1);
        playlist_id = playlistItem?.id.split("_")[1];
    }
    if (!playlistItem) return;

    // Highlight and load videos
    const playlistName = playlistItem.querySelector(".playlist-item-name").textContent;
    const groupName = groupItem.querySelector(".group-item-name").textContent;
    const videoHead = document.getElementById("videos_title");
    videoHead.textContent = `${groupName} → ${playlistName}`;

    document.querySelectorAll(".selected").forEach(el => el.classList.remove("selected"));
    playlistItem.classList.add("selected");

    await initVideoElemetns(playlist_id);

    // 3. Resolve video
    let videoItem;
    if (video_id) {
        videoItem = document.getElementById(video_id.startsWith("video_") ? video_id : `video_${video_id}`);
    }
    if (!videoItem) {
        const videos = Array.from(document.querySelectorAll(".video-item"));
        videoItem = getWeekSeededRandomItem(videos, 2);
    }
    if (!videoItem) return;

    // Select video
    selectVideo(videoItem);
}

async function initializeGoogle() {    
    const googleButton = document.getElementById("google_button");
    const google_client_id = document.querySelector('meta[name="google-client-id"]').getAttribute('content');

    function renderButton() {
        google.accounts.id.renderButton(
            googleButton,
            {
                size: "medium",
                type: "icon",
                theme: "filled_blue",
                text: "signin"
            }
        );
    }

    async function handleLoginResponse(response) {
        answer = await postData("/login", JSON.stringify(response));
        // console.log("trusted: ", answer.trusted);
        googleButton.innerHTML = `<img class="google_logout" title="logout" src="${answer.picture}">`
        googleButton.addEventListener("click", () => {
            renderButton();
        });
    }

    google.accounts.id.initialize({
        client_id: google_client_id,
        callback: handleLoginResponse
    });
    renderButton();
}

async function initializePage() {
    const init_groups_job = initGroups();
    const config_data_job = fetchData("/config.json");

    const header_text = document.getElementById("header_text");
    const footer_text = document.getElementById("footer_text");
    const config_data = await config_data_job;
    header_text.textContent = config_data.header_text || "Yehi Adonenu";
    footer_text.textContent = config_data.footer_text || "We Want Mochiah Now";
    const first_video = config_data.first_video;
    await init_groups_job;
    await selectVideoTree(first_video);
}
// Initialize when page loads
window.addEventListener('DOMContentLoaded', initializePage);
window.addEventListener('load', initializeGoogle)

/*


1. Accessibility Improvements

Add aria-expanded attributes to dropdown checkboxes
Consider adding role="button" to clickable elements that aren't buttons
Add alt text templates for video thumbnails

2. Security Considerations

Ensure proper sanitization of data from the API, especially for innerHTML assignments
*/