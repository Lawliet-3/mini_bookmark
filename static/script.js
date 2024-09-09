document.addEventListener('DOMContentLoaded', function() {
    const urlForm = document.getElementById('url-form');
    const urlInput = document.getElementById('url-input');
    const contentDisplay = document.getElementById('content-display');
    const saveButton = document.getElementById('save-button');
    const downloadButton = document.getElementById('download-button');
    const actionButtons = document.getElementById('action-buttons');

    urlForm.addEventListener('submit', function(e) {
        e.preventDefault();
        fetchContent(urlInput.value);
    });

    saveButton.addEventListener('click', saveBookmark);
    downloadButton.addEventListener('click', function() {
        const url = this.dataset.url;
        const title = this.dataset.title;
        const summary = this.dataset.summary;

        // Create the content for the file
        const content = `URL: ${url}\n\nTitle: ${title}\n\nSummary:\n${summary}`;

        // Create a Blob with the content
        const blob = new Blob([content], { type: 'text/plain' });

        // Create a temporary URL for the Blob
        const downloadUrl = window.URL.createObjectURL(blob);

        // Create a temporary anchor element and trigger the download
        const tempLink = document.createElement('a');
        tempLink.href = downloadUrl;
        tempLink.download = `${title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.txt`;
        document.body.appendChild(tempLink);
        tempLink.click();
        document.body.removeChild(tempLink);

        // Clean up the temporary URL
        window.URL.revokeObjectURL(downloadUrl);
    });

    function fetchContent(url) {
        fetch('/fetch', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({url: url}),
        })
        .then(response => {
            console.log('Response status:', response.status);
            console.log('Response headers:', response.headers);
            return response.text().then(text => {
                try {
                    return JSON.parse(text);
                } catch (e) {
                    console.error('Error parsing JSON:', e);
                    console.log('Raw response:', text);
                    throw new Error('Invalid JSON response from server');
                }
            });
        })
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            if (contentDisplay) {
                contentDisplay.innerHTML = `
                    <h2>${data.title || 'No title'}</h2>
                    <h3>Summary:</h3>
                    <p>${data.summary || 'No summary available'}</p>
                    <h3>Full Text:</h3>
                    <p>${data.full_text || 'No full text available'}</p>
                `;
            } else {
                console.error('contentDisplay element not found');
            }
            if (saveButton) {
                saveButton.dataset.url = url;
                saveButton.dataset.title = data.title || 'No title';
                saveButton.dataset.summary = data.summary || 'No summary available';
            } else {
                console.error('saveButton element not found');
            }
            if (downloadButton) {
                downloadButton.dataset.url = url;
                downloadButton.dataset.title = data.title || 'No title';
                downloadButton.dataset.summary = data.summary || 'No summary available';
            } else {
                console.error('downloadButton element not found');
            }
            if (actionButtons) {
                actionButtons.style.display = 'flex';
            } else {
                console.error('actionButtons element not found');
            }
        })
        .catch(error => {
            console.error('Fetch error:', error);
            if (contentDisplay) {
                contentDisplay.innerHTML = `<p>Error: ${error.message || 'An error occurred while fetching the content.'}</p>`;
            } else {
                console.error('contentDisplay element not found');
            }
        });
    }

    function saveBookmark() {
        const bookmarkData = {
            url: saveButton.dataset.url,
            title: saveButton.dataset.title,
            summary: saveButton.dataset.summary
        };

        fetch('/save_bookmark', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(bookmarkData),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Bookmark saved successfully!');
                loadBookmarks();  // Reload the bookmarks list
            } else {
                alert('Failed to save bookmark.');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while saving the bookmark.');
        });
    }

    function loadBookmarks() {
        fetch('/bookmarks')
            .then(response => response.json())
            .then(bookmarks => {
                const bookmarkList = document.getElementById('bookmark-list');
                bookmarkList.innerHTML = '';
                bookmarks.forEach(bookmark => {
                    const item = document.createElement('li');
                    item.className = 'bg-gray-50 rounded-lg p-4 shadow-sm hover:shadow-md transition duration-300';
                    item.innerHTML = `
                        <div class="flex items-center justify-between">
                            <div>
                                <h3 class="text-lg font-semibold text-gray-800">${bookmark.title}</h3>
                                <p class="text-sm text-gray-600">${bookmark.url}</p>
                            </div>
                            <div class="flex space-x-2">
                                <button class="text-blue-500 hover:text-blue-700" onclick="editBookmark('${bookmark._id}')">
                                    <i class="fas fa-edit"></i>
                                </button>
                                <button class="text-red-500 hover:text-red-700" onclick="deleteBookmark('${bookmark._id}')">
                                    <i class="fas fa-trash-alt"></i>
                                </button>
                            </div>
                        </div>
                    `;
                    bookmarkList.appendChild(item);
                });
            })
            .catch(error => {
                console.error('Error loading bookmarks:', error);
            });
    }

    // Call loadBookmarks when the page loads
    document.addEventListener('DOMContentLoaded', loadBookmarks);

    // Initially hide the action buttons
    if (actionButtons) {
        actionButtons.style.display = 'none';
    }
});