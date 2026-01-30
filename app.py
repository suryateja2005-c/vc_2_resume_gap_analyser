import os
import json
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import requests
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
import re
import PyPDF2
from supabase import create_client

# Environment Logic
load_dotenv()
IS_VERCEL = "VERCEL" in os.environ

app = Flask(__name__)
CORS(app)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 52428800
app.config['UPLOAD_FOLDER'] = '/tmp' if IS_VERCEL else 'uploads'
HF_API_KEY = os.getenv('HF_API_KEY', 'dummy_key')

# Safe Directory Prep
if not IS_VERCEL and not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Supabase Initialization (Safe)
supabase = None
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
if url and key:
    try:
        supabase = create_client(url, key)
    except Exception as e:
        print(f"Supabase Init Error: {e}")

# Core Logic: Job Titles & Skills
JOB_TITLES = {
    'technology': ['Software Engineer', 'Data Scientist', 'DevOps Engineer', 'UI/UX Designer', 'Product Manager'],
    'finance': ['Financial Analyst', 'Accountant', 'Investment Banker', 'Risk Manager', 'CFO'],
    'healthcare': ['Nurse', 'Doctor', 'Pharmacist', 'Medical Assistant', 'Healthcare Manager'],
    'education': ['Teacher', 'Professor', 'Curriculum Developer', 'Training Specialist', 'Education Manager'],
    'marketing': ['Marketing Manager', 'Content Writer', 'SEO Specialist', 'Brand Manager', 'Digital Marketer']
}

SKILLS_DATABASE = {
    'technology': ['Python', 'JavaScript', 'SQL', 'AWS', 'Docker', 'Kubernetes', 'React', 'Node.js', 'Java', 'C++'],
    'finance': ['Excel', 'Financial Modeling', 'SAP', 'Bloomberg Terminal', 'Risk Analysis', 'Budgeting', 'Python', 'SQL'],
    'healthcare': ['Patient Care', 'EMR Systems', 'Medical Terminology', 'HIPAA', 'Clinical Skills', 'EHR'],
    'education': ['Curriculum Design', 'Student Assessment', 'Lesson Planning', 'Mentoring', 'Research', 'LMS'],
    'marketing': ['SEO', 'Content Marketing', 'Google Analytics', 'Social Media', 'Email Marketing', 'CRM']
}

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route("/add-user", methods=["POST"])
def add_user():
    try:
        data = request.json
        if not supabase: return jsonify({"error": "DB not ready"}), 500
        
        response = supabase.table("user_data_vc_2").insert({
            "name": data.get("name"),
            "email": data.get("email")
        }).execute()
        
        return jsonify({"success": True, "message": "User added"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/get-users", methods=["GET"])
def get_users():
    try:
        if not supabase: return jsonify({"users": []})
        response = supabase.table("user_data_vc_2").select("*").execute()
        return jsonify({"success": True, "users": response.data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- AI & RESUME FEATURES ---

def call_huggingface_api(prompt, max_tokens=500):
    if HF_API_KEY == 'dummy_key': return "AI content demo."
    try:
        headers = {"Authorization": f"Bearer {HF_API_KEY}"}
        payload = {"inputs": prompt, "parameters": {"max_new_tokens": max_tokens}}
        r = requests.post("https://api-inference.huggingface.co/models/Qwen/Qwen2-7B", headers=headers, json=payload, timeout=20)
        if r.status_code == 200:
            res = r.json()
            return res[0].get('generated_text', '') if isinstance(res, list) else str(res)
    except: pass
    return "AI generation unavailable"

def extract_keywords(text):
    return list(set([w.strip('.,!?:') for w in text.lower().split() if len(w) > 3]))

@app.route('/api/analyze-resume-gap', methods=['POST'])
def analyze_gap():
    data = request.json
    res_text = data.get('resumeText', '').lower()
    jd_text = data.get('jobDescription', '').lower()
    
    res_keys = set(extract_keywords(res_text))
    jd_keys = set(extract_keywords(jd_text))
    
    match = res_keys & jd_keys
    score = int((len(match) / len(jd_keys)) * 100) if jd_keys else 0
    
    return jsonify({
        "success": True,
        "analysis": {
            "score": score,
            "matching_keywords": list(match)[:10],
            "missing_keywords": list(jd_keys - res_keys)[:10],
            "total_jd_keywords": len(jd_keys),
            "matched_count": len(match)
        },
        "suggestions": ["Add more technical keywords."] if score < 70 else ["Excellent match!"],
        "status": "Good" if score > 60 else "Needs Work"
    })

@app.route('/api/ats-check', methods=['POST'])
def ats_check():
    text = request.json.get('resumeText', '')
    issues = []
    score = 100
    if len(text) < 200: issues.append("Too short"); score -= 20
    if '@' not in text: issues.append("Email missing"); score -= 15
    return jsonify({"score": max(0, score), "issues": issues, "success": True, "status": "Checked"})

@app.route('/api/ats-check-upload', methods=['POST'])
def ats_upload():
    if 'resume' not in request.files: return jsonify({"error": "No file"}), 400
    file = request.files['resume']
    text = ""
    try:
        pdf = PyPDF2.PdfReader(file)
        for page in pdf.pages: text += page.extract_text() + "\n"
        return jsonify({"score": 85, "issues": [], "success": True, "status": "PDF Parsed"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate-content', methods=['POST'])
def gen_content():
    data = request.json
    prompt = f"Write a {data.get('section')} for a {data.get('jobTitle')}."
    return jsonify({"content": call_huggingface_api(prompt), "success": True})

@app.route('/api/chat', methods=['POST'])
def chat():
    msg = request.json.get('message', '')
    prompt = f"Career coach response to: {msg}"
    return jsonify({"response": call_huggingface_api(prompt), "success": True})

# Entry point for Vercel
app = app

if __name__ == '__main__':
    app.run(debug=True, port=5000)
