document.addEventListener('DOMContentLoaded', function() {
    let currentPage = 1;
    const filesPerPage = 10;
    const notifications = JSON.parse(document.getElementById('notifications-data').textContent);

    function displayNotifications(page) {
        const startIndex = (page - 1) * filesPerPage;
        const endIndex = startIndex + filesPerPage;
        const notificationsToDisplay = notifications.slice(startIndex, endIndex);

        const notificationList = document.querySelector('tbody');
        notificationList.innerHTML = '';

        if (notificationsToDisplay.length > 0) {
            notificationsToDisplay.forEach(notification => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td class="message">${notification.message}</td>
                    <td>${notification.timestamp}</td>
                    <td>${notification.signature}</td>
                    <td>${notification.download_link ? `<a class="download-btn" href="/download/${notification.download_link}" download>Download</a>` : ''}</td>
                `;
                notificationList.appendChild(row);
            });
        } else {
            notificationList.innerHTML = '<tr><td colspan="4"><strong>No notifications to display.</strong></td></tr>';
        }
    }

    function updatePagination() {
        const totalPages = Math.ceil(notifications.length / filesPerPage);
        const pagination = document.querySelector('.pagination');
        const pageSummary = document.getElementById('page-summary');
        pageSummary.textContent = `Page ${currentPage} of ${totalPages}`;
        pagination.innerHTML = '';

        const maxPageLinks = 5;
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
                displayNotifications(currentPage);
                updatePagination();
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
                displayNotifications(currentPage);
                updatePagination();
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
                displayNotifications(currentPage);
                updatePagination();
            });
            pagination.appendChild(lastPageLink);
        }
    }

    displayNotifications(currentPage);
    updatePagination();
});
