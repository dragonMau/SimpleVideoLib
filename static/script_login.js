async function getGoogleClient() {
    // 1. Check if the object already exists (if it finished loading early)
    if (window.google && window.google.accounts) {
        return window.google;
    }

    // 2. Otherwise, wait for the script to trigger its 'load' event
    return new Promise((resolve, reject) => {
        const script = document.querySelector('script[src*="gsi/client"]');
        
        script.addEventListener('load', () => resolve(window.google));
        script.addEventListener('error', () => reject(new Error("Google script failed to load")));
        
        // Safety timeout: don't hang your app forever if Google is down
        setTimeout(() => reject(new Error("Google script load timeout")), 5000);
    });
}
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
async function renderGoogleButton() {
    const statusElement = document.getElementById("status");
    
    // Update status message
    statusElement.innerHTML = '<span>Login required.</span>';
    const google = await getGoogleClient();
    
    // Render the Google Sign-In button
    google.accounts.id.renderButton(
        document.getElementById("google_button"),
        { 
            theme: "outline", 
            size: "large",
            width: 280,
            text: "signin_with",
            shape: "rectangular"
        }
    );
    
    // Prompt for One Tap sign-in
    // google.accounts.id.prompt();
}

// ---------- Initialize Google ----------
async function initializeGoogle() {
    const google = await getGoogleClient();
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