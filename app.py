import json
import os
from flask import Flask, render_template, request, jsonify
from bs4 import BeautifulSoup
import requests
from trafilatura import extract
import asyncio
from playwright.async_api import async_playwright
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
import nltk
from nltk.corpus import stopwords
import time
import robotexclusionrulesparser

app = Flask(__name__)

BOOKMARKS_FILE = 'bookmarks.json'

# Download necessary NLTK data
nltk.download('stopwords')
nltk.download('punkt')

# Initialize the robots.txt parser
rp = robotexclusionrulesparser.RobotExclusionRulesParser()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/fetch', methods=['POST'])
async def fetch_url():
    url = request.json['url']
    try:
        # Check robots.txt
        robots_url = f"{url.split('//', 1)[0]}//{url.split('//', 1)[1].split('/', 1)[0]}/robots.txt"
        rp.fetch(robots_url)
        if not rp.is_allowed(url, '*'):
            return jsonify({'error': 'Access to this URL is not allowed by robots.txt'}), 403

        # Implement rate limiting
        time.sleep(1)  # Simple delay-based rate limiting

        # Fetch content with JavaScript support
        html_content = await fetch_url_with_js(url)
        parsed_content = parse_content(html_content, url)
        return jsonify(parsed_content)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/save', methods=['POST'])
def save_bookmark():
    bookmark = request.json
    bookmarks = load_bookmarks()
    bookmarks.append(bookmark)
    save_bookmarks(bookmarks)
    return jsonify({'message': 'Bookmark saved successfully'})

@app.route('/bookmarks', methods=['GET'])
def get_bookmarks():
    bookmarks = load_bookmarks()
    return jsonify(bookmarks)

async def fetch_url_with_js(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url)
        # Wait for any JavaScript to finish executing
        await page.wait_for_load_state('networkidle')
        content = await page.content()
        await browser.close()
        return content

def parse_content(html_content, url):
    soup = BeautifulSoup(html_content, 'lxml')
    
    title = soup.title.string if soup.title else ''
    
    # Use a more sophisticated content extraction method
    main_content = extract_main_content(html_content)
    
    metadata = {
        'author': soup.find('meta', {'name': 'author'})['content'] if soup.find('meta', {'name': 'author'}) else '',
        'description': soup.find('meta', {'name': 'description'})['content'] if soup.find('meta', {'name': 'description'}) else '',
        'keywords': soup.find('meta', {'name': 'keywords'})['content'] if soup.find('meta', {'name': 'keywords'}) else '',
    }
    
    # Try to extract Open Graph metadata
    og_title = soup.find('meta', {'property': 'og:title'})
    og_description = soup.find('meta', {'property': 'og:description'})
    if og_title:
        metadata['og_title'] = og_title['content']
    if og_description:
        metadata['og_description'] = og_description['content']
    
    content_type = classify_content_ml(title, main_content)
    
    links = extract_links(soup, url)
    
    return {
        'title': title,
        'main_content': main_content,
        'metadata': metadata,
        'url': url,
        'content_type': content_type,
        'links': links
    }

def load_bookmarks():
    if os.path.exists(BOOKMARKS_FILE):
        with open(BOOKMARKS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_bookmarks(bookmarks):
    with open(BOOKMARKS_FILE, 'w') as f:
        json.dump(bookmarks, f)

def extract_links(soup, base_url):
    links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        full_url = requests.compat.urljoin(base_url, href)
        links.append({'text': a.text.strip(), 'url': full_url})
    return links

def classify_content_ml(title, main_content):
    combined_text = f"{title} {main_content}"
    return classifier.predict([combined_text])[0]

def extract_main_content(html_content):
    # Use readability-lxml for better content extraction
    from readability import Document
    doc = Document(html_content)
    return doc.summary()

# Train a simple ML model for content classification
def train_classifier():
    # This is a placeholder. In a real scenario, you'd use a larger, labeled dataset.
    X = ["This is a news article about current events",
         "Check out our new product for sale",
         "Welcome to my personal blog",
         "Here's the documentation for our API"]
    y = ["news", "product", "blog", "documentation"]

    classifier = Pipeline([
        ('tfidf', TfidfVectorizer(stop_words=stopwords.words('english'))),
        ('clf', MultinomialNB()),
    ])
    classifier.fit(X, y)
    return classifier

classifier = train_classifier()

if __name__ == '__main__':
    app.run(debug=True)