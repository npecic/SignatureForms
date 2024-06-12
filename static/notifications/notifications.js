
let fileInput = document.getElementById('fileElem');

let message = document.getElementById('message');

let prevPage = document.getElementById('prevPage');
let nextPage = document.getElementById('nextPage');
let pageIndicator = document.getElementById('pageIndicator');



function updateMessage() {
    if (fileInput.files.length > 0) {
        message.innerHTML = `<div class="notification-item"><span class="notification-text"><strong>${fileInput.files.length} file(s) selected.</strong> Ready to upload.</span></div>`;
    } else {
        message.innerHTML = `<div class="notification-item"><span class="notification-text"><strong>No files selected.</strong></span></div>`;
    }
}



function displayFiles(page) {
    let startIndex = (page - 1) * filesPerPage;
    let endIndex = startIndex + filesPerPage;
    let filesToDisplay = processedFiles.slice(startIndex, endIndex);

    if (filesToDisplay.length > 0) {
        let messageHtml = '';
        filesToDisplay.forEach((file) => {
            messageHtml += `<tr><td>${file.filename}</td><td>${file.timestamp}</td><td>${file.signature}</td>`;
            if (file.downloadLink) {
                messageHtml += `<td><a href="/uploads/${file.downloadLink}" download class="download-btn">Download</a></td>`;
            }
            messageHtml += `</tr>`;
        });
        document.querySelector('tbody').innerHTML = messageHtml;
    } else {
        document.querySelector('tbody').innerHTML = `<tr><td colspan="4"><strong>No files to display.</strong></td></tr>`;
    }
}

        document.getElementById('clearOutputDirBtn').addEventListener('click', () => {
            let xhr = new XMLHttpRequest();
            xhr.open('POST', '/clear_output_directory');
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

function exportFileNames() {
            fetch('/export-file-names')
                .then(response => response.blob())
                .then(blob => {
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.style.display = 'none';
                    a.href = url;
                    a.download = 'processed_files.pdf';
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                })
                .catch(error => console.error('Error exporting file names:', error));
        }


function updatePagination() {
    let totalPages = Math.ceil(processedFiles.length / filesPerPage);
    let paginationHtml = '';
    for (let i = 1; i <= totalPages; i++) {
        paginationHtml += `<a href="#" onclick="navigateToPage(${i})" class="${i === currentPage ? 'active' : ''}">${i}</a>`;
    }
    document.querySelector('.pagination').innerHTML = paginationHtml;
}

function navigateToPage(page) {
    currentPage = page;
    displayFiles(currentPage);
    updatePagination();
}

// Initially display the first page if there are any processed files
if (processedFiles.length > 0) {
    displayFiles(currentPage);
    updatePagination();
}