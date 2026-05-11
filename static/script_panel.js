let allVideoElements = []; // Store elements here for fast filtering

function populateVideoTemplate(video, template) {
    const clone = template.content.cloneNode(true);
    const root = clone.querySelector('.video-item');

    // 1. Hidden Data (stored in the DOM but not visible to user)
    root.dataset.id = video.id_; 
    root.dataset.differ = video.is_differ;

    // 2. Visible Data
    root.querySelector('.v-archive-id').textContent = video.archive_id;
    root.querySelector('.v-title').textContent = video.title;

    // 3. Description + Hover
    const descEl = root.querySelector('.v-description');
    descEl.textContent = video.description || '';
    descEl.title = video.description || 'No description'; // This creates the hover tooltip

    // 4. Status Flags
    root.querySelector('.badge-remote').textContent = video.is_remote ? '☁️ Remote' : '💾 Local';
    
    if (video.is_hidden) {
        root.querySelector('.badge-hidden').style.display = 'inline-block';
    }

    // 5. Logic for 'is_differ' (e.g., subtle background tint if they differ)
    if (video.is_differ) {
        root.style.backgroundColor = '#fff9e6'; // Light warning yellow
    }

    return clone;
}
    
async function loadVideos() {
    const videos = await fetchData('/admin/all_videos');
    
    const container = document.getElementById('videos_list');
    const template = document.getElementById('item_video');

    // Use a DocumentFragment to improve performance (avoids 2,000 separate page updates)
    const fragment = document.createDocumentFragment();
    videos.forEach(video => {
        // 1. Use the new function to get the "stamped" HTML
        const clone = populateVideoTemplate(video, template);
        
        // 2. Get the actual <div> from inside the clone to save for filtering
        const root = clone.querySelector('.video-item');

        // 3. Save reference for filtering (using the rich data we just set)
        allVideoElements.push({
            el: root,
            // Searching by title, archive_id, and even description
            searchText: `${video.title} ${video.archive_id} ${video.description}`.toLowerCase()
        });

        // 4. Add the finished clone to the "box" (fragment)
        fragment.appendChild(clone);
    });

    container.innerHTML="";
    container.appendChild(fragment);
}

function filterVideos() {
    const query = document.getElementById('videoSearch').value.toLowerCase();
    
    allVideoElements.forEach(item => {
        const isMatch = item.searchText.includes(query);
        item.el.style.display = isMatch ? 'flex' : 'none';
    });
}

// ---------- Try accessing /panel ----------
async function checkPanelAccess() {
    try {
        await fetchData("/get_picture");
    } catch (err) {
        if (err.status === 401) {
        window.location.replace("/login");
        } else {
            document.getElementById("status").innerText = "Server error.";
        }
    }
}


// Start the process
loadVideos();