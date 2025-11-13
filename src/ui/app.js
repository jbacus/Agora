// Virtual Debate Panel - Frontend JavaScript

const API_BASE_URL = 'http://localhost:8000/api';

// State
let authors = [];

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
    setupEventListeners();
});

// Initialize application
async function initializeApp() {
    await loadAuthors();
    updateThresholdDisplay();
}

// Load available authors
async function loadAuthors() {
    try {
        const response = await fetch(`${API_BASE_URL}/authors`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        authors = data.authors;

        // Populate author select
        const select = document.getElementById('authorSelect');
        authors.forEach(author => {
            const option = document.createElement('option');
            option.value = author.id;
            option.textContent = author.name;
            select.appendChild(option);
        });

        console.log(`Loaded ${authors.length} authors`);
    } catch (error) {
        console.error('Failed to load authors:', error);
        showStatus('Failed to load authors. Please check API connection.', 'error');
    }
}

// Setup event listeners
function setupEventListeners() {
    // Submit button
    document.getElementById('submitBtn').addEventListener('click', handleSubmit);

    // Enter key in textarea
    document.getElementById('queryInput').addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
            handleSubmit();
        }
    });

    // Threshold slider
    document.getElementById('threshold').addEventListener('input', updateThresholdDisplay);
}

// Update threshold display
function updateThresholdDisplay() {
    const threshold = document.getElementById('threshold').value;
    document.getElementById('thresholdValue').textContent = threshold;
}

// Handle form submission
async function handleSubmit() {
    const queryText = document.getElementById('queryInput').value.trim();

    if (!queryText) {
        showStatus('Please enter a question', 'error');
        return;
    }

    // Get form values
    const authorSelect = document.getElementById('authorSelect');
    const selectedAuthors = Array.from(authorSelect.selectedOptions)
        .map(opt => opt.value)
        .filter(val => val !== '');

    const maxAuthors = parseInt(document.getElementById('maxAuthors').value);
    const threshold = parseFloat(document.getElementById('threshold').value);

    // Build request
    const request = {
        text: queryText,
        max_authors: maxAuthors,
        min_authors: 2,
        relevance_threshold: threshold
    };

    if (selectedAuthors.length > 0) {
        request.specified_authors = selectedAuthors;
    }

    // Show loading state
    setLoadingState(true);
    hideResults();
    showStatus('Querying the debate panel...', 'loading');

    try {
        const response = await fetch(`${API_BASE_URL}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(request)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }

        const data = await response.json();
        displayResults(data);
        hideStatus();

    } catch (error) {
        console.error('Query failed:', error);
        showStatus(`Error: ${error.message}`, 'error');
    } finally {
        setLoadingState(false);
    }
}

// Display results
function displayResults(data) {
    // Show results section
    document.getElementById('resultsSection').style.display = 'block';

    // Display query info
    document.getElementById('displayQuery').textContent = data.query_text;
    document.getElementById('panelInfo').textContent =
        `${data.author_count} authors (${data.selection_method} selection)`;
    document.getElementById('timingInfo').textContent =
        `Generated in ${data.total_time_ms.toFixed(0)}ms`;

    // Clear previous responses
    const container = document.getElementById('responsesContainer');
    container.innerHTML = '';

    // Display author responses
    data.authors.forEach((author, index) => {
        const responseDiv = createAuthorResponseElement(author, index + 1);
        container.appendChild(responseDiv);
    });

    // Scroll to results
    document.getElementById('resultsSection').scrollIntoView({
        behavior: 'smooth',
        block: 'start'
    });
}

// Create author response element
function createAuthorResponseElement(author, rank) {
    const div = document.createElement('div');
    div.className = 'author-response';

    // Parse response text into paragraphs
    const paragraphs = author.response_text
        .split('\n\n')
        .filter(p => p.trim())
        .map(p => `<p>${escapeHtml(p.trim())}</p>`)
        .join('');

    div.innerHTML = `
        <div class="author-header">
            <div class="author-name">${rank}. ${escapeHtml(author.author_name)}</div>
            <div class="relevance-score">Relevance: ${author.relevance_score.toFixed(2)}</div>
        </div>
        <div class="response-text">
            ${paragraphs}
        </div>
    `;

    return div;
}

// Show status message
function showStatus(message, type = 'loading') {
    const section = document.getElementById('statusSection');
    const messageDiv = section.querySelector('.status-message');

    messageDiv.textContent = message;
    messageDiv.className = `status-message ${type}`;
    section.style.display = 'block';
}

// Hide status message
function hideStatus() {
    document.getElementById('statusSection').style.display = 'none';
}

// Hide results
function hideResults() {
    document.getElementById('resultsSection').style.display = 'none';
}

// Set loading state
function setLoadingState(loading) {
    const button = document.getElementById('submitBtn');
    const btnText = button.querySelector('.btn-text');
    const spinner = button.querySelector('.spinner');

    button.disabled = loading;

    if (loading) {
        btnText.style.display = 'none';
        spinner.style.display = 'inline-block';
    } else {
        btnText.style.display = 'inline';
        spinner.style.display = 'none';
    }
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Export for testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        loadAuthors,
        handleSubmit,
        displayResults
    };
}
