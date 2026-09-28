document.addEventListener("DOMContentLoaded", () => {
    setupModal();
    setupDropZone();
    setupSingleProductForm();
    loadStats();
    loadInventory();

    const dateField = document.getElementById("prod-date");
    if (dateField && !dateField.value) {
        dateField.value = new Date().toISOString().split('T')[0];
    }
});

function setupModal() {
    const modal = document.getElementById("upload-modal");
    const openBtn = document.getElementById("open-upload-btn");
    const navTrigger = document.getElementById("nav-upload-trigger");
    const closeBtn = document.getElementById("close-modal-btn");
    const backdrop = document.getElementById("modal-close-backdrop");

    const open = () => modal.classList.add("active");
    const close = () => modal.classList.remove("active");

    if (openBtn) openBtn.onclick = open;
    if (navTrigger) navTrigger.onclick = (e) => { e.preventDefault(); open(); };
    if (closeBtn) closeBtn.onclick = close;
    if (backdrop) backdrop.onclick = close;
}

function setupDropZone() {
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("batch-file-input");
    const browseBtn = document.getElementById("browse-btn");
    const preview = document.getElementById("file-name-preview");
    const uploadBtn = document.getElementById("start-upload-btn");
    const statusBox = document.getElementById("upload-status");

    if (!dropZone || !fileInput) return;

    browseBtn.onclick = () => fileInput.click();

    fileInput.onchange = () => {
        if (fileInput.files.length > 0) {
            preview.innerText = fileInput.files[0].name;
            uploadBtn.removeAttribute("disabled");
        }
    };

    dropZone.ondragover = (e) => { e.preventDefault(); dropZone.style.borderColor = "var(--accent)"; };
    dropZone.ondragleave = () => { dropZone.style.borderColor = "var(--border)"; };
    dropZone.ondrop = (e) => {
        e.preventDefault();
        dropZone.style.borderColor = "var(--border)";
        if (e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;
            preview.innerText = e.dataTransfer.files[0].name;
            uploadBtn.removeAttribute("disabled");
        }
    };

    uploadBtn.onclick = async () => {
        if (!fileInput.files.length) return;
        const formData = new FormData();
        formData.append("file", fileInput.files[0]);

        uploadBtn.disabled = true;
        statusBox.style.color = "var(--accent)";
        statusBox.innerText = "Analyzing file with AI & indexing vectors...";

        try {
            const res = await fetch("/api/upload", {
                method: "POST",
                body: formData
            });
            const data = await res.json();
            if (res.ok) {
                statusBox.style.color = "var(--emerald)";
                statusBox.innerText = `Success: ${data.count} items imported into catalog!`;
                loadStats();
                loadInventory();
                setTimeout(() => {
                    document.getElementById("upload-modal").classList.remove("active");
                    statusBox.innerText = "";
                    preview.innerText = "";
                    fileInput.value = "";
                }, 1800);
            } else {
                statusBox.style.color = "var(--rose)";
                statusBox.innerText = data.error || "Upload failed";
                uploadBtn.disabled = false;
            }
        } catch (err) {
            statusBox.style.color = "var(--rose)";
            statusBox.innerText = "Network error during upload";
            uploadBtn.disabled = false;
        }
    };
}

function setupSingleProductForm() {
    const form = document.getElementById("single-product-form");
    if (!form) return;

    form.onsubmit = async (e) => {
        e.preventDefault();
        const payload = {
            product_name: document.getElementById("prod-name").value.trim(),
            model: document.getElementById("prod-model").value.trim(),
            supplier: document.getElementById("prod-supplier").value.trim(),
            price: parseFloat(document.getElementById("prod-price").value),
            currency: document.getElementById("prod-currency").value.trim() || "PKR",
            date: document.getElementById("prod-date").value,
            source_file: document.getElementById("prod-source").value.trim() || "manual_entry"
        };

        try {
            const res = await fetch("/api/products", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (res.ok) {
                form.reset();
                const dateField = document.getElementById("prod-date");
                if (dateField) dateField.value = new Date().toISOString().split('T')[0];
                document.getElementById("prod-currency").value = "PKR";
                document.getElementById("prod-source").value = "manual_entry";
                loadStats();
                loadInventory();
            } else {
                alert(data.error || "Failed to create product");
            }
        } catch (err) {
            console.error(err);
        }
    };
}

async function loadStats() {
    try {
        const res = await fetch("/api/stats");
        if (!res.ok) return;
        const data = await res.json();
        document.getElementById("stat-total-products").innerText = data.total_products || 0;
        document.getElementById("stat-total-val").innerText = `PKR ${Number(data.total_inventory_value || 0).toLocaleString()}`;
        document.getElementById("stat-avg-price").innerText = `PKR ${Number(data.average_price || 0).toLocaleString()}`;
        document.getElementById("stat-categories").innerText = data.suppliers_count || 0;
    } catch (err) {
        console.error(err);
    }
}

async function loadInventory() {
    const tbody = document.getElementById("inventory-table-body");
    const refreshBtn = document.getElementById("refresh-inventory-btn");
    if (refreshBtn) refreshBtn.onclick = loadInventory;
    if (!tbody) return;

    try {
        const res = await fetch("/api/products?limit=100");
        const data = await res.json();
        const products = data.products || [];

        if (products.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center">No inventory found. Upload a file or add products.</td></tr>`;
            return;
        }

        tbody.innerHTML = products.map(p => `
            <tr>
                <td><strong>${escapeHtml(p.product_name)}</strong></td>
                <td><span class="badge badge-ai">${escapeHtml(p.model || '-')}</span></td>
                <td>${escapeHtml(p.supplier || '-')}</td>
                <td><strong>${escapeHtml(p.currency || 'PKR')} ${Number(p.price).toLocaleString()}</strong></td>
                <td><small class="subtext">${p.date || '-'}</small></td>
                <td><small class="subtext">${escapeHtml(p.source_file || 'manual')}</small></td>
                <td>
                    <button class="btn btn-secondary btn-sm" onclick="deleteProduct('${p.id}')">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </td>
            </tr>
        `).join("");
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center">Error loading products</td></tr>`;
    }
}

async function deleteProduct(id) {
    if (!confirm("Are you sure you want to delete this product?")) return;
    try {
        const res = await fetch(`/api/products/${id}`, { method: "DELETE" });
        if (res.ok) {
            loadStats();
            loadInventory();
        } else {
            const data = await res.json();
            alert(data.error || "Deletion failed");
        }
    } catch (err) {
        console.error(err);
    }
}

function escapeHtml(text) {
    if (!text) return "";
    return text.toString()
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}