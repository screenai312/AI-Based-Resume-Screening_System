import re


COMMON_SKILLS = [
    "python","java","c","c++","html","css","javascript","bootstrap",
    "react","node","flask","django","sql","mysql","postgresql",
    "mongodb","machine learning","deep learning","data science",
    "pandas","numpy","tensorflow","scikit-learn",
    "api","rest api","git","github","docker",
    "excel","power bi","tableau",
    "problem solving","communication","teamwork"
]


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


def extract_skills_from_text(text, skill_list=None):
    text = clean_text(text)
    skill_list = skill_list or COMMON_SKILLS

    found_skills = []
    for skill in skill_list:
        pattern = r"\b" + re.escape(skill.lower()) + r"\b"
        if re.search(pattern, text):
            found_skills.append(skill)

    return sorted(list(set(found_skills)))


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


def analyze_resume_against_job(resume_text, job_description):

    text = clean_text(resume_text)
    job_text = clean_text(job_description)

    # =========================
    # SKILL MATCHING (STRONGER)
    # =========================
    resume_skills = extract_skills_from_text(text)
    job_skills = extract_skills_from_text(job_text)

    matched_skills = [s for s in job_skills if s in resume_skills]
    missing_skills = [s for s in job_skills if s not in resume_skills]

    skill_score = 0
    if job_skills:
        skill_score = (len(matched_skills) / len(job_skills)) * 100

    # =========================
    # EXPERIENCE DETECTION
    # =========================
    experience_score = 0
    years = re.findall(r"(\d+)\+?\s*(year|years)", text)

    if years:
        max_year = max(int(y[0]) for y in years)
        experience_score = min(max_year * 12, 100)

    # check keywords
    exp_keywords = ["internship", "project", "experience", "worked"]
    exp_hits = sum(1 for k in exp_keywords if k in text)
    experience_score += exp_hits * 5
    experience_score = min(experience_score, 100)

    # =========================
    # EDUCATION DETECTION
    # =========================
    edu_keywords = ["btech", "b.e", "diploma", "computer science", "it", "engineering"]
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

    # email + phone
    if re.search(r"\S+@\S+", text):
        quality_score += 10
    if re.search(r"\b\d{10}\b", text):
        quality_score += 10

    quality_score = min(quality_score, 100)

    # =========================
    # KEYWORD MATCH
    # =========================
    keyword_score = calculate_keyword_match_score(text, job_text)

    # =========================
    # FINAL SCORE
    # =========================
    final_score = (
        0.35 * skill_score +
        0.25 * keyword_score +
        0.20 * experience_score +
        0.10 * education_score +
        0.10 * quality_score
    )

    final_score = round(final_score, 2)

    # =========================
    # 🔥 STRONG EXPLANATION SYSTEM
    # =========================
    strengths = []
    weaknesses = []

    if matched_skills:
        strengths.append(f"Strong alignment with required skills like {', '.join(matched_skills[:5])}")

    if experience_score > 60:
        strengths.append("Candidate demonstrates solid hands-on experience through projects or work")

    if quality_score > 70:
        strengths.append("Resume is well structured and contains sufficient technical information")

    if education_score > 60:
        strengths.append("Relevant educational background supports the role requirements")

    if not strengths:
        strengths.append("Basic eligibility met but lacks strong highlights")

    # weaknesses
    if missing_skills:
        weaknesses.append(f"Missing important skills such as {', '.join(missing_skills[:5])}")

    if experience_score < 40:
        weaknesses.append("Limited practical experience detected")

    if quality_score < 50:
        weaknesses.append("Resume lacks detail and proper structure")

    if word_count < 120:
        weaknesses.append("Resume is too short for strong evaluation")

    if not weaknesses:
        weaknesses.append("No major weaknesses detected in initial screening")

    # =========================
    # RECOMMENDATION (SMART)
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
        "recommendation": recommendation
    }