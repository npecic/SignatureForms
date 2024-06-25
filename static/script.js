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

async function uploadFiles() {
    let files = fileInput.files;
    if (files.length === 0) {
        message.innerHTML = `<div class="notification-item"><span class="notification-text"><strong>No files selected.</strong></span></div>`;
        return;
    }

    uploadBtn.disabled = true;
    message.innerHTML = '<div class="notification-item"><span class="notification-text"><strong>Uploading PDF files</strong></span></div>';
    uploadMessage.style.display = 'block';
    progressBarFill.style.width = '0%';
    progressBarFill.innerText = '0%';

    let chunkSize = 5 * 1024 * 1024;  // 5MB chunk size
    let allFilesProcessed = [];
    let totalChunksUploaded = 0;
    let totalChunks = Array.from(files).reduce((acc, file) => acc + Math.ceil(file.size / chunkSize), 0);

    for (let file of files) {
        let fileChunks = Math.ceil(file.size / chunkSize);
        let chunkNumber = 0;

        for (let start = 0; start < file.size; start += chunkSize) {
            let chunk = file.slice(start, start + chunkSize);
            let formData = new FormData();
            formData.append('chunk', chunk);
            formData.append('fileName', file.name);
            formData.append('chunkNumber', chunkNumber);
            formData.append('totalChunks', fileChunks);

            let response = await uploadFileChunk(formData);
            if (response.status === 'success' && response.message === 'File upload complete') {
                allFilesProcessed.push(response.filePath);
            }
            chunkNumber++;
            totalChunksUploaded++;

            // Update upload progress bar
            let uploadProgress = Math.round((totalChunksUploaded / totalChunks) * 100);
            progressBarFill.style.width = `${uploadProgress}%`;
            progressBarFill.innerText = `${uploadProgress}%`;

            if (uploadProgress === 100) {
                uploadMessage.style.display = 'none';
            }
        }
    }

    if (allFilesProcessed.length > 0) {
        await processUploadedFiles(allFilesProcessed);
    }

    uploadBtn.disabled = false;
}

function uploadFileChunk(formData) {
    return new Promise((resolve, reject) => {
        let xhr = new XMLHttpRequest();
        xhr.open('POST', '/upload_file_chunk');
        xhr.onload = () => {
            if (xhr.status === 200) {
                resolve(JSON.parse(xhr.response));
            } else {
                reject(xhr.statusText);
            }
        };
        xhr.onerror = () => reject(xhr.statusText);
        xhr.send(formData);
    });
}

async function processUploadedFiles(filePaths) {
    message.innerHTML = '<div class="notification-item"><span class="notification-text"><strong>Processing uploaded files</strong></span></div>';
    processingMessage.style.display = 'block';
    processingProgressBar.style.display = 'block';
    processingProgressBarFill.style.width = '0%';
    processingProgressBarFill.innerText = '0%';

    let totalFiles = filePaths.length;
    let processedFilesCount = 0;

    let responses = await Promise.all(filePaths.map(async (filePath, index) => {
        let response = await processFile(filePath);
        processedFilesCount++;

        // Update processing progress bar
        let processingProgress = Math.round((processedFilesCount / totalFiles) * 100);
        processingProgressBarFill.style.width = `${processingProgress}%`;
        processingProgressBarFill.innerText = `${processingProgress}%`;

        // Add the processed file details to the array
        processedFiles.push({
            filename: response.message,
            downloadLink: response.downloadLink
        });

        if (processingProgress === 100) {
            processingMessage.style.display = 'none';
            processingProgressBar.style.display = 'none';
        }

        return response;
    }));

    displayFiles(currentPage);
    updatePagination();

    // Clear the upload folder once processing is complete
    await clearUploadFolder();
}

function processFile(filePath) {
    return new Promise((resolve, reject) => {
        let xhr = new XMLHttpRequest();
        xhr.open('POST', '/process_file');
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.onload = () => {
            if (xhr.status === 200) {
                resolve(JSON.parse(xhr.response));
            } else {
                reject(xhr.statusText);
            }
        };
        xhr.onerror = () => reject(xhr.statusText);
        xhr.send(JSON.stringify({ filePath }));
    });
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

async function clearUploadFolder() {
    return new Promise((resolve, reject) => {
        let xhr = new XMLHttpRequest();
        xhr.open('POST', '/clear_upload_dir');
        xhr.onload = () => {
            if (xhr.status === 200) {
                let response = JSON.parse(xhr.response);
                if (response.status === 'success') {
                    resolve(response);
                } else {
                    reject(response.message);
                }
            } else {
                reject(xhr.statusText);
            }
        };
        xhr.onerror = () => reject(xhr.statusText);
        xhr.send();
    });
}
