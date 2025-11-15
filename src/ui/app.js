// Agora Virtual Debate Panel - Frontend Application
const API_URL = window.location.hostname === 'localhost'
    ? 'http://localhost:8000'
    : 'https://agora-backend-uc.a.run.app';

const queryInput = document.getElementById('query-input');
const submitBtn = document.getElementById('submit-btn');
const debateBtn = document.getElementById('debate-btn');
const clearBtn = document.getElementById('clear-btn');
const numRoundsInput = document.getElementById('num-rounds');
const selectedAuthorsDiv = document.getElementById('selected-authors');
const authorsListDiv = document.getElementById('authors-list');
const responsesDiv = document.getElementById('responses');
const loadingDiv = document.getElementById('loading');
const themeToggle = document.getElementById('theme-toggle');
const themeIcon = document.getElementById('theme-icon');

let currentQuery = '';
let isLoading = false;

// Theme management
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    if (savedTheme === 'dark') {
        document.body.classList.add('dark');
        themeIcon.textContent = '🌙';
    } else {
        document.body.classList.remove('dark');
        themeIcon.textContent = '☀️';
    }
}

function toggleTheme() {
    document.body.classList.toggle('dark');
    const isDark = document.body.classList.contains('dark');
    themeIcon.textContent = isDark ? '🌙' : '☀️';
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
}

// Event listeners
submitBtn.addEventListener('click', () => handleSubmit(false));
debateBtn.addEventListener('click', () => handleSubmit(true));
clearBtn.addEventListener('click', handleClear);
themeToggle.addEventListener('click', toggleTheme);

queryInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && e.ctrlKey) {
        e.preventDefault();
        handleSubmit(false);
    }
});

async function submitQuery(query, isDebate = false) {
    // Use streaming for debates, regular endpoint for queries
    const endpoint = isDebate ? '/api/query/debate/agentic/stream' : '/api/query';
    const body = isDebate
        ? { text: query, max_authors: 5, num_rounds: parseInt(numRoundsInput.value) || 2 }
        : { text: query, max_authors: 5, relevance_threshold: 0.7 };

    const response = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    });
    if (!response.ok) throw new Error('Query failed');

    // Return response object for streaming, or JSON for regular query
    return isDebate ? response : response.json();
}

function showLoading(isDebate = false) {
    isLoading = true;
    submitBtn.disabled = true;
    debateBtn.disabled = true;
    loadingDiv.classList.remove('hidden');
    loadingDiv.querySelector('p').textContent = isDebate
        ? 'Starting agentic debate (authors will use tools to search their works)...'
        : 'Consulting the panel...';
    responsesDiv.innerHTML = '';
    selectedAuthorsDiv.classList.add('hidden');
}

function hideLoading() {
    isLoading = false;
    submitBtn.disabled = false;
    debateBtn.disabled = false;
    loadingDiv.classList.add('hidden');
}

function displayAuthors(authors) {
    const authorList = Array.isArray(authors) ? authors : authors.map(a => ({
        name: a.author_name,
        id: a.author_id
    }));

    authorsListDiv.innerHTML = authorList.map(author => `
        <span class="author-badge">
            ${author.name || author.author_name}
        </span>
    `).join('');
    selectedAuthorsDiv.classList.remove('hidden');
}

function formatResponse(text) {
    // Split into paragraphs
    const paragraphs = text.split('\n\n').filter(p => p.trim());

    return paragraphs.map(p => {
        // Add emphasis for quoted text or italicized phrases
        let formatted = p;

        // Convert **bold** to <strong>
        formatted = formatted.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

        // Convert *italic* to <em>
        formatted = formatted.replace(/\*(.+?)\*/g, '<em>$1</em>');

        // Convert _italic_ to <em>
        formatted = formatted.replace(/_(.+?)_/g, '<em>$1</em>');

        return `<p>${formatted}</p>`;
    }).join('');
}

function buildCitations(response) {
    // If retrieved_chunks exist, build citations
    if (!response.retrieved_chunks || response.retrieved_chunks.length === 0) {
        return '';
    }

    const uniqueSources = new Map();

    response.retrieved_chunks.forEach(chunk => {
        if (chunk.metadata && chunk.metadata.book) {
            // Format book name nicely (replace underscores with spaces, capitalize)
            const bookName = chunk.metadata.book
                .replace(/_/g, ' ')
                .replace(/\b\w/g, l => l.toUpperCase());
            const key = chunk.metadata.book;

            if (!uniqueSources.has(key)) {
                const citation = {
                    source: bookName,
                    book_id: chunk.metadata.book
                };
                uniqueSources.set(key, citation);
            }
        }
    });

    if (uniqueSources.size === 0) {
        return '';
    }

    const citationList = Array.from(uniqueSources.values())
        .map(c => `<span class="citation-title">${c.source}</span>`)
        .join(', ');

    return `<div class="citation">Sources: ${citationList}</div>`;
}

function displayResponses(responses) {
    responsesDiv.innerHTML = responses.map(response => `
        <div class="author-card">
            <div class="flex items-center gap-4 mb-6">
                <div>
                    <h3 class="font-bold text-xl mb-1">${response.author_name}</h3>
                    <p class="text-sm text-gray-500 dark:text-gray-400">Relevance: ${(response.relevance_score * 100).toFixed(0)}%</p>
                </div>
            </div>
            <div class="prose">
                ${formatResponse(response.response_text)}
                ${buildCitations(response)}
            </div>
        </div>
    `).join('');
}

function displayDebate(debateData) {
    // Show authors from first round
    if (debateData.rounds && debateData.rounds[0]) {
        displayAuthors(debateData.rounds[0].author_responses);
    }

    // Display rounds
    responsesDiv.innerHTML = debateData.rounds.map((round, roundIdx) => `
        <div class="mb-10">
            <span class="round-badge">
                Round ${round.round_number}: ${getRoundLabel(round.round_type)}
            </span>
            <div class="space-y-6 mt-4">
                ${round.author_responses.map(response => `
                    <div class="author-card">
                        <div class="flex items-center gap-4 mb-6">
                            <div>
                                <h3 class="font-bold text-xl mb-1">${response.author_name}</h3>
                                ${round.round_number === 1 ? `<p class="text-sm text-gray-500 dark:text-gray-400">Relevance: ${(response.relevance_score * 100).toFixed(0)}%</p>` : ''}
                            </div>
                        </div>
                        <div class="prose">
                            ${formatResponse(response.response_text)}
                            ${buildCitations(response)}
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
    `).join('');
}

function getRoundLabel(roundType) {
    const labels = {
        'initial': 'Initial Responses',
        'rebuttal': 'Rebuttals',
        'response': 'Continued Discussion'
    };
    return labels[roundType] || roundType;
}

async function handleSubmit(isDebate = false) {
    const query = queryInput.value.trim();
    if (!query || isLoading) return;

    currentQuery = query;
    showLoading(isDebate);

    try {
        if (isDebate) {
            // Handle streaming debate
            await handleStreamingDebate(query);
        } else {
            // Handle regular query
            const data = await submitQuery(query, false);
            hideLoading();
            displayAuthors(data.authors);
            displayResponses(data.authors);
        }
    } catch (error) {
        hideLoading();
        responsesDiv.innerHTML = `
            <div class="border border-gray-300 dark:border-gray-700 p-6">
                <p class="text-gray-800 dark:text-gray-200 font-medium">Error: ${error.message}</p>
            </div>`;
    }
}

async function handleStreamingDebate(query) {
    const response = await submitQuery(query, true);
    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    const debateState = {
        rounds: [],
        currentRound: null,
        authors: [],
        currentAuthorResponse: null
    };

    try {
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;

                const data = JSON.parse(line.slice(6));

                switch (data.type) {
                    case 'authors':
                        debateState.authors = data.authors;
                        displayAuthors(data.authors);
                        hideLoading();
                        break;

                    case 'round_start':
                        debateState.currentRound = {
                            round_number: data.round_number,
                            round_type: data.round_type,
                            author_responses: []
                        };
                        debateState.rounds.push(debateState.currentRound);
                        displayDebateStreaming(debateState);
                        break;

                    case 'author_start':
                        // Start new author response
                        debateState.currentAuthorResponse = {
                            author_id: data.author_id,
                            author_name: data.author_name,
                            response_text: '',
                            relevance_score: 0,
                            retrieved_chunks: [],
                            streaming: true
                        };
                        debateState.currentRound.author_responses.push(debateState.currentAuthorResponse);
                        displayDebateStreaming(debateState);
                        break;

                    case 'token':
                        // Append token to current response
                        if (debateState.currentAuthorResponse && data.author_id === debateState.currentAuthorResponse.author_id) {
                            debateState.currentAuthorResponse.response_text += data.token;
                            displayDebateStreaming(debateState);
                        }
                        break;

                    case 'response_complete':
                        // Finalize response
                        if (debateState.currentAuthorResponse) {
                            debateState.currentAuthorResponse.response_text = data.response_text;
                            debateState.currentAuthorResponse.relevance_score = data.relevance_score;
                            debateState.currentAuthorResponse.retrieved_chunks = data.retrieved_chunks;
                            debateState.currentAuthorResponse.streaming = false;
                            debateState.currentAuthorResponse = null;
                            displayDebateStreaming(debateState);
                        }
                        break;

                    case 'done':
                        console.log('Debate complete. Stats:', data.stats);
                        break;

                    case 'error':
                        throw new Error(data.message);
                }
            }
        }
    } finally {
        reader.releaseLock();
    }
}

function displayDebateStreaming(debateState) {
    // Display rounds as they come in
    responsesDiv.innerHTML = debateState.rounds.map((round, roundIdx) => `
        <div class="mb-10">
            <span class="round-badge">
                Round ${round.round_number}: ${getRoundLabel(round.round_type)}
            </span>
            <div class="space-y-6 mt-4">
                ${round.author_responses.map(response => `
                    <div class="author-card">
                        <div class="flex items-center gap-4 mb-6">
                            <div>
                                <h3 class="font-bold text-xl mb-1">${response.author_name}</h3>
                                ${round.round_number === 1 && response.relevance_score ? `<p class="text-sm text-gray-500 dark:text-gray-400">Relevance: ${(response.relevance_score * 100).toFixed(0)}%</p>` : ''}
                            </div>
                        </div>
                        <div class="prose">
                            ${formatResponse(response.response_text)}${response.streaming ? '<span class="inline-block w-2 h-5 ml-1 bg-blue-500 animate-pulse"></span>' : ''}
                            ${!response.streaming && response.retrieved_chunks ? buildCitations(response) : ''}
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
    `).join('');

    // Auto-scroll to bottom as new content appears
    const lastCard = responsesDiv.lastElementChild;
    if (lastCard) {
        lastCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

function handleClear() {
    queryInput.value = '';
    responsesDiv.innerHTML = '';
    selectedAuthorsDiv.classList.add('hidden');
    currentQuery = '';
}

// Initialize theme on load
initTheme();

console.log('Agora Virtual Debate Panel loaded');
