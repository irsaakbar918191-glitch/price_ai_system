document.addEventListener("DOMContentLoaded", () => {
    checkCurrentUser();
    setupAuthPage();
});

async function checkCurrentUser() {
    try {
        const res = await fetch("/api/auth/me");
        const data = await res.json();
        const display = document.getElementById("user-display-email");
        const btn = document.getElementById("auth-action-btn");

        if (data.authenticated && data.user) {
            if (display) display.innerText = data.user.email;
            if (btn) {
                btn.innerText = "Logout";
                btn.onclick = logoutUser;
            }
        } else {
            if (display) display.innerText = "Guest User";
            if (btn) {
                btn.innerText = "Login";
                btn.onclick = () => { window.location.href = "/login"; };
            }
        }
    } catch (err) {
        console.error(err);
    }
}

async function logoutUser() {
    try {
        await fetch("/api/auth/logout", { method: "POST" });
        window.location.reload();
    } catch (err) {
        console.error(err);
    }
}

function setupAuthPage() {
    const authForm = document.getElementById("auth-form");
    if (!authForm) return;

    let isLoginMode = true;
    const toggleBtn = document.getElementById("toggle-auth-mode");
    const title = document.getElementById("auth-title");
    const desc = document.getElementById("auth-desc");
    const submitBtn = document.getElementById("auth-submit-btn");
    const toggleText = document.getElementById("auth-toggle-text");
    const alertBox = document.getElementById("auth-alert");

    toggleBtn.addEventListener("click", () => {
        isLoginMode = !isLoginMode;
        if (isLoginMode) {
            title.innerText = "Welcome Back";
            desc.innerText = "Login to manage prices and inventory intelligence";
            submitBtn.innerText = "Login";
            toggleText.innerText = "Don't have an account?";
            toggleBtn.innerText = "Sign Up";
        } else {
            title.innerText = "Create Account";
            desc.innerText = "Sign up to track and optimize your product pricing";
            submitBtn.innerText = "Register";
            toggleText.innerText = "Already have an account?";
            toggleBtn.innerText = "Login";
        }
        alertBox.innerText = "";
    });

    authForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const email = document.getElementById("auth-email").value.trim();
        const password = document.getElementById("auth-password").value.trim();

        const endpoint = isLoginMode ? "/api/auth/login" : "/api/auth/register";

        alertBox.innerText = "Processing...";
        alertBox.style.color = "var(--accent)";

        try {
            const res = await fetch(endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password })
            });

            const data = await res.json();
            if (res.ok) {
                alertBox.style.color = "var(--emerald)";
                alertBox.innerText = isLoginMode ? "Login successful! Redirecting..." : "Registration successful! Redirecting...";
                setTimeout(() => { window.location.href = "/"; }, 1000);
            } else {
                alertBox.style.color = "var(--rose)";
                alertBox.innerText = data.error || "Authentication error occurred";
            }
        } catch (err) {
            alertBox.style.color = "var(--rose)";
            alertBox.innerText = "Server connection error";
        }
    });
}