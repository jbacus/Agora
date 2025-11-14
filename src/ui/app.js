// Agora Virtual Debate Panel - Frontend Application
const API_URL = window.location.hostname === 'localhost' 
    ? 'http://localhost:8000'
    : 'https://agora-backend-uc.a.run.app';

const queryInput = document.getElementById('query-input');
const submitBtn = document.getElementById('submit-btn');
const clearBtn = document.getElementById('clear-btn');
const selectedAuthorsDiv = document.getElementById('selected-authors');
const authorsListDiv = document.getElementById('authors-list');
const responsesDiv = document.getElementById('responses');
const loadingDiv = document.getElementById('loading');

let currentQuery = '';
let isLoading = false;

submitBtn.addEventListener('click', handleSubmit);
clearBtn.addEventListener('click', handleClear);

queryInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && e.ctrlKey) {
        e.preventDefault();
        handleSubmit();
    }
});

async function submitQuery(query) {
    const response = await fetch(`${API_URL}/api/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, max_authors: 5, relevance_threshold: 0.7 })
    });
    if (!response.ok) throw new Error('Query failed');
    return response.json();
}

function showLoading() {
    isLoading = true;
    submitBtn.disabled = true;
    loadingDiv.classList.remove('hidden');
    responsesDiv.innerHTML = '';
    selectedAuthorsDiv.classList.add('hidden');
}

function hideLoading() {
    isLoading = false;
    submitBtn.disabled = false;
    loadingDiv.classList.add('hidden');
}

function displayAuthors(authors) {
    authorsListDiv.innerHTML = authors.map(author => `
        <span class="px-3 py-1 bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 rounded-full text-sm">
            ${author.name}
        </span>
    `).join('');
    selectedAuthorsDiv.classList.remove('hidden');
}

function displayResponses(responses) {
    responsesDiv.innerHTML = responses.map(response => `
        <div class="author-card ${response.author_id}">
            <div class="flex items-center gap-3 mb-4">
                <div class="w-12 h-12 bg-gray-200 dark:bg-gray-700 rounded-full flex items-center justify-center text-xl">
                    ${getAuthorEmoji(response.author_id)}
                </div>
                <div>
                    <h3 class="font-bold text-lg">${response.author_name}</h3>
                    <p class="text-sm text-gray-500">Relevance: ${(response.relevance_score * 100).toFixed(0)}%</p>
                </div>
            </div>
            <div class="prose dark:prose-invert">${formatResponse(response.response)}</div>
        </div>
    `).join('');
}

function getAuthorEmoji(authorId) {
    return { 'marx': '🔨', 'whitman': '🌿', 'baudelaire': '💪' }[authorId] || '📚';
}

function formatResponse(text) {
    return text.split('\n\n').map(p => `<p>${p}</p>`).join('');
}

async function handleSubmit() {
    const query = queryInput.value.trim();
    if (!query || isLoading) return;
    
    currentQuery = query;
    showLoading();
    
    try {
        const data = await submitQuery(query);
        hideLoading();
        displayAuthors(data.selected_authors);
        displayResponses(data.responses);
    } catch (error) {
        hideLoading();
        responsesDiv.innerHTML = `<div class="bg-red-50 border border-red-200 rounded-lg p-4"><p class="text-red-800">Error: ${error.message}</p></div>`;
    }
}

function handleClear() {
    queryInput.value = '';
    responsesDiv.innerHTML = '';
    selectedAuthorsDiv.classList.add('hidden');
    currentQuery = '';
}

console.log('Agora Virtual Debate Panel loaded');
