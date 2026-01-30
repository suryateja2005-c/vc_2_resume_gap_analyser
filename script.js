// Page Navigation
function showPage(pageName) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById(pageName).classList.add('active');

    document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
    event.target.closest('.nav-item')?.classList.add('active');
}

// Resume Gap Analysis
async function analyzeGap() {
    const resumeText = document.getElementById('resumeTextGap').value;
    const jobDescription = document.getElementById('jobDescriptionGap').value;

    if (!resumeText || !jobDescription) {
        alert('Please provide both resume and job description');
        return;
    }

    showLoading(true);

    try {
        const response = await fetch('/api/analyze-resume-gap', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                resumeText: resumeText,
                jobDescription: jobDescription
            })
        });

        const data = await response.json();

        if (data.success) {
            displayGapResults(data);
            document.getElementById('gapResults').classList.remove('hidden');
        }
    } catch (e) {
        alert('Error analyzing gap: ' + e.message);
    } finally {
        showLoading(false);
    }
}

function displayGapResults(data) {
    const analysis = data.analysis;

    // Score
    document.getElementById('compatibilityScore').textContent = analysis.score;
    document.getElementById('matchStatus').textContent = data.status;
    document.getElementById('matchDescription').textContent = `${analysis.matched_count} out of ${analysis.total_jd_keywords} keywords matched`;

    // Matching Keywords
    const matchingDiv = document.getElementById('matchingKeywords');
    matchingDiv.innerHTML = analysis.matching_keywords.map(k =>
        `<span class="keyword-tag">${k}</span>`
    ).join('');

    // Missing Keywords
    const missingDiv = document.getElementById('missingKeywords');
    missingDiv.innerHTML = analysis.missing_keywords.map(k =>
        `<span class="keyword-tag">${k}</span>`
    ).join('');

    // Suggestions
    const suggestionsUl = document.getElementById('gapSuggestions');
    suggestionsUl.innerHTML = data.suggestions.map(s =>
        `<li>💡 ${s}</li>`
    ).join('');
}

// ATS Check
async function checkATS() {
    const resumeText = document.getElementById('resumeTextATS').value;
    const resumeFile = document.getElementById('resumeFileATS').files[0];

    if (!resumeText && !resumeFile) {
        alert('Please upload a resume (PDF) or paste resume text');
        return;
    }

    showLoading(true);

    try {
        let response;
        if (resumeFile) {
            const formData = new FormData();
            formData.append('resume', resumeFile);
            response = await fetch('/api/ats-check-upload', {
                method: 'POST',
                body: formData
            });
        } else {
            response = await fetch('/api/ats-check', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ resumeText: resumeText })
            });
        }

        const data = await response.json();

        if (data.success) {
            document.getElementById('atsScoreValue').textContent = data.score;
            document.getElementById('atsStatus').textContent = `ATS Compatibility: ${data.status}`;

            const issuesList = document.getElementById('atsIssues');
            issuesList.innerHTML = data.issues.map(issue =>
                `<li>⚠️ ${issue}</li>`
            ).join('');

            document.getElementById('atsResults').classList.remove('hidden');
        }
    } catch (e) {
        alert('Error checking ATS: ' + e.message);
    } finally {
        showLoading(false);
    }
}

// Improve Bullets
function addBulletField() {
    const bulletsList = document.getElementById('bulletsList');
    const bulletInput = document.createElement('input');
    bulletInput.type = 'text';
    bulletInput.className = 'bullet-input';
    bulletInput.placeholder = 'Enter a resume bullet point...';
    bulletInput.style.marginBottom = '10px';
    bulletsList.appendChild(bulletInput);
}

async function improveBullets() {
    const bullets = Array.from(document.querySelectorAll('.bullet-input')).map(input => input.value).filter(v => v);
    const jobDescription = document.getElementById('jobDescriptionBullets').value;

    if (bullets.length === 0) {
        alert('Please add at least one bullet point');
        return;
    }

    showLoading(true);

    try {
        const response = await fetch('/api/improve-bullets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                bullets: bullets,
                jobDescription: jobDescription
            })
        });

        const data = await response.json();

        if (data.success) {
            const improvedList = document.getElementById('improvedBulletsList');
            improvedList.innerHTML = data.improved_bullets.map(bullet =>
                `<div style="background: #f0f8ff; padding: 12px; margin: 10px 0; border-radius: 4px;">
                    <p style="color: #333;">✨ ${bullet}</p>
                </div>`
            ).join('');

            document.getElementById('improvedBulletsResult').classList.remove('hidden');
        }
    } catch (e) {
        alert('Error improving bullets: ' + e.message);
    } finally {
        showLoading(false);
    }
}

// Download Resume
async function downloadResume() {
    const fullName = document.getElementById('fullName').value;
    const email = document.getElementById('email').value;
    const phone = document.getElementById('phone').value;
    const summary = document.getElementById('summary').value;
    const skills = document.getElementById('skills').value.split(',').map(s => s.trim());

    if (!fullName) {
        alert('Please enter your full name');
        return;
    }

    showLoading(true);

    try {
        const response = await fetch('/api/generate-resume', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                fullName, email, phone, summary, skills
            })
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${fullName.replace(' ', '-')}-Resume.pdf`;
            a.click();
            showSuccess('Resume downloaded!');
        }
    } catch (e) {
        alert('Error downloading resume: ' + e.message);
    } finally {
        showLoading(false);
    }
}

// Generate Summary
async function generateSummary() {
    const industry = 'technology'; // Default
    showLoading(true);

    try {
        const response = await fetch('/api/generate-content', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                jobTitle: 'Professional',
                section: 'summary'
            })
        });

        const data = await response.json();

        if (data.success) {
            document.getElementById('summary').value = data.content;
        }
    } catch (e) {
        alert('Error generating summary: ' + e.message);
    } finally {
        showLoading(false);
    }
}

// Cover Letter
async function generateCoverLetterText() {
    const company = document.getElementById('companyName').value;
    const jobTitle = document.getElementById('coverLetterJobTitle').value;

    if (!company || !jobTitle) {
        alert('Please provide company name and job title');
        return;
    }

    showLoading(true);

    try {
        const response = await fetch('/api/generate-cover-letter', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                company: company,
                jobTitle: jobTitle
            })
        });

        const data = await response.json();

        if (data.success) {
            document.getElementById('coverLetterText').value = data.cover_letter;
            document.getElementById('coverLetterResult').classList.remove('hidden');
        }
    } catch (e) {
        alert('Error generating cover letter: ' + e.message);
    } finally {
        showLoading(false);
    }
}

function downloadCoverLetter() {
    const text = document.getElementById('coverLetterText').value;
    const element = document.createElement('a');
    element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(text));
    element.setAttribute('download', 'CoverLetter.txt');
    element.style.display = 'none';
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
}

// Extract Keywords
function extractKeywords() {
    const jobDesc = document.getElementById('jobDescKeywords').value;

    if (!jobDesc) {
        alert('Please provide job description');
        return;
    }

    // Simple keyword extraction
    const words = jobDesc.toLowerCase().split(/\s+/);
    const keywords = [...new Set(words.filter(w => w.length > 4))].slice(0, 15);

    const keywordsList = document.getElementById('keywordsList');
    keywordsList.innerHTML = keywords.map(k =>
        `<span class="keyword-tag">${k}</span>`
    ).join('');

    document.getElementById('keywordResults').classList.remove('hidden');
}

// Optimize LinkedIn
function optimizeLinkedin() {
    const headline = document.getElementById('linkedinHeadline').value;
    const summary = document.getElementById('linkedinSummary').value;

    if (!headline || !summary) {
        alert('Please provide headline and summary');
        return;
    }

    // Simple optimization suggestions
    const optimizedHeadline = `${headline} | AI-Driven Professional | Open to Opportunities`;
    const optimizedSummary = `Innovative professional with expertise in ${headline.split(' ').slice(-2).join(' ')}. 
Passionate about delivering results and driving impact. 
Skilled in problem-solving, team collaboration, and continuous learning.`;

    document.getElementById('optimizedHeadline').textContent = optimizedHeadline;
    document.getElementById('optimizedSummary').textContent = optimizedSummary;
    document.getElementById('linkedinResult').classList.remove('hidden');
}

// Utilities
function showLoading(show) {
    let loader = document.getElementById('loadingOverlay');
    if (show && !loader) {
        loader = document.createElement('div');
        loader.id = 'loadingOverlay';
        loader.style.cssText = `
            position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.5); display: flex;
            align-items: center; justify-content: center; z-index: 9999;
        `;
        loader.innerHTML = `
            <div style="background: white; padding: 30px; border-radius: 8px; text-align: center;">
                <div style="font-size: 40px; margin-bottom: 15px;">⏳</div>
                <p style="font-size: 16px; font-weight: 600;">Processing...</p>
            </div>
        `;
        document.body.appendChild(loader);
    } else if (!show && loader) {
        loader.remove();
    }
}

function showSuccess(msg) {
    const notif = document.createElement('div');
    notif.style.cssText = `
        position: fixed; top: 20px; right: 20px;
        background: #32c988; color: white; padding: 16px 20px;
        border-radius: 4px; z-index: 10000;
    `;
    notif.textContent = msg;
    document.body.appendChild(notif);
    setTimeout(() => notif.remove(), 3000);
}

// Login
async function handleLogin() {
    const name = document.getElementById('loginName').value;
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;

    if (!email) {
        alert('Please enter email');
        return;
    }

    showLoading(true);

    // Add user to Supabase
    if (name && email) {
        try {
            const response = await fetch("/add-user", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ name, email })
            });
            const data = await response.json();
            console.log('User add response:', data);

            if (!response.ok || data.error) {
                alert('Database Error: ' + (data.error || 'Check server logs'));
            } else {
                showSuccess('User recorded in database!');
            }
        } catch (err) {
            console.error('Supabase fetch error:', err);
            alert('Failed to connect to database endpoint.');
        }
    }

    // Simulate login buffer
    setTimeout(() => {
        showLoading(false);
        document.getElementById('login-container').classList.add('hidden');
        document.getElementById('app-container').classList.remove('hidden');
        document.getElementById('mainChatWidget').classList.remove('hidden');
        fetchUsers();
    }, 1000);
}

async function fetchUsers() {
    const container = document.getElementById('userListContainer');
    if (!container) return;

    try {
        const response = await fetch('/get-users');
        const data = await response.json();

        if (data.success && data.users) {
            if (data.users.length === 0) {
                container.innerHTML = '<p style="color: #888;">No users found in database.</p>';
            } else {
                container.innerHTML = data.users.map(user => `
                    <div style="background: #f8f9fa; padding: 8px; border-radius: 4px; margin-bottom: 5px; border-left: 3px solid #32c988;">
                        <strong style="color: #333;">${user.name || 'Anonymous'}</strong><br>
                        <small style="color: #666;">${user.email}</small>
                    </div>
                `).join('');
            }
        } else {
            container.innerHTML = '<p style="color: #ff5e5e;">Error loading users.</p>';
        }
    } catch (e) {
        console.error(e);
        container.innerHTML = '<p style="color: #ff5e5e;">Connection error.</p>';
    }
}

// Chatbot
function toggleChat() {
    const chatWindow = document.getElementById('chatWidget');
    chatWindow.classList.toggle('hidden');
}

function handleChatInput(event) {
    if (event.key === 'Enter') {
        sendChatMessage();
    }
}

async function sendChatMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();

    if (!message) return;

    // Add user message
    addMessage(message, 'user');
    input.value = '';

    // Call API
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message })
        });

        const data = await response.json();
        if (data.success) {
            addMessage(data.response, 'bot');
        } else {
            addMessage('Sorry, I encountered an error.', 'bot');
        }
    } catch (e) {
        console.error(e);
        addMessage('Sorry, I cannot connect right now.', 'bot');
    }
}

function addMessage(text, sender) {
    const chatMessages = document.getElementById('chatMessages');
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender}`;
    msgDiv.innerHTML = `<p>${text}</p>`;
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Settings
function saveSettings() {
    showLoading(true);
    setTimeout(() => {
        showLoading(false);
        showSuccess('Settings saved successfully!');
    }, 800);
}

// Initialize
document.addEventListener('DOMContentLoaded', function () {
    addBulletField();
    addBulletField();
    addBulletField();
});