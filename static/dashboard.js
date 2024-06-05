document.addEventListener('DOMContentLoaded', function() {
    const keywordToggle = document.getElementById('keyword-toggle');
    const manualKeywords = document.getElementById('manual-keywords');
    const keywordForm = document.getElementById('keyword-form');
    const toggleButton = document.getElementById('toggle-keywords');
    const currentKeywords = document.getElementById('current-keywords');
    const primaryKeywordsContainer = document.getElementById('primary-keywords-container');
    const secondaryKeywordsContainer = document.getElementById('secondary-keywords-container');
    const addPrimaryKeywordButton = document.getElementById('add-primary-keyword');
    const addSecondaryKeywordButton = document.getElementById('add-secondary-keyword');
    const primaryKeywordsList = document.getElementById('primary-keywords-list');
    const secondaryKeywordsList = document.getElementById('secondary-keywords-list');

    // Load initial keyword toggle state from localStorage
    if (localStorage.getItem('keywordToggle') === 'manual') {
        keywordToggle.checked = true;
        manualKeywords.style.display = 'block';
    } else {
        keywordToggle.checked = false;
        manualKeywords.style.display = 'none';
    }

    keywordToggle.addEventListener('change', function() {
        if (this.checked) {
            manualKeywords.style.display = 'block';
            localStorage.setItem('keywordToggle', 'manual');
        } else {
            manualKeywords.style.display = 'none';
            localStorage.setItem('keywordToggle', 'default');
        }
    });

    addPrimaryKeywordButton.addEventListener('click', function() {
        const input = document.createElement('input');
        input.type = 'text';
        input.name = 'primary_keywords[]';
        input.placeholder = 'Enter primary keywords';
        primaryKeywordsContainer.appendChild(input);
    });

    addSecondaryKeywordButton.addEventListener('click', function() {
        const input = document.createElement('input');
        input.type = 'text';
        input.name = 'secondary_keywords[]';
        input.placeholder = 'Enter secondary keywords';
        secondaryKeywordsContainer.appendChild(input);
    });

    keywordForm.addEventListener('submit', function(event) {
        event.preventDefault();
        const formData = new FormData(keywordForm);
        const keywordOption = keywordToggle.checked ? 'manual' : 'default';
        const primaryKeywords = formData.getAll('primary_keywords[]');
        const secondaryKeywords = formData.getAll('secondary_keywords[]');

        fetch('/set_keywords', {
            method: 'POST',
            body: JSON.stringify({
                keyword_option: keywordOption,
                primary_keywords: primaryKeywords,
                secondary_keywords: secondaryKeywords
            }),
            headers: {
                'Content-Type': 'application/json'
            }
        }).then(response => response.json()).then(data => {
            console.log(data);
            // Refresh keywords display
            refreshKeywords();
        });
    });

    toggleButton.addEventListener('click', function() {
        if (currentKeywords.style.display === 'none') {
            currentKeywords.style.display = 'block';
            toggleButton.textContent = 'Hide Keywords';
            refreshKeywords();
        } else {
            currentKeywords.style.display = 'none';
            toggleButton.textContent = 'Show Keywords';
        }
    });

    // Function to fetch and display current keywords
    function refreshKeywords() {
        fetch('/get_keywords')
            .then(response => response.json())
            .then(data => {
                primaryKeywordsList.innerHTML = '';
                secondaryKeywordsList.innerHTML = '';

                data.primary_keywords.forEach(keyword => {
                    const li = document.createElement('li');
                    li.textContent = keyword.replace(/\\/g, '');
                    primaryKeywordsList.appendChild(li);
                });

                data.secondary_keywords.forEach(keyword => {
                    const li = document.createElement('li');
                    li.textContent = keyword.replace(/\\/g, '');
                    secondaryKeywordsList.appendChild(li);
                });
            });
    }

    // Initial fetch and display current keywords
    refreshKeywords();
});
