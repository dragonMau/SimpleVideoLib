// ---------- Try accessing /panel ----------
async function checkPanelAccess() {
    try {
        await fetchData("/get_picture");
        window.location.replace("/panel");
    } catch (err) {
        if (err.status === 401) {
            renderGoogleButton();
        } else {
            document.getElementById("status").innerText = "Server error.";
        }
    }
}

// ---------- Handle Google login ----------
async function handleLoginResponse(response) {
    try { await postData("/login", response); } catch { }
    window.location.replace("/panel");
}

// ---------- Render Google button ----------
function renderGoogleButton() {
    document.getElementById("status").innerText = "Login required.";

    google.accounts.id.renderButton(
        document.getElementById("google_button"),
        { theme: "outline", size: "large" }
    );

    google.accounts.id.prompt();
}

// ---------- Initialize Google ----------
async function initializeGoogle() {
    const clientId = document
        .querySelector('meta[name="google-client-id"]')
        .getAttribute('content');

    google.accounts.id.initialize({
        client_id: clientId,
        callback: handleLoginResponse
    });
}

// ---------- On load ----------
window.addEventListener("DOMContentLoaded", async () => {
    await initializeGoogle();
    await checkPanelAccess();
});