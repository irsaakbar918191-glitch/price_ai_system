document.addEventListener("DOMContentLoaded", () => {
    setupChat();
});

function setupChat() {
    const chatForm = document.getElementById("chat-form");
    const chatInput = document.getElementById("chat-input");
    const chatBox = document.getElementById("chat-box");
    const globalSearch = document.getElementById("global-search");

    if (globalSearch) {
        globalSearch.addEventListener("keypress", (e) => {
            if (e.key === "Enter" && globalSearch.value.trim()) {
                chatInput.value = globalSearch.value;
                chatForm.dispatchEvent(new Event("submit"));
                globalSearch.value = "";
                document.getElementById("chat-section").scrollIntoView({ behavior: "smooth" });
            }
        });
    }

    if (!chatForm || !chatInput || !chatBox) return;

    chatForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const query = chatInput.value.trim();
        if (!query) return;

        appendMessage("user", query);
        chatInput.value = "";

        const loadingId = appendLoading();

        try {
            const res = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query })
            });

            removeLoading(loadingId);

            if (res.ok) {
                const data = await res.json();
                appendMessage("ai", data.answer);
            } else {
                appendMessage("ai", "Error: Unable to get a response from the server.");
            }
        } catch (err) {
            removeLoading(loadingId);
            appendMessage("ai", "Network connection error.");
        }
    });

    function appendMessage(sender, text) {
        const div = document.createElement("div");
        div.className = `chat-bubble ${sender}`;

        const icon = sender === "ai" ? "fa-robot" : "fa-user";
        div.innerHTML = `
            <i class="fa-solid ${icon} bubble-avatar"></i>
            <div class="bubble-text">${formatMessage(text)}</div>
        `;
        chatBox.appendChild(div);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    function appendLoading() {
        const id = "loading-" + Date.now();
        const div = document.createElement("div");
        div.id = id;
        div.className = "chat-bubble ai";
        div.innerHTML = `
            <i class="fa-solid fa-robot bubble-avatar"></i>
            <div class="bubble-text"><i class="fa-solid fa-spinner fa-spin"></i> Analyzing catalog & prices...</div>
        `;
        chatBox.appendChild(div);
        chatBox.scrollTop = chatBox.scrollHeight;
        return id;
    }

    function removeLoading(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    function formatMessage(text) {
        if (!text) return "";
        let formatted = text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");

        formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');
        return formatted;
    }
}