let dropArea = document.getElementById('drop-area');
let fileInput = document.getElementById('fileElem');
let progressBarFill = document.getElementById('progress-bar-fill');
let message = document.getElementById('message');
let uploadBtn = document.getElementById('uploadBtn');

dropArea.addEventListener('dragover', (event) => {
    event.preventDefault();
    dropArea.classList.add('hover');
});

dropArea.addEventListener('dragleave', () => {
    dropArea.classList.remove('hover');
});

dropArea.addEventListener('drop', (event) => {
    event.preventDefault();
    dropArea.classList.remove('hover');
    fileInput.files = event.dataTransfer.files;
    updateMessage();
});

dropArea.addEventListener('click', () => {
    fileInput.click();
});

fileInput.addEventListener('change', () => {
    updateMessage();
});

function updateMessage() {
    if (fileInput.files.length > 0) {
        message.innerHTML = `<div class="notification-item"><strong>${fileInput.files.length} file(s) selected.</strong> Ready to upload.</div>`;
    } else {
        message.innerHTML = `<div class="notification-item"><strong>No files selected.</strong></div>`;
    }
}

function uploadFiles() {
    let files = fileInput.files;
    if (files.length === 0) {
        message.innerHTML = `<div class="notification-item"><strong>No files selected.</strong></div>`;
        return;
    }

    uploadBtn.disabled = true; // Disable the button during upload

    let formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
    }

    let xhr = new XMLHttpRequest();
    xhr.open('POST', '/upload');
    xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable) {
            let percentComplete = (event.loaded / event.total) * 100;
            document.getElementById('progress-bar').style.display = 'block';
            progressBarFill.style.width = percentComplete + '%';
            progressBarFill.innerText = Math.round(percentComplete) + '%';
        }
    });

    xhr.onload = () => {
        if (xhr.status === 200) {
            let response = JSON.parse(xhr.responseText);
            if (response.status === 'success') {
                let messages = response.messages;
                let downloadLinks = response.download_links;
                let messageHtml = '';
                messages.forEach((msg, index) => {
                    messageHtml += `<div class="notification-item"><span class="notification-text"><strong>${msg}</strong></span>`;
                    if (downloadLinks[index]) {
                        messageHtml += `<a href="/uploads/${downloadLinks[index]}" download class="download-btn">Download</a>`;
                    }
                    messageHtml += `</div>`;
                });
                message.innerHTML = messageHtml;
            } else {
                message.innerHTML = `<div class="notification-item"><strong>${response.message}</strong></div>`;
            }
            progressBarFill.style.width = '0%';
        } else {
            message.innerHTML = `<div class="notification-item"><strong>Upload failed</strong></div>`;
        }
        uploadBtn.disabled = false; // Re-enable the button after upload completes
        document.getElementById('progress-bar').style.display = 'none';
    };

    xhr.send(formData);
}
