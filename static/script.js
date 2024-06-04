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
        message.innerHTML = `${fileInput.files.length} file(s) selected. Ready to upload.`;
    } else {
        message.innerHTML = 'No files selected.';
    }
}

function uploadFiles() {
    let files = fileInput.files;
    if (files.length === 0) {
        message.innerHTML = 'No files selected';
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
                    messageHtml += `${msg}<br>`;
                    if (downloadLinks[index]) {
                        messageHtml += `<a href="/uploads/${downloadLinks[index]}" download class="download-btn">Download</a><br>`;
                    }
                });
                message.innerHTML = messageHtml;
            } else {
                message.innerHTML = response.message;
            }
            progressBarFill.style.width = '0%';
        } else {
            message.innerHTML = 'Upload failed';
        }
        uploadBtn.disabled = false; // Re-enable the button after upload completes
        document.getElementById('progress-bar').style.display = 'none';
    };

    xhr.send(formData);
}
