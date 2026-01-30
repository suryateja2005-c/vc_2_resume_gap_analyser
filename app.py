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

load_dotenv()

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

app.config['MAX_CONTENT_LENGTH'] = 52428800
app.config['UPLOAD_FOLDER'] = 'uploads'
HF_API_KEY = os.getenv('HF_API_KEY', 'dummy_key')

# Initialize Supabase
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key) if url and key else None

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Job titles and skills database
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

def call_huggingface_api(prompt, max_tokens=500):
    if HF_API_KEY == 'dummy_key':
        return "Generated professional content based on your input."
    try:
        headers = {"Authorization": f"Bearer {HF_API_KEY}"}
        payload = {"inputs": prompt, "parameters": {"max_new_tokens": max_tokens}}
        response = requests.post(
            "https://api-inference.huggingface.co/models/Qwen/Qwen2-7B",
            headers=headers, json=payload, timeout=30
        )
        if response.status_code == 200:
            result = response.json()
            return result[0].get('generated_text', '') if isinstance(result, list) else str(result)
        return "Content generation unavailable"
    except:
        return "Content generation unavailable"

def extract_keywords(text):
    """Extract important keywords from text"""
    words = text.lower().split()
    keywords = [w.strip('.,!?;:') for w in words if len(w) > 3]
    return list(set(keywords))

def analyze_resume_gap(resume_text, job_description):
    """Analyze gap between resume and job description"""
    resume_keywords = set(extract_keywords(resume_text))
    jd_keywords = set(extract_keywords(job_description))
    
    matching = resume_keywords & jd_keywords
    missing = jd_keywords - resume_keywords
    extra = resume_keywords - jd_keywords
    
    if len(jd_keywords) > 0:
        compatibility_score = int((len(matching) / len(jd_keywords)) * 100)
    else:
        compatibility_score = 0
    
    return {
        'score': min(100, max(0, compatibility_score)),
        'matching_keywords': list(matching)[:10],
        'missing_keywords': list(missing)[:10],
        'total_jd_keywords': len(jd_keywords),
        'matched_count': len(matching),
        'match_percentage': compatibility_score
    }

def generate_resume_pdf(profile_data):
    try:
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
        story = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=24, textColor=colors.HexColor('#1a1a2e'), alignment=TA_CENTER, fontName='Helvetica-Bold')
        heading_style = ParagraphStyle('Heading', parent=styles['Heading2'], fontSize=12, textColor=colors.HexColor('#16213e'), fontName='Helvetica-Bold')
        
        name = profile_data.get('fullName', 'Your Name')
        email = profile_data.get('email', 'email@example.com')
        phone = profile_data.get('phone', '(123) 456-7890')
        location = profile_data.get('location', 'City, State')
        
        story.append(Paragraph(name, title_style))
        story.append(Paragraph(f"{email} | {phone} | {location}", styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        if profile_data.get('summary'):
            story.append(Paragraph("PROFESSIONAL SUMMARY", heading_style))
            story.append(Paragraph(profile_data['summary'], styles['BodyText']))
            story.append(Spacer(1, 0.1*inch))
        
        if profile_data.get('skills'):
            story.append(Paragraph("SKILLS", heading_style))
            skills = ', '.join(profile_data['skills']) if isinstance(profile_data['skills'], list) else profile_data['skills']
            story.append(Paragraph(skills, styles['BodyText']))
            story.append(Spacer(1, 0.1*inch))
        
        if profile_data.get('experiences'):
            story.append(Paragraph("EXPERIENCE", heading_style))
            for exp in profile_data['experiences']:
                story.append(Paragraph(f"<b>{exp.get('jobTitle', '')}</b> | {exp.get('company', '')}", styles['BodyText']))
                if exp.get('description'):
                    story.append(Paragraph(f"• {exp['description']}", styles['BodyText']))
                story.append(Spacer(1, 0.05*inch))
        
        if profile_data.get('educations'):
            story.append(Paragraph("EDUCATION", heading_style))
            for edu in profile_data['educations']:
                story.append(Paragraph(f"<b>{edu.get('degree', '')}</b> | {edu.get('institution', '')}", styles['BodyText']))
                story.append(Spacer(1, 0.05*inch))
        
        doc.build(story)
        pdf_buffer.seek(0)
        return pdf_buffer
    except Exception as e:
        raise Exception(f"PDF Error: {str(e)}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route("/add-user", methods=["POST"])
def add_user():
    try:
        data = request.json
        name = data.get("name")
        email = data.get("email")
        
        if not supabase:
             return jsonify({"error": "Supabase not configured. Check your .env file."}), 500

        print(f"DEBUG: Attempting to insert into user_data_vc_2: name={name}, email={email}")
        
        # Insert user data
        response = supabase.table("user_data_vc_2").insert({
            "name": name,
            "email": email
        }).execute()
        
        print(f"DEBUG: Supabase Response Object: {response}")

        # Check for errors in the response (older SDK versions vs newer)
        # In newer versions, .execute() returns an object with .data and .error
        # But sometimes it's just the data if successful.
        
        return jsonify({
            "success": True, 
            "message": "User added successfully", 
            "data": response.data if hasattr(response, 'data') else str(response)
        })
    except Exception as e:
        print(f"DEBUG: Exception during insert: {str(e)}")
        return jsonify({"error": str(e), "success": False}), 500

@app.route("/get-users", methods=["GET"])
def get_users():
    try:
        if not supabase:
             return jsonify({"error": "Supabase not configured"}), 500
             
        print("DEBUG: Fetching users from user_data_vc_2")
        response = supabase.table("user_data_vc_2").select("*").execute()
        print(f"DEBUG: Fetched users count: {len(response.data) if hasattr(response, 'data') else 'Unknown'}")
        
        users = response.data if hasattr(response, 'data') else []
        return jsonify({"success": True, "users": users})
    except Exception as e:
        print(f"DEBUG: Exception during fetch: {str(e)}")
        return jsonify({"error": str(e), "success": False}), 500

@app.route('/api/industries')
def get_industries():
    return jsonify({'industries': list(JOB_TITLES.keys())})

@app.route('/api/job-titles/<industry>')
def get_job_titles(industry):
    return jsonify({'job_titles': JOB_TITLES.get(industry, [])})

@app.route('/api/skills/<industry>')
def get_skills(industry):
    return jsonify({'skills': SKILLS_DATABASE.get(industry, [])})

@app.route('/api/analyze-resume-gap', methods=['POST'])
def analyze_resume_gap_api():
    """Analyze gap between resume and job description"""
    try:
        data = request.get_json()
        resume_text = data.get('resumeText', '').lower()
        job_description = data.get('jobDescription', '').lower()
        
        if not resume_text or not job_description:
            return jsonify({'error': 'Please provide both resume and job description'}), 400
        
        analysis = analyze_resume_gap(resume_text, job_description)
        
        # Generate improvement suggestions
        suggestions = []
        if analysis['score'] < 50:
            suggestions.append("Your resume is missing key keywords. Consider adding technical skills mentioned in the job description.")
        if analysis['score'] < 75:
            suggestions.append("Add more specific achievements and metrics to improve ATS compatibility.")
        if analysis['score'] < 90:
            suggestions.append("Try incorporating more industry-specific terminology from the job posting.")
        
        if not suggestions:
            suggestions.append("Great match! Your resume aligns well with this job description.")
        
        return jsonify({
            'success': True,
            'analysis': analysis,
            'suggestions': suggestions,
            'status': 'Excellent Match' if analysis['score'] >= 80 else 'Good Match' if analysis['score'] >= 60 else 'Needs Improvement'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-content', methods=['POST'])
def generate_content():
    try:
        data = request.get_json()
        job_title = data.get('jobTitle', '')
        section = data.get('section', '')
        
        if section == 'summary':
            prompt = f"Write a professional 2-3 sentence resume summary for a {job_title}."
        else:
            prompt = f"Write a professional work experience bullet for a {job_title}."
        
        content = call_huggingface_api(prompt)
        return jsonify({'content': content, 'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-resume', methods=['POST'])
def generate_resume():
    try:
        data = request.get_json()
        if not data.get('fullName'):
            return jsonify({'error': 'Missing required fields'}), 400
        
        pdf_buffer = generate_resume_pdf(data)
        return send_file(pdf_buffer, mimetype='application/pdf', as_attachment=True, download_name=f"{data.get('fullName', 'Resume').replace(' ', '_')}.pdf")
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-cover-letter', methods=['POST'])
def generate_cover_letter():
    try:
        data = request.get_json()
        job_title = data.get('jobTitle', '')
        company = data.get('company', '')
        
        prompt = f"Write a professional cover letter for a {job_title} position at {company}."
        content = call_huggingface_api(prompt, 1000)
        return jsonify({'cover_letter': content, 'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat_bot():
    try:
        data = request.get_json()
        message = data.get('message', '')
        
        if not message:
            return jsonify({'error': 'No message provided'}), 400
            
        prompt = f"You are a helpful AI career coach and resume assistant. User asks: {message}. Provide a helpful, professional, and concise response."
        response = call_huggingface_api(prompt)
        
        return jsonify({'response': response, 'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def evaluate_resume_text(resume_text):
    """Helper to evaluate resume text and return score + issues"""
    issues = []
    score = 100
    
    # Check for common ATS issues
    if len(resume_text) < 200:
        issues.append("Resume is too short. Aim for at least 200 words to ensure enough content for keyword matching.")
        score -= 20
    
    if '@' not in resume_text and 'email' not in resume_text.lower():
        issues.append("Email address missing. Ensure your contact info is clearly visible.")
        score -= 15
    
    if 'phone' not in resume_text.lower() and not any(c.isdigit() for c in resume_text):
        issues.append("Phone number missing. Recruiters need a way to contact you.")
        score -= 10
        
    # Section checks
    sections = ['experience', 'education', 'skills', 'summary', 'projects']
    missing_sections = [s for s in sections if s not in resume_text.lower()]
    
    if missing_sections:
        for section in missing_sections:
            issues.append(f"Missing '{section.capitalize()}' section. Standard sections help ATS parse your data.")
            score -= 5
    
    # Check for symbols that may not parse well
    problematic_chars = ['©', '®', '™', '†', '‡']
    if any(char in resume_text for char in problematic_chars):
        issues.append("Avoid special symbols (©, ®, etc.) as some older ATS systems cannot parse them.")
        score -= 5
    
    # Check for bullet points usage
    if '•' not in resume_text and '-' not in resume_text and '*' not in resume_text:
        issues.append("Use standard bullet points (•, -, *) to organize your achievements for better readability.")
        score -= 5
    
    score = max(0, min(100, score))
    
    return {
        'score': score,
        'issues_found': len(issues),
        'issues': issues,
        'success': True,
        'status': 'Excellent' if score >= 90 else 'Good' if score >= 70 else 'Needs Improvement'
    }

@app.route('/api/ats-check', methods=['POST'])
def ats_check():
    """Check ATS compatibility of resume text"""
    try:
        data = request.get_json()
        resume_text = data.get('resumeText', '')
        
        if not resume_text:
            return jsonify({'error': 'No resume text provided'}), 400
        
        result = evaluate_resume_text(resume_text)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ats-check-upload', methods=['POST'])
def ats_check_upload():
    """Check ATS compatibility of uploaded resume PDF"""
    try:
        if 'resume' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['resume']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
            
        if file and file.filename.lower().endswith('.pdf'):
            try:
                pdf_reader = PyPDF2.PdfReader(file)
                resume_text = ""
                for page in pdf_reader.pages:
                    resume_text += page.extract_text() + "\n"
            except Exception as e:
                return jsonify({'error': f"Error reading PDF: {str(e)}"}), 400
        else:
             return jsonify({'error': 'Please upload a PDF file'}), 400
             
        result = evaluate_resume_text(resume_text)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/improve-bullets', methods=['POST'])
def improve_bullets():
    """Improve resume bullets for ATS"""
    try:
        data = request.get_json()
        bullets = data.get('bullets', [])
        job_description = data.get('jobDescription', '')
        
        if not bullets:
            return jsonify({'error': 'No bullets provided'}), 400
        
        improved = []
        for bullet in bullets:
            # Add action verbs if missing
            action_verbs = ['Implemented', 'Developed', 'Designed', 'Managed', 'Led', 'Achieved', 'Improved', 'Optimized']
            
            if not any(verb in bullet for verb in action_verbs):
                bullet = f"Developed {bullet}" if bullet else bullet
            
            # Add metrics if missing
            if not any(c.isdigit() for c in bullet):
                bullet = bullet + " (resulting in 20% efficiency increase)"
            
            improved.append(bullet)
        
        return jsonify({'improved_bullets': improved, 'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
