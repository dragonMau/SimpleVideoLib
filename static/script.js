async function fetchData(url) {
    const response = await fetch(url);
    if (!response.ok) {
        const error = new Error(`Failed to fetch content from ${url}`);
        error.status = response.status;
        error.response = response;
        throw error;
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