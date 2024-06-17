document.getElementById('compareForm').addEventListener('submit', function(e) {
    e.preventDefault();
    const folder1 = document.getElementById('folder1').value;
    const folder2 = document.getElementById('folder2').value;
    fetchMismatchedFiles(folder1, folder2);
});

let currentPage = 1;
const filesPerPage = 10;
let mismatchedFiles = [];

function fetchMismatchedFiles(folder1, folder2) {
    fetch('/compare_pdfs', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ folder1, folder2 }),
    })
    .then(response => response.json())
    .then(data => {
        mismatchedFiles = data.mismatch_pdfs;
        if (mismatchedFiles.length === 0) {
            displayNoMismatchesMessage();
        } else {
            displayFiles(1);
            updatePagination();
        }
    })
    .catch(error => console.error('Error fetching mismatched folders:', error));
}

function displayFiles(page) {
    const startIndex = (page - 1) * filesPerPage;
    const endIndex = startIndex + filesPerPage;
    const filesToDisplay = mismatchedFiles.slice(startIndex, endIndex);

    const mismatchList = document.getElementById('matchList');
    mismatchList.innerHTML = '';
    filesToDisplay.forEach(file => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="file-name">${file.message}</td>
            <td class="download-link"><a href="/matched_files/${file.download_link}" class="download-btn" download="${file.download_link}">Download</a></td>
        `;
        mismatchList.appendChild(row);
    });
}

function displayNoMismatchesMessage() {
    const mismatchList = document.getElementById('matchList');
    mismatchList.innerHTML = '<tr><td colspan="2">No matched files found.</td></tr>';

    const pagination = document.getElementById('pagination');
    pagination.innerHTML = ''; // Clear pagination if no mismatched files
}

function updatePagination() {
    const totalPages = Math.ceil(mismatchedFiles.length / filesPerPage);
    const pagination = document.getElementById('pagination');
    pagination.innerHTML = '';

    for (let i = 1; i <= totalPages; i++) {
        const link = document.createElement('a');
        link.href = '#';
        link.textContent = i;
        link.className = i === currentPage ? 'active' : '';
        link.addEventListener('click', function(e) {
            e.preventDefault();
            currentPage = i;
            displayFiles(i);
            updatePagination();
        });
        pagination.appendChild(link);
    }
}
