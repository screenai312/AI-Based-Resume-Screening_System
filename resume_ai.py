import re

from sqlalchemy import text


COMMON_SKILLS = [
    "python", "java", "javascript", "html", "css", "bootstrap", "flask",
    "django", "react", "node", "node.js", "express", "sql", "mysql",
    "postgresql", "mongodb", "sqlite", "api", "rest api", "git", "github",
    "docker", "aws", "machine learning", "deep learning", "data science",
    "data analysis", "pandas", "numpy", "scikit-learn", "tensorflow",
    "power bi", "tableau", "excel", "c", "c++", "php", "laravel",
    "problem solving", "communication", "teamwork", "leadership",
    "oops", "object oriented programming", "dbms", "operating system",
    "computer networks", "nlp", "artificial intelligence", "prompt engineering"
]


SKILL_GROUPS = {
    "machine learning": ["ml", "machine learning", "supervised learning", "unsupervised learning"],
    "deep learning": ["deep learning", "neural networks", "cnn", "rnn"],
    "nlp": ["nlp", "natural language processing"],
    "python": ["python"],
    "data analysis": ["data analysis", "eda", "feature engineering"],
}


EDUCATION_KEYWORDS = [
    "b.tech", "btech", "b.e", "be", "bsc", "msc", "m.tech", "mtech",
    "diploma", "engineering", "computer science", "information technology",
    "bca", "mca", "master", "bachelor"
]


EXPERIENCE_KEYWORDS = [
    "experience", "intern", "internship", "worked", "project", "projects",
    "developer", "engineer", "analyst", "freelance", "job", "employment"
]


POSITIVE_RESUME_SECTIONS = [
    "education", "skills", "experience", "projects", "certifications",
    "summary", "objective", "achievements"
]


def clean_text(text):
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def is_skill_match(skill, resume_text):
    skill = skill.lower().strip()
    text = clean_text(resume_text)

    # direct phrase match
    if skill in text:
        return True

    # group-based match
    for _, variants in SKILL_GROUPS.items():
        if skill in variants:
            for var in variants:
                if var in text:
                    return True

    # partial multi-word support
    words = [w for w in skill.split() if len(w) > 2]
    if words and all(word in text for word in words):
        return True

    return False


def extract_job_requirements(job_description):
    job_text = clean_text(job_description)

    # 1. skills explicitly written by recruiter in job description
    explicit_job_skills = extract_explicit_job_skills(job_description)

    # 2. known skills from master list
    known_job_skills = extract_skills_from_text(job_text, COMMON_SKILLS)

    # 3. merge both
    merged_job_skills = []
    seen = set()

    for skill in explicit_job_skills + known_job_skills:
        skill = skill.strip().lower()
        if skill and skill not in seen:
            merged_job_skills.append(skill)
            seen.add(skill)

    # 4. keywords fallback
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9+#.\-]{2,}", job_text)

    stopwords = {
        "the", "and", "for", "with", "that", "this", "have", "has", "are",
        "you", "your", "will", "all", "our", "from", "into", "using", "use",
        "job", "role", "candidate", "should", "must", "good", "strong",
        "ability", "knowledge", "required", "preferred", "responsible",
        "skills", "requirements", "technical", "experience"
    }

    extra_keywords = []
    for w in words:
        word = w.lower()
        if word not in stopwords and len(word) > 2:
            extra_keywords.append(word)

    job_keywords = []
    seen_kw = set()

    for item in merged_job_skills + extra_keywords[:25]:
        if item not in seen_kw:
            job_keywords.append(item)
            seen_kw.add(item)

    return merged_job_skills, job_keywords


def extract_skills_from_text(text, skill_list=None):
    text = clean_text(text)
    skill_list = skill_list or COMMON_SKILLS

    found_skills = []

    for skill in skill_list:
        skill_lower = skill.lower()

        # exact phrase match
        if skill_lower in text:
            found_skills.append(skill)
            continue

        # word boundary match for safer detection
        pattern = r"\b" + re.escape(skill_lower) + r"\b"
        if re.search(pattern, text):
            found_skills.append(skill)

    # remove duplicates while preserving order
    unique_skills = []
    seen = set()
    for skill in found_skills:
        key = skill.lower()
        if key not in seen:
            unique_skills.append(skill)
            seen.add(key)

    return unique_skills


def extract_keywords_from_job_description(job_description):
    job_description = clean_text(job_description)

    matched_common_skills = extract_skills_from_text(job_description, COMMON_SKILLS)

    extra_keywords = []
    words = re.findall(r"[a-zA-Z][a-zA-Z+#.]{1,}", job_description)

    stopwords = {
        "the", "and", "for", "with", "that", "this", "have", "has", "are",
        "you", "your", "will", "all", "our", "from", "into", "using", "use",
        "job", "role", "candidate", "should", "must", "good", "strong",
        "ability", "knowledge", "required", "preferred", "responsible"
    }

    for word in words:
        word = word.lower()
        if len(word) > 2 and word not in stopwords:
            extra_keywords.append(word)

    final_keywords = sorted(list(set(matched_common_skills + extra_keywords[:25])))
    return final_keywords


def calculate_keyword_match_score(resume_text, job_description):
    resume_words = set(clean_text(resume_text).split())
    job_words = set(clean_text(job_description).split())

    if not job_words:
        return 0

    matched_words = resume_words.intersection(job_words)
    raw_score = len(matched_words) / len(job_words)
    score = raw_score * 100

    if score > 100:
        score = 100

    return round(score, 2)


def calculate_skill_match(resume_text, job_description):
    resume_skills = extract_skills_from_text(resume_text, COMMON_SKILLS)
    job_skills = extract_skills_from_text(job_description, COMMON_SKILLS)

    if not job_skills:
        return 50.0, [], [], resume_skills, job_skills

    matched_skills = [skill for skill in job_skills if skill in resume_skills]
    missing_skills = [skill for skill in job_skills if skill not in resume_skills]

    score = (len(matched_skills) / len(job_skills)) * 100
    return round(score, 2), matched_skills, missing_skills, resume_skills, job_skills

def extract_years_of_experience(text):
    text = clean_text(text)

    year_patterns = re.findall(r"(\d+)\+?\s*(year|years)", text)
    if year_patterns:
        years = max(int(match[0]) for match in year_patterns)
        return years

    return 0


def build_experience_sentence(resume_text):
    text = clean_text(resume_text)
    years = extract_years_of_experience(text)

    if years >= 1:
        return f"Candidate appears to have around {years} year{'s' if years != 1 else ''} of relevant experience mentioned in the resume."

    if "internship" in text or "intern" in text:
        return "Candidate shows internship-level practical exposure in relevant areas."

    if "project" in text or "projects" in text:
        return "Candidate shows hands-on exposure through academic or personal projects."

    return "No strong direct experience evidence was clearly detected in the resume."


def build_skill_sentence(matched_skills, missing_skills):
    parts = []

    if matched_skills:
        parts.append(
            f"Candidate demonstrates knowledge of {', '.join(matched_skills[:8])}."
        )

    if missing_skills:
        parts.append(
            f"Important gaps were identified in {', '.join(missing_skills[:6])}."
        )
    else:
        parts.append("No major skill gaps were detected against the current job description.")

    return " ".join(parts)


def build_education_sentence(resume_text):
    text = clean_text(resume_text)

    education_terms = [
        "b.tech", "btech", "b.e", "be", "diploma", "engineering",
        "computer science", "information technology", "bca", "mca"
    ]

    found = [term for term in education_terms if term in text]

    if found:
        cleaned = []
        for item in found:
            if item not in cleaned:
                cleaned.append(item)
        return f"Resume reflects relevant educational background such as {', '.join(cleaned[:4])}."

    return "Relevant education background is not strongly detailed in the resume."


def build_quality_sentence(quality_score, resume_text):
    word_count = len(clean_text(resume_text).split())

    if quality_score >= 75:
        return "Resume is well structured and contains sufficient detail for technical evaluation."

    if quality_score >= 50:
        return "Resume has moderate structure, but some sections could be explained in more depth."

    if word_count < 120:
        return "Resume is too short, which limits deeper candidate evaluation."

    return "Resume quality is below ideal because structure or detail level appears weak."


def build_final_summary(job_title, matched_skills, missing_skills, experience_line, education_line, quality_line, final_score):
    summary_parts = []

    summary_parts.append(f"This candidate was evaluated for the role of {job_title}.")

    if matched_skills:
        summary_parts.append(
            f"The profile shows relevant alignment through skills such as {', '.join(matched_skills[:6])}."
        )

    summary_parts.append(experience_line)
    summary_parts.append(education_line)
    summary_parts.append(quality_line)

    if missing_skills:
        summary_parts.append(
            f"The main concerns are missing competencies in {', '.join(missing_skills[:5])}."
        )

    if final_score >= 80:
        summary_parts.append("Overall, this profile appears strongly suitable for shortlist consideration.")
    elif final_score >= 65:
        summary_parts.append("Overall, this profile is a good fit but still has some noticeable gaps.")
    elif final_score >= 50:
        summary_parts.append("Overall, this profile needs manual review before moving forward.")
    else:
        summary_parts.append("Overall, this profile appears weak for the current role requirements.")

    return " ".join(summary_parts)

def calculate_experience_score(resume_text):
    text = clean_text(resume_text)

    score = 0

    year_matches = re.findall(r"(\d+)\+?\s*(year|years)", text)
    if year_matches:
        max_years = max(int(match[0]) for match in year_matches)
        score += min(max_years * 12, 60)

    keyword_hits = sum(1 for word in EXPERIENCE_KEYWORDS if word in text)
    score += min(keyword_hits * 8, 40)

    return min(round(score, 2), 100)


def calculate_education_score(resume_text):
    text = clean_text(resume_text)

    found = [kw for kw in EDUCATION_KEYWORDS if kw in text]

    if not found:
        return 30.0

    score = 40 + min(len(found) * 10, 60)
    return min(round(score, 2), 100)


def calculate_resume_quality_score(resume_text):
    text = clean_text(resume_text)

    score = 0

    word_count = len(text.split())

    if word_count >= 150:
        score += 20
    if word_count >= 300:
        score += 20
    if word_count >= 500:
        score += 10

    section_hits = sum(1 for section in POSITIVE_RESUME_SECTIONS if section in text)
    score += min(section_hits * 10, 50)

    email_found = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    phone_found = re.search(r"\b\d{10}\b", text)

    if email_found:
        score += 10
    if phone_found:
        score += 10

    return min(round(score, 2), 100)


def generate_strengths(matched_skills, experience_score, education_score, quality_score):
    strengths = []

    if matched_skills:
        strengths.append(f"Matched key skills: {', '.join(matched_skills[:6])}")

    if experience_score >= 60:
        strengths.append("Resume shows good experience or project exposure")

    if education_score >= 60:
        strengths.append("Resume contains relevant education background")

    if quality_score >= 70:
        strengths.append("Resume structure looks complete and well-organized")

    if not strengths:
        strengths.append("Resume has some relevant information for initial screening")

    return strengths


def generate_weaknesses(missing_skills, experience_score, quality_score, resume_text):
    weaknesses = []

    if missing_skills:
        weaknesses.append(f"Missing important skills: {', '.join(missing_skills[:6])}")

    if experience_score < 40:
        weaknesses.append("Experience section appears weak or unclear")

    if quality_score < 60:
        weaknesses.append("Resume format/content looks incomplete or lacks detail")

    if len(clean_text(resume_text).split()) < 150:
        weaknesses.append("Resume content is too short for strong evaluation")

    if not weaknesses:
        weaknesses.append("No major weakness detected in basic screening")

    return weaknesses


def generate_recommendation(final_score):
    if final_score >= 80:
        return "Strong Shortlist"
    elif final_score >= 65:
        return "Shortlist"
    elif final_score >= 50:
        return "Hold"
    else:
        return "Reject"


def extract_explicit_job_skills(job_description):
    """
    Extract recruiter-written skills directly from the job description.
    Works best when JD contains lines like:
    - Skills: Python, Flask, SQL
    - Required skills: Excel, typing, communication
    - Technologies: React, Node.js, MongoDB
    """
    if not job_description:
        return []

    raw_text = job_description.replace("\r", "\n")
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]

    extracted = []

    skill_section_keywords = [
        "skills", "required skills", "technical skills",
        "technologies", "requirements", "must have", "preferred skills"
    ]

    for line in lines:
        lower_line = line.lower()

        if any(keyword in lower_line for keyword in skill_section_keywords):
            # take text after colon if present
            if ":" in line:
                _, skill_part = line.split(":", 1)
            else:
                skill_part = line

            # split by comma or pipe or slash
            parts = re.split(r"[,/|•]", skill_part)

            for part in parts:
                skill = part.strip().lower()
                skill = re.sub(r"\s+", " ", skill)

                # keep useful skills only
                if len(skill) >= 2 and len(skill) <= 40:
                    extracted.append(skill)

    # fallback: if recruiter wrote skills in one paragraph
    if not extracted:
        words = re.split(r"[,/\n|•]", job_description)
        for word in words:
            skill = word.strip().lower()
            skill = re.sub(r"\s+", " ", skill)

            if 2 <= len(skill) <= 40:
                # keep only more skill-like items
                if any(ch.isalpha() for ch in skill):
                    extracted.append(skill)

    # remove obvious non-skill phrases
    stop_phrases = {
        "job description", "responsibilities", "candidate", "role", "experience",
        "qualification", "qualifications", "company", "team", "developer needed",
        "looking for", "we are hiring", "must have experience"
    }

    cleaned = []
    seen = set()

    for skill in extracted:
        if skill in stop_phrases:
            continue
        if skill not in seen:
            cleaned.append(skill)
            seen.add(skill)

    return cleaned


def analyze_resume_against_job(resume_text, job_description):
    text = clean_text(resume_text)
    job_text = clean_text(job_description)

    # =========================
    # SKILL MATCHING
    # =========================
    resume_skills = extract_skills_from_text(text)

    job_skills, job_keywords = extract_job_requirements(job_description)

    # 🔥 Assign importance weight based on frequency in job description
    skill_importance = {}

    for skill in job_skills:
        count = job_text.count(skill.lower())
        skill_importance[skill] = 1 + count  # base weight + frequency

    matched_skills = [s for s in job_skills if is_skill_match(s, text)]
    missing_skills = [s for s in job_skills if not is_skill_match(s, text)]

# 🔥 NEW: keyword-level matching (important)
    resume_words = set(text.split())
    job_word_matches = [w for w in job_keywords if w in resume_words]

    keyword_score = (len(job_word_matches) / len(job_keywords)) * 100 if job_keywords else 50

# slight boost for strong keyword overlap
    if len(job_word_matches) > 5:
     keyword_score += 10

    keyword_score = min(keyword_score, 100)

    skill_score = 0

    if job_skills:
     total_weight = sum(skill_importance.values())

    matched_weight = sum(
        skill_importance[s] for s in matched_skills if s in skill_importance
    )

    skill_score = (matched_weight / total_weight) * 100

    # =========================
    # EXPERIENCE DETECTION
    # =========================
    experience_score = 0
    years = re.findall(r"(\d+)\+?\s*(year|years)", text)

    if years:
        max_year = max(int(y[0]) for y in years)
        experience_score = min(max_year * 12, 100)

    exp_keywords = ["internship", "project", "projects", "experience", "worked", "developer"]
    exp_hits = sum(1 for k in exp_keywords if k in text)
    experience_score += exp_hits * 5
    experience_score = min(experience_score, 100)

    # =========================
    # EDUCATION DETECTION
    # =========================
    edu_keywords = ["btech", "b.e", "diploma", "computer science", "information technology", "engineering", "bca", "mca"]
    edu_hits = [k for k in edu_keywords if k in text]

    education_score = 40 + len(edu_hits) * 10 if edu_hits else 30
    education_score = min(education_score, 100)

    # =========================
    # QUALITY CHECK
    # =========================
    word_count = len(text.split())

    quality_score = 0
    if word_count > 150:
        quality_score += 30
    if word_count > 300:
        quality_score += 30
    if word_count > 500:
        quality_score += 20

    if re.search(r"\S+@\S+", text):
        quality_score += 10
    if re.search(r"\b\d{10}\b", text):
        quality_score += 10

    quality_score = min(quality_score, 100)

    # =========================
    # KEYWORD MATCH
    # =========================
    

    # =========================
    # FINAL SCORE
    # =========================
    final_score = (
        0.50 * skill_score +        # 🔥 MAIN FACTOR
        0.25 * keyword_score +
        0.15 * experience_score +
        0.05 * education_score +
        0.05 * quality_score
    )
    final_score = round(final_score, 2)

    # =========================
    # EXPLANATION LINES
    # =========================
    experience_line = build_experience_sentence(resume_text)
    education_line = build_education_sentence(resume_text)
    quality_line = build_quality_sentence(quality_score, resume_text)
    skill_line = build_skill_sentence(matched_skills, missing_skills)

    summary = build_final_summary(
        "this role",
        matched_skills,
        missing_skills,
        experience_line,
        education_line,
        quality_line,
        final_score
    )

    # =========================
    # STRENGTHS
    # =========================
    strengths = []

    if matched_skills:
        strengths.append(f"Candidate matches important skills such as {', '.join(matched_skills[:8])}")

# 🔥 ADD THIS HERE
    if job_skills:
        strengths.append(f"Candidate matches {len(matched_skills)} out of {len(job_skills)} required job skills")

    strengths.append(experience_line)
    strengths.append(education_line)

    if quality_score >= 60:
        strengths.append("Resume presentation is clear enough for recruiter review")

    # =========================
    # WEAKNESSES
    # =========================
    weaknesses = []

    if missing_skills:
        weaknesses.append(f"Missing or weak skills include {', '.join(missing_skills[:8])}")

# 🔥 ADD THIS HERE
    if job_skills and missing_skills:
        weaknesses.append(f"{len(missing_skills)} critical job-required skills are missing")

    if experience_score < 40:
        weaknesses.append("Relevant practical experience appears limited or not clearly described")

    if quality_score < 50:
        weaknesses.append("Resume detail level is low, making technical evaluation harder")

    if word_count < 120:
        weaknesses.append("Resume is too short for strong evaluation")

    if not weaknesses:
        weaknesses.append("No major weaknesses detected in initial screening")

    # =========================
    # RECOMMENDATION
    # =========================
    if final_score >= 80:
        recommendation = "Strong Shortlist – Highly suitable candidate"
    elif final_score >= 65:
        recommendation = "Shortlist – Good fit with minor gaps"
    elif final_score >= 50:
        recommendation = "Hold – Needs further evaluation"
    else:
        recommendation = "Reject – Not aligned with job requirements"

    return {
        "final_score": final_score,
        "keyword_score": round(keyword_score, 2),
        "skill_score": round(skill_score, 2),
        "experience_score": round(experience_score, 2),
        "education_score": round(education_score, 2),
        "quality_score": round(quality_score, 2),
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommendation": recommendation,
        "summary": summary,
        "skill_line": skill_line,
        "experience_line": experience_line,
        "education_line": education_line,
        "quality_line": quality_line
    }