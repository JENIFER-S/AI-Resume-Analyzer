import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

genai.configure(
    api_key=os.getenv("GEMINI_API_KEY")
)

model = genai.GenerativeModel(
    "models/gemini-2.5-flash"
)

def analyze_resume(
    resume_text,
    job_description,
    matched,
    missing
):

    prompt = f"""
Resume Analysis

Matched Skills:
{matched}

Missing Skills:
{missing}

Based on these skills, provide:

1. Strengths
2. Recommendations
3. Interview Readiness
4. Learning Roadmap

Do not generate Matched Skills or Missing Skills again.

Only provide the above sections.
"""

    response = model.generate_content(prompt)

    return response.text