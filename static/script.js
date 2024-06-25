let dropArea = document.getElementById('drop-area');
let fileInput = document.getElementById('fileElem');
let progressBarFill = document.getElementById('progress-bar-fill');
let processingProgressBarFill = document.getElementById('processing-progress-bar-fill');
let processingProgressBar = document.getElementById('processing-progress-bar');
let processingMessage = document.getElementById('processing-message');
let uploadMessage = document.getElementById('upload-message');
let message = document.getElementById('message');
let uploadBtn = document.getElementById('uploadBtn');
let prevPage = document.getElementById('prevPage');
let nextPage = document.getElementById('nextPage');
let pageIndicator = document.getElementById('pageIndicator');
let clearUploadDirBtn = document.getElementById('clearUploadDirBtn');

let currentPage = 1;
let filesPerPage = 10;
let processedFiles = [];

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
        message.innerHTML = `<div class="notification-item"><span class="notification-text"><strong>${fileInput.files.length} file(s) selected.</strong> Ready to upload.</span></div>`;
    } else {
        message.innerHTML = `<div class="notification-item"><span class="notification-text"><strong>No files selected.</strong></span></div>`;
    }
}

function showAnalyzingMessage() {
    message.innerHTML = '<div class="notification-item"><span class="notification-text"><strong>Analyzing Files ...</strong></span></div>';
}

function showProcessingMessage() {
    message.innerHTML = '<div class="notification-item"><span class="notification-text"><strong>Processing PDF files</strong></span></div>';
}

function uploadFiles() {
    let files = fileInput.files;
    if (files.length === 0) {
        message.innerHTML = `<div class="notification-item"><span class="notification-text"><strong>No files selected.</strong></span></div>`;
        return;
    }

    uploadBtn.disabled = true;
    message.innerHTML = '<div class="notification-item"><span class="notification-text"><strong>Uploading PDF files</strong></span></div>';

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
            uploadMessage.style.display = 'block';
            progressBarFill.style.width = percentComplete + '%';
            progressBarFill.innerText = Math.round(percentComplete) + '%';

            if (percentComplete === 100) {
                showAnalyzingMessage();
            }
        }
    });

    xhr.onload = () => {
        if (xhr.status === 200) {
            let response = JSON.parse(xhr.responseText);
            if (response.status === 'success') {
                let messages = response.messages;
                let downloadLinks = response.download_links;
                let totalFiles = messages.length;
                let processedCount = 0;

                progressBarFill.style.width = '0%';
                document.getElementById('progress-bar').style.display = 'none';

                showProcessingMessage();
                processingProgressBar.style.display = 'block';

                processedFiles = messages.map((msg, index) => ({
                    filename: msg,
                    downloadLink: downloadLinks[index]
                }));

                let processInterval = setInterval(() => {
                    processedCount++;
                    let processingPercentComplete = (processedCount / totalFiles) * 100;
                    processingProgressBarFill.style.width = processingPercentComplete + '%';
                    processingProgressBarFill.innerText = Math.round(processingPercentComplete) + '%';

                    if (processedCount >= totalFiles) {
                        clearInterval(processInterval);
                        processingProgressBar.style.display = 'none';
                        processingMessage.style.display = 'none';
                        displayFiles(currentPage);
                        updatePagination();
                    }
                }, 100);

            } else {
                message.innerHTML = `<div class="notification-item"><span class="notification-text"><strong>${response.message}</strong></span></div>`;
            }
        } else {
            message.innerHTML = `<div class="notification-item"><span class="notification-text"><strong>Upload failed</strong></span></div>`;
        }
        uploadBtn.disabled = false;
    };

    xhr.send(formData);
}

function displayFiles(page) {
    let startIndex = (page - 1) * filesPerPage;
    let endIndex = startIndex + filesPerPage;
    let filesToDisplay = processedFiles.slice(startIndex, endIndex);

    if (filesToDisplay.length > 0) {
        let messageHtml = '';
        filesToDisplay.forEach((file) => {
            messageHtml += `<div class="notification-item"><span class="notification-text"><strong>${file.filename}</strong></span>`;
            if (file.downloadLink) {
                messageHtml += `<a href="/uploads/${file.downloadLink}" download class="download-btn">Download</a>`;
            }
            messageHtml += `</div>`;
        });
        message.innerHTML = messageHtml;
    } else {
        message.innerHTML = `<div class="notification-item"><span class="notification-text"><strong>No files to display.</strong></span></div>`;
    }
}

function updatePagination() {
    let totalPages = Math.ceil(processedFiles.length / filesPerPage);
    pageIndicator.innerText = `Page ${currentPage} of ${totalPages}`;
    prevPage.style.display = currentPage > 1 ? 'inline-block' : 'none';
    nextPage.style.display = currentPage < totalPages ? 'inline-block' : 'none';
}

prevPage.addEventListener('click', () => {
    if (currentPage > 1) {
        currentPage--;
        displayFiles(currentPage);
        updatePagination();
    }
});

nextPage.addEventListener('click', () => {
    let totalPages = Math.ceil(processedFiles.length / filesPerPage);
    if (currentPage < totalPages) {
        currentPage++;
        displayFiles(currentPage);
        updatePagination();
    }
});

if (processedFiles.length > 0) {
    displayFiles(currentPage);
    updatePagination();
}

clearUploadDirBtn.addEventListener('click', () => {
    let xhr = new XMLHttpRequest();
    xhr.open('POST', '/clear_upload_dir');
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.onload = () => {
        if (xhr.status === 200) {
            let response = JSON.parse(xhr.responseText);
            if (response.status === 'success') {
                message.innerHTML = `<div class="notification-item"><span class="notification-text"><strong>Upload directory cleared successfully.</strong></span></div>`;
            } else {
                message.innerHTML = `<div class="notification-item"><span class="notification-text"><strong>Failed to clear upload directory.</strong></span></div>`;
            }
        } else {
            message.innerHTML = `<div class="notification-item"><span class="notification-text"><strong>Request failed</strong></span></div>`;
        }
    };
    xhr.send();
});
