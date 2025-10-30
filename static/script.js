async function fetchData(url) {
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`Failed to fetch content from ${url}`);
    }
    const data = await response.json();
    return data;
}
async function postData(url, data = {}) {
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
            playlistsWrap.style.height = playlistsList.scrollHeight + 1 + "px";

            await initPlaylistElements(playlistsList, group_id);

            loadingIndicator.remove();
            playlistsWrap.style.height = playlistsList.scrollHeight + 1 + "px";

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

// createPlaylistElement(playlistsList, playlistTemplate, groupid, playlist.id_, playlist.name)
function createPlaylistElement(playlistsList, playlistTemplate, group_id, playlist_id, playlist_name) {
    const playlistItem = playlistTemplate.cloneNode(true);
    playlistItem.id = `playlist_${playlist_id}`;
    const playlistName = playlistItem.querySelector(".playlist-item-name");
    playlistName.innerHTML = `${playlist_name}`;

    playlistItem.addEventListener("click", async () => {

        const videoHead = document.querySelector("#videos_title");
        const group_name = playlistItem.closest(".group-item").querySelector(".group-item-name").textContent;

        playlistName.innerHTML = `${playlist_name} <span class="spinner"></spinner>`;
        await initVideoElemetns(group_id, playlist_id);
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

//createVideoElement(videoList, videoTemplate, groupid, playlistid, video.id_, video.title, video.description, video.archive_id )
function createVideoElement(videoList, videoTemplate, group_id, playlist_id, video_id, video_title, video_description, archive_id) {
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
        sessionStorage.setItem("opened_video", JSON.stringify([
            Date.now() + 3600000, group_id, playlist_id, video_id
        ]))
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

async function initVideoElemetns(group_id, playlist_id) {
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
        createVideoElement(videoList, videoTemplate, group_id, playlist_id,
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
        createPlaylistElement(playlistsList, playlistTemplate, group_id,
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

async function selectVideoTree() {
    let group_id, playlist_id, video_id;
    const opened_video = JSON.parse(sessionStorage.getItem("opened_video") || "[0, 0, 0, 0]");
    let video_path;
    if (opened_video[0] < Date.now()) { // expired
        video_path = [0, 0, 0];
    }
    else {
        video_path = opened_video.slice(1);
    }

    if (!Array.isArray(video_path) || video_path.length !== 3) {
        console.warn("No valid video_path provided. Using fallback random values.");
        group_id = playlist_id = video_id = undefined;
    } else {
        [group_id, playlist_id, video_id] = video_path;
    }

    // 1. Resolve group
    let groupItem;
    if (group_id) {
        groupItem = document.getElementById(`group_${group_id}`);
    }
    if (!groupItem) {
        const groups = Array.from(document.querySelectorAll(".group-item"));
        groupItem = getWeekSeededRandomItem(groups, 0);
        group_id = +groupItem?.id.split("_")[1];
    }
    if (!groupItem) {
        console.error("Group Item not found!!");
        return;
    }

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
        playlistItem = document.getElementById(`playlist_${playlist_id}`);
    }
    if (!playlistItem) {
        const playlists = Array.from(playlistsList.querySelectorAll(".playlist-item"));
        playlistItem = getWeekSeededRandomItem(playlists, 1);
        playlist_id = playlistItem?.id.split("_")[1];
    }
    if (!playlistItem) {
        console.error("Playlist Item not Found!!!");
        return;
    }

    // Highlight and load videos
    const playlistName = playlistItem.querySelector(".playlist-item-name").textContent;
    const groupName = groupItem.querySelector(".group-item-name").textContent;
    const videoHead = document.getElementById("videos_title");
    videoHead.textContent = `${groupName} → ${playlistName}`;

    document.querySelectorAll(".selected").forEach(el => el.classList.remove("selected"));
    playlistItem.classList.add("selected");

    await initVideoElemetns(group_id, playlist_id);

    // 3. Resolve video
    let videoItem;
    if (video_id) {
        videoItem = document.getElementById(`video_${video_id}`);
    }
    if (!videoItem) {
        const videos = Array.from(document.querySelectorAll(".video-item"));
        videoItem = getWeekSeededRandomItem(videos, 2);
    }
    if (!videoItem) {
        console.error("Video Item not Found!!!");
        return;
    }

    // Select video
    sessionStorage.setItem("opened_video", JSON.stringify([Date.now() + 3600000, group_id, playlist_id, video_id]));
    selectVideo(videoItem);
}

// --- Render Google login button ---
function renderGoogleButton() {
    const googleButton = document.getElementById("google_button");
    googleButton.innerHTML = "";
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

// --- Render user picture with logout ---
function renderUserPicture(pictureUrl) {
    const googleButton = document.getElementById("google_button");
    googleButton.innerHTML = `<img class="google_logout" title="logout" src="${pictureUrl}" onclick="showMenu()">`;
    // googleButton.onclick = showMenu; 
}
function showMenu() {
    const menu = document.querySelector("#menu_box");
    menu.show();
}
function hideMenu() {
    menu.close();
}
// --- Logout function ---
async function logout() {
    try { await postData("/logout"); } catch { }
    // hideMenu();
    renderGoogleButton();
}

// --- Handle Google login response ---
async function handleLoginResponse(response) {
    try { await postData("/login", response); } catch { }
    await renderMode();
}

async function renderMode() {
    try {
        const pictureData = await fetchData("/get_picture");
        renderUserPicture(pictureData.picture);
    } catch (err) {
        renderGoogleButton();
    }
}
async function initializeGoogle() {
    const google_client_id = document.querySelector('meta[name="google-client-id"]').getAttribute('content');


    // --- Initialize Google API ---
    google.accounts.id.initialize({
        client_id: google_client_id,
        callback: handleLoginResponse
    });
}


async function initializePage() {
    const config_data_job = fetchData("/config.json");

    const header_text = document.getElementById("header_text");
    const footer_text = document.getElementById("footer_text");
    const config_data = await config_data_job;
    header_text.textContent = config_data.header_text || "Yehi Adonenu";
    footer_text.textContent = config_data.footer_text || "We Want Mochiah Now";
    const opened_video = JSON.parse(sessionStorage.getItem("opened_video") || "[0, 0, 0, 0]"); // [when, group, playlist, video]
    if (opened_video[0] < Date.now()) { // expired
        sessionStorage.setItem("opened_video", JSON.stringify(
            [Date.now() + 3600000, ...config_data.first_video]
        ));
    }
}
// Initialize when page loads
window.addEventListener('DOMContentLoaded', async () => {
    initializeGoogle().then(renderMode);
    await initializePage();
    await initGroups();
    await selectVideoTree();
});
window.addEventListener('load', async () => {
});
window.addEventListener('scroll', () => {
    document.documentElement.style.setProperty('--scroll-y', `${window.scrollY}px`);
});


document.querySelector("#menu_logout").onclick = logout;

const dialogUpload = document.querySelector("#dialog_upload");
const dialogUploadPlaylists = document.querySelector("#dialog_upload_playlists");
new Choices('#dialog_upload_playlists', {
    duplicateItemsAllowed: false,
    searchEnabled: true,
    shouldSort: false,
    placeholderValue: 'choose atleast one playlist'
});
dialogUpload.addEventListener("close", () => {
    const scrollY =  document.body.style.top;
    document.body.style.position = '';
    document.body.style.top = '';
    window.scrollTo(0, parseInt(scrollY || '0') * -1);
});
const dialogUploadNewPlaylistLabel = dialogUpload.querySelector(".new_name_label");
const dialogUploadNewPlaylistInput = dialogUpload.querySelector(".new_name_input");

dialogUploadPlaylists.addEventListener("change", ()=>{
    var special_selected = Array.from(dialogUploadPlaylists.selectedOptions).some(opt => opt.value === '-1');
    if (special_selected){
        dialogUploadNewPlaylistLabel.classList.remove("hidden");
        dialogUploadNewPlaylistInput.classList.remove("hidden");
    } else {
        dialogUploadNewPlaylistInput.classList.add("hidden");
        dialogUploadNewPlaylistLabel.classList.add("hidden");
    }
    dialogUploadNewPlaylistInput.required=special_selected;
});
document.querySelector("#menu_upload").onclick = () => {
    const scrollY = document.documentElement.style.getPropertyValue('--scroll-y');
    dialogUpload.showModal();
    document.body.style.position = 'fixed';
    document.body.style.top = `-${scrollY}`;
};

const dialogSite = document.querySelector("#dialog_site");
document.querySelector("#menu_site").onclick = () => dialogSite.showModal();
const dialogVideo = document.querySelector("#dialog_video");
document.querySelector("#menu_video").onclick = () => dialogVideo.showModal();
const dialogPlaylist = document.querySelector("#dialog_playlist");
document.querySelector("#menu_playlist").onclick = () => dialogPlaylist.showModal();
const dialogGroup = document.querySelector("#dialog_group");
document.querySelector("#menu_group").onclick = () => dialogGroup.showModal();
/*


1. Accessibility Improvements

Add aria-expanded attributes to dropdown checkboxes
Consider adding role="button" to clickable elements that aren't buttons
Add alt text templates for video thumbnails

2. Security Considerations

Ensure proper sanitization of data from the API, especially for innerHTML assignments
*/