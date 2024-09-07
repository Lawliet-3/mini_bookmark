document.getElementById('url-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const url = document.getElementById('url-input').value;
    const response = await fetch('/fetch', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url }),
    });
    const data = await response.json();
    if (data.error) {
        document.getElementById('content-display').textContent = `Error: ${data.error}`;
    } else {
        displayParsedContent(data);
    }
});

function displayParsedContent(data) {
    const contentDisplay = document.getElementById('content-display');
    contentDisplay.innerHTML = `
        <h2>${data.title}</h2>
        <p><strong>URL:</strong> ${data.url}</p>
        <h3>Main Content:</h3>
        <p>${data.main_content}</p>
        <h3>Metadata:</h3>
        <ul>
            <li><strong>Author:</strong> ${data.metadata.author}</li>
            <li><strong>Description:</strong> ${data.metadata.description}</li>
            <li><strong>Keywords:</strong> ${data.metadata.keywords}</li>
        </ul>
        <button onclick="saveBookmark(${JSON.stringify(data)})">Save Bookmark</button>
    `;
}

async function saveBookmark(data) {
    const response = await fetch('/save', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
    });
    const result = await response.json();
    alert(result.message);
}

async function loadBookmarks() {
    const response = await fetch('/bookmarks');
    const bookmarks = await response.json();
    const bookmarksList = document.getElementById('bookmarks-list');
    bookmarksList.innerHTML = bookmarks.map(bookmark => `
        <li>
            <a href="${bookmark.url}" target="_blank">${bookmark.title}</a>
        </li>
    `).join('');
}

// Call loadBookmarks when the page loads
window.addEventListener('load', loadBookmarks);