document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('folder1Input').addEventListener('change', function() {
        updatePath('folder1', this);
    });

    document.getElementById('folder2Input').addEventListener('change', function() {
        updatePath('folder2', this);
    });

    document.getElementById('uploadCompareButton').addEventListener('click', function(e) {
        e.preventDefault();
        const folder1 = document.getElementById('folder1Input').files;
        const folder2 = document.getElementById('folder2Input').files;
        document.getElementById('progressBarContainer').classList.add('visible'); // Show the progress bar
        document.getElementById('progressBar').style.width = '0%'; // Reset progress bar width
        document.getElementById('progressBar').textContent = '0%'; // Reset progress bar text
        uploadAndCompareFolders(folder1, folder2);
    });

    document.getElementById('clearDropdown').addEventListener('change', function() {
        handleClear(this);
    });

    document.getElementById('downloadDropdown').addEventListener('change', function() {
        handleDownload(this);
    });
});

let currentPage = 1;
const filesPerPage = 10;
let matches = [];
let mismatches = [];
let displayType = 'matches'; // Control what to display: 'matches' or 'mismatches'

function updatePath(inputId, inputElement) {
    if (inputElement.files.length > 0) {
        document.getElementById(inputId).value = inputElement.files[0].webkitRelativePath.split('/')[0];
    }
}

function uploadAndCompareFolders(folder1Files, folder2Files) {
    const formData = new FormData();
    for (let file of folder1Files) {
        formData.append('folder1', file);
    }
    for (let file of folder2Files) {
        formData.append('folder2', file);
    }

    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/upload_folders', true);

    xhr.upload.onprogress = function(event) {
        if (event.lengthComputable) {
            const percentComplete = (event.loaded / event.total) * 50; // Upload progress max 50%
            document.getElementById('progressBar').style.width = percentComplete + '%';
            document.getElementById('progressBar').textContent = Math.floor(percentComplete) + '%';
        }
    };

    xhr.onload = function() {
        if (xhr.status === 200) {
            document.getElementById('progressBar').textContent = 'Upload completed. Comparing...';
            document.getElementById('progressBar').style.width = '50%'; // Set to 50% for comparison progress
            fetchComparisonResults();
        } else {
            document.getElementById('progressBar').textContent = 'Upload failed.';
        }
    };

    xhr.onerror = function() {
        document.getElementById('progressBar').textContent = 'Upload failed.';
    };

    xhr.send(formData);
}

function fetchComparisonResults() {
    fetch('/compare_pdfs', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'error') {
            throw new Error(data.message);
        }

        matches = data.matches;
        mismatches = data.mismatches;
        let percentComplete = 50;
        const interval = setInterval(() => {
            if (percentComplete < 100) {
                percentComplete += 5;
                document.getElementById('progressBar').style.width = percentComplete + '%';
                document.getElementById('progressBar').textContent = Math.floor(percentComplete) + '%';
            } else {
                clearInterval(interval);
                document.getElementById('progressBar').textContent = 'Comparison completed.';
            }
        }, 100);

        if (displayType === 'matches') {
            displayFiles(matches, 'match');
        } else {
            displayFiles(mismatches, 'mismatch');
        }
        updatePagination(displayType === 'matches' ? matches : mismatches);
    })
    .catch(error => {
        console.error('Error fetching comparison results:', error);
        document.getElementById('progressBar').textContent = 'Comparison failed.';
    });
}

function displayFiles(files, type) {
    const startIndex = (currentPage - 1) * filesPerPage;
    const endIndex = startIndex + filesPerPage;
    const filesToDisplay = files.slice(startIndex, endIndex);

    const resultList = document.getElementById('matchList');
    resultList.innerHTML = '';
    filesToDisplay.forEach(file => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="file-name">${file.message}</td>
            <td class="download-link"><a href="/download_compare_file/${type}/${file.download_link}" class="download-btn" download="${file.download_link}">Download</a></td>
        `;
        resultList.appendChild(row);
    });
}


function displayNoResultsMessage() {
    const resultList = document.getElementById('matchList');
    resultList.innerHTML = '<tr><td colspan="2">No files found.</td></tr>';

    const pagination = document.getElementById('pagination');
    pagination.innerHTML = ''; // Clear pagination if no results
}

function updatePagination(files) {
    const totalPages = Math.ceil(files.length / filesPerPage);
    const pagination = document.getElementById('pagination');
    pagination.innerHTML = '';

    const maxPageLinks = 5; // Maximum number of page links to display at a time
    let startPage = Math.max(currentPage - Math.floor(maxPageLinks / 2), 1);
    let endPage = startPage + maxPageLinks - 1;

    if (endPage > totalPages) {
        endPage = totalPages;
        startPage = Math.max(endPage - maxPageLinks + 1, 1);
    }

    if (startPage > 1) {
        const firstPageLink = document.createElement('a');
        firstPageLink.href = '#';
        firstPageLink.textContent = '1';
        firstPageLink.className = 'page-link';
        firstPageLink.addEventListener('click', function(e) {
            e.preventDefault();
            currentPage = 1;
            displayFiles(files, displayType === 'matches' ? 'match' : 'mismatch');
            updatePagination(files);
        });
        pagination.appendChild(firstPageLink);

        const ellipsis = document.createElement('span');
        ellipsis.textContent = '...';
        pagination.appendChild(ellipsis);
    }

    for (let i = startPage; i <= endPage; i++) {
        const link = document.createElement('a');
        link.href = '#';
        link.textContent = i;
        link.className = i === currentPage ? 'active' : '';
        link.addEventListener('click', function(e) {
            e.preventDefault();
            currentPage = i;
            displayFiles(files, displayType === 'matches' ? 'match' : 'mismatch');
            updatePagination(files);
        });
        pagination.appendChild(link);
    }

    if (endPage < totalPages) {
        const ellipsis = document.createElement('span');
        ellipsis.textContent = '...';
        pagination.appendChild(ellipsis);

        const lastPageLink = document.createElement('a');
        lastPageLink.href = '#';
        lastPageLink.textContent = totalPages;
        lastPageLink.className = 'page-link';
        lastPageLink.addEventListener('click', function(e) {
            e.preventDefault();
            currentPage = totalPages;
            displayFiles(files, displayType === 'matches' ? 'match' : 'mismatch');
            updatePagination(files);
        });
        pagination.appendChild(lastPageLink);
    }
}

function handleClear(selectElement) {
    const action = selectElement.value;
    if (action) {
        let url;
        if (action === 'clearMismatchedFiles') {
            url = '/clear_mismatched_folder';
        } else if (action === 'clearMatchedFiles') {
            url = '/clear_matched_folder';
        }
        if (url) {
            let xhr = new XMLHttpRequest();
            xhr.open('POST', url);
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.onload = () => {
                let message = document.getElementById('message');
                if (xhr.status === 200) {
                    let response = JSON.parse(xhr.responseText);
                    if (response.status === 'success') {
                        message.innerHTML = `<div class="notification-item"><span class="notification-text"><strong>${action.replace('clear', '').replace('Files', '')} directory cleared successfully.</strong></span></div>`;
                    } else {
                        message.innerHTML = `<div class="notification-item"><span class="notification-text"><strong>Failed to clear ${action.replace('clear', '').replace('Files', '')} directory: ${response.message}</strong></span></div>`;
                    }
                } else {
                    let response = JSON.parse(xhr.responseText);
                    message.innerHTML = `<div class="notification-item"><span class="notification-text"><strong>Request failed: ${response.message}</strong></span></div>`;
                }
            };
            xhr.onerror = function() {
                let message = document.getElementById('message');
                message.innerHTML = `<div class="notification-item"><span class="notification-text"><strong>Request failed</strong></span></div>`;
            };
            xhr.send();
        }
    }
}

function handleDownload(selectElement) {
    const url = selectElement.value;
    if (url) {
        window.location.href = url;
    }
}

function setDisplayType(type) {
    displayType = type;
    if (displayType === 'matches') {
        displayFiles(matches, 'match');
    } else {
        displayFiles(mismatches, 'mismatch');
    }
    updatePagination(displayType === 'matches' ? matches : mismatches);
}
