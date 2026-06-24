import os
from dotenv import load_dotenv
load_dotenv()
import csv
from flask import Response
import mysql.connector
from flask import Flask, render_template, request, redirect,session
import PyPDF2
from mongo_db import resume_collection
from ai_analyzer import analyze_resume
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Flask application create
app = Flask(__name__)
app.secret_key="resume_analyzer_secret"
# Skills database
SKILLS = [
    "python","java","c","c++","mysql","sql",
    "html","css","javascript","bootstrap",
    "react","angular","node.js",
    "flask","django","spring",
    "git","github",
    "mongodb","docker",
    "aws","azure","kubernetes"
]

# Home page route
@app.route('/')
def home():
    return render_template('index.html')
@app.route('/login')
def login():
    return render_template('login.html')
@app.route('/login_check', methods=['POST'])
def login_check():

    email = request.form['email']
    password = request.form['password']

    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password=os.getenv("MYSQL_PASSWORD"),
        database="resume_analyzer"
    )

    cursor = conn.cursor()

    query = """
    SELECT *
    FROM users
    WHERE email=%s AND password=%s
    """

    cursor.execute(query, (email, password))

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if user:

        session['user'] = email

        return redirect('/dashboard')

    return "Invalid Login"
@app.route('/logout')
def logout():

    session.pop('user', None)

    return redirect('/login')
# Resume analysis route
@app.route('/analyze', methods=['POST'])
def analyze():

    # Get uploaded PDF file
    resume = request.files['resume']

    # Get job description text
    job_desc = request.form['job_desc']

    # Read PDF file
    pdf_reader = PyPDF2.PdfReader(resume)

    # Store complete resume text
    text = ""

    # Extract text from all pages
    for page in pdf_reader.pages:

        extracted_text = page.extract_text()

        if extracted_text:
            text += extracted_text.lower()

    # Resume skills
    found_skills = []

    # Search skills in resume
    for skill in SKILLS:
        if skill in text:
            found_skills.append(skill)

    # Convert JD to lowercase
    job_desc = job_desc.lower()

    # Job description skills
    jd_skills = []

    # Search skills in JD
    for skill in SKILLS:
        if skill in job_desc:
            jd_skills.append(skill)

    # Store matched and missing skills
    matched = []
    missing = []

    # Compare JD skills with Resume skills
    for skill in jd_skills:

        if skill in found_skills:
            matched.append(skill)

        else:
            missing.append(skill)

    # Calculate match percentage
    # AI Matching using TF-IDF + Cosine Similarity

    documents = [text, job_desc]

    vectorizer = TfidfVectorizer()

    tfidf_matrix = vectorizer.fit_transform(documents)

    similarity = cosine_similarity(
        tfidf_matrix[0:1],
        tfidf_matrix[1:2]
    )

    percentage = round(
        similarity[0][0] * 100,
        2
    )
    ai_result = analyze_resume(
    text,
    job_desc,
    matched,
    missing
)
    print("Resume Skills:", found_skills)
    print("JD Skills:", jd_skills)
    print("Matched Skills:", matched)
    print("Missing Skills:", missing)


        # Database Connection
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password=os.getenv("MYSQL_PASSWORD"),
        database="resume_analyzer"
    )

    cursor = conn.cursor()

    query = """
    INSERT INTO analysis_history
    (resume_name, match_percentage, matched_skills, missing_skills)
    VALUES (%s, %s, %s, %s)
    """

    values = (
        resume.filename,
        percentage,
        ", ".join(matched),
        ", ".join(missing)
    )

    cursor.execute(query, values)

    conn.commit()

    cursor.close()
    conn.close()    
    resume_data = {

    "resume_name": resume.filename,

    "match_percentage": percentage,

    "matched_skills": matched,

    "missing_skills": missing,

    "resume_skills": found_skills

}

    #resume_collection.insert_one(resume_data)
    # Send data to result.html
    return render_template(
    "result.html",
    percentage=percentage,
    matched=matched,
    missing=missing,
    found_skills=found_skills,
    ai_result=ai_result
)
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password=os.getenv("MYSQL_PASSWORD"),
        database="resume_analyzer"
    )

    cursor = conn.cursor()

    # Total Analyses
    cursor.execute("SELECT COUNT(*) FROM analysis_history")
    total_resumes = cursor.fetchone()[0]

    # Average Score
    cursor.execute("SELECT AVG(match_percentage) FROM analysis_history")
    avg_score = cursor.fetchone()[0]

    cursor.execute("""
    SELECT match_percentage
    FROM analysis_history
    ORDER BY analysis_date DESC
    LIMIT 10
    """)

    chart_scores = cursor.fetchall()

    cursor.execute("""
    SELECT resume_name, match_percentage, analysis_date
    FROM analysis_history
    ORDER BY analysis_date DESC
    LIMIT 10
    """)

    recent_records = cursor.fetchall()

    cursor.close()
    conn.close()
    cursor.execute("""
    SELECT resume_name, match_percentage
    FROM analysis_history
    ORDER BY match_percentage DESC
    LIMIT 1
""")

    top_candidate = cursor.fetchone()
    return render_template(
        "dashboard.html",
        total_resumes=total_resumes,
        avg_score=round(avg_score or 0, 2),
        top_candidate=top_candidate,
        recent_records=recent_records,
        chart_scores=chart_scores
    )

@app.route('/export')
def export_csv():

    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password=os.getenv("MYSQL_PASSWORD"),
        database="resume_analyzer"
    )

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            resume_name,
            match_percentage,
            matched_skills,
            missing_skills,
            analysis_date
        FROM analysis_history
    """)

    data = cursor.fetchall()

    cursor.close()
    conn.close()

    output = []

    output.append([
        "Resume Name",
        "Match Percentage",
        "Matched Skills",
        "Missing Skills",
        "Date"
    ])

    for row in data:
        output.append(row)

    def generate():
        for row in output:
            yield ",".join(map(str, row)) + "\n"

    return Response(
        generate(),
        mimetype="text/csv",
        headers={
            "Content-Disposition":
            "attachment; filename=analysis_report.csv"
        }
    )    
@app.route('/history')
def history():

    search = request.args.get('search', '')

    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password=os.getenv("MYSQL_PASSWORD"),
        database="resume_analyzer"
    )

    cursor = conn.cursor()

    query = """
        SELECT id,
               resume_name,
               match_percentage,
               analysis_date
        FROM analysis_history
        WHERE resume_name LIKE %s
        ORDER BY analysis_date DESC
    """

    cursor.execute(query, ('%' + search + '%',))

    records = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "history.html",
        records=records
    )
@app.route('/ranking')
def ranking():

    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password=os.getenv("MYSQL_PASSWORD"),
        database="resume_analyzer"
    )

    cursor = conn.cursor()

    cursor.execute("""
        SELECT resume_name,
               match_percentage
        FROM analysis_history
        ORDER BY match_percentage DESC
    """)

    rankings = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "ranking.html",
        rankings=rankings
    )
@app.route('/delete/<int:id>')
def delete_analysis(id):

    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password=os.getenv("MYSQL_PASSWORD"),
        database="resume_analyzer"
    )

    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM analysis_history WHERE id=%s",
        (id,)
    )

    conn.commit()

    cursor.close()
    conn.close()

    return redirect('/history')
# Run application
if __name__ == "__main__":
    app.run(debug=True)    

