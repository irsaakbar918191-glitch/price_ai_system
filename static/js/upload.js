const uploadForm = document.getElementById('uploadForm');
const fileInput = document.getElementById('fileInput');
const dragArea = document.getElementById('dragArea');
const uploadStatus = document.getElementById('uploadStatus');
const selectedFileName = document.getElementById('selectedFileName');
const dropText = document.getElementById('dropText');
const dropHint = document.getElementById('dropHint');

function showSelectedFile(file) {
  if (!file) {
    if (selectedFileName) selectedFileName.textContent = '';
    if (dropText) dropText.textContent = 'Drag & drop file here';
    if (dropHint) dropHint.textContent = 'PDF, image, Excel, or CSV';
    if (dragArea) dragArea.classList.remove('attached');
    return;
  }

  if (selectedFileName) selectedFileName.textContent = `Selected: ${file.name}`;
  if (dropText) dropText.textContent = 'File attached successfully';
  if (dropHint) dropHint.textContent = `${file.name} • ${Math.round(file.size / 1024)} KB`;
  if (dragArea) dragArea.classList.add('attached');
}

if (uploadForm && fileInput && dragArea) {
  fileInput.addEventListener('change', () => {
    const file = fileInput.files[0];
    showSelectedFile(file);
  });

  ['dragenter', 'dragover'].forEach(eventName => {
    dragArea.addEventListener(eventName, (event) => {
      event.preventDefault();
      dragArea.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dragArea.addEventListener(eventName, (event) => {
      event.preventDefault();
      dragArea.classList.remove('dragover');
    });
  });

  dragArea.addEventListener('drop', (event) => {
    const files = event.dataTransfer.files;
    if (files && files.length > 0) {
      fileInput.files = files;
      showSelectedFile(files[0]);
    }
  });

  dragArea.addEventListener('click', () => fileInput.click());

  uploadForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const file = fileInput.files[0];
    if (!file) {
      if (uploadStatus) uploadStatus.textContent = 'Please select a file first.';
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    if (uploadStatus) uploadStatus.textContent = 'Uploading and processing...';
    try {
      const response = await fetch('/api/upload', {
        method: 'POST',
        headers: { Authorization: `Bearer ${localStorage.getItem('price_ai_token') || ''}` },
        body: formData
      });

      if (response.status === 401) {
        handleAuthFailure();
        return;
      }

      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Upload failed');
      if (uploadStatus) uploadStatus.textContent = `Saved: ${data.product.product_name}`;
      showSelectedFile(file);
    } catch (error) {
      if (uploadStatus) uploadStatus.textContent = error.message || 'Upload failed.';
    }
  });
}
