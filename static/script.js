document.addEventListener('DOMContentLoaded', function() {
    const urlForm = document.getElementById('url-form');
    const urlInput = document.getElementById('url-input');
    const contentDisplay = document.getElementById('content-display');
    const saveButton = document.getElementById('save-button');
    const downloadButton = document.getElementById('download-button');
    const actionButtons = document.getElementById('action-buttons');
    let contentType;

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
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            contentType = data.type;
            if (contentDisplay) {
                if (data.type === 'article') {
                    contentDisplay.innerHTML = `
                        <h2>${data.title || 'No title'}</h2>
                        <p>${data.url}</p>
                        <h3>Summary:</h3>
                        <p>${data.summary || 'No summary available'}</p>
                        <h3>Full Text:</h3>
                        <p>${data.full_text || 'No full text available'}</p>
                    `;
                } else if (data.type === 'list') {
                    let linksHtml = data.links.map(link => `
                        <div class="link-item">
                            ${link.image ? `<img src="${link.image}" alt="${link.title}" class="link-image">` : '<div class="no-image"></div>'}
                            <a href="${link.url}" target="_blank" class="link-title">${link.title}</a>
                        </div>
                    `).join('');
                    contentDisplay.innerHTML = `
                        <h2>${data.title || 'Link List'}</h2>
                        <p>${data.url}</p>
                        <div class="links-container">${linksHtml}</div>
                    `;
                }
            } else {
                console.error('contentDisplay element not found');
            }
            if (saveButton) {
                saveButton.dataset.url = url;
                saveButton.dataset.title = data.title || 'No title';
                saveButton.dataset.type = data.type;
                if (data.type === 'article') {
                    saveButton.dataset.summary = data.summary || 'No summary available';
                } else if (data.type === 'list') {
                    saveButton.dataset.links = JSON.stringify(data.links);
                }
            } else {
                console.error('saveButton element not found');
            }
            if (downloadButton) {
                downloadButton.dataset.url = url;
                downloadButton.dataset.title = data.title || 'No title';
                downloadButton.dataset.type = data.type;
                if (data.type === 'article') {
                    downloadButton.dataset.summary = data.summary || 'No summary available';
                } else if (data.type === 'list') {
                    downloadButton.dataset.links = JSON.stringify(data.links);
                }
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
        const contentDisplay = document.getElementById('content-display');
        const h2Element = contentDisplay.querySelector('h2');
        const urlElement = contentDisplay.querySelector('p');
        
        if (!h2Element || !urlElement) {
            alert('No content to save. Please fetch a URL first.');
            return;
        }

        const bookmarkData = {
            url: urlElement.textContent,
            title: h2Element.textContent,
            type: contentType // This should be set when fetching content
        };

        if (contentType === 'article') {
            const summaryElement = contentDisplay.querySelector('div');
            bookmarkData.summary = summaryElement ? summaryElement.innerHTML : 'No summary available';
        } else if (contentType === 'list') {
            const linksContainer = contentDisplay.querySelector('.links-container');
            if (linksContainer) {
                bookmarkData.links = Array.from(linksContainer.querySelectorAll('.link-item')).map(item => ({
                    title: item.querySelector('.link-title').textContent,
                    url: item.querySelector('.link-title').href,
                    image: item.querySelector('.link-image') ? item.querySelector('.link-image').src : null
                }));
            }
        }

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
                    item.className = 'bg-gray-50 rounded-lg p-4 shadow-sm hover:shadow-md transition duration-300 mb-4';
                    if (bookmark.type === 'article') {
                        item.innerHTML = `
                            <h3 class="text-lg font-semibold text-gray-800">${bookmark.title}</h3>
                            <p class="text-sm text-gray-600">${bookmark.url}</p>
                            <p class="text-sm text-gray-500 mt-2">${bookmark.summary}</p>
                            <div class="flex justify-end mt-2">
                                <button class="text-red-500 hover:text-red-700" onclick="deleteBookmark('${bookmark._id}')">
                                    <i class="fas fa-trash-alt"></i> Delete
                                </button>
                            </div>
                        `;
                    } else if (bookmark.type === 'list') {
                        const linksList = bookmark.links.map(link => `
                            <li class="mb-1">
                                <a href="${link.url}" target="_blank" class="text-blue-500 hover:underline">${link.title}</a>
                            </li>
                        `).join('');
                        item.innerHTML = `
                            <h3 class="text-lg font-semibold text-gray-800">${bookmark.title}</h3>
                            <p class="text-sm text-gray-600">${bookmark.url}</p>
                            <ul class="mt-2 list-disc list-inside">
                                ${linksList}
                            </ul>
                            <div class="flex justify-end mt-2">
                                <button class="text-red-500 hover:text-red-700" onclick="deleteBookmark('${bookmark._id}')">
                                    <i class="fas fa-trash-alt"></i> Delete
                                </button>
                            </div>
                        `;
                    }
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