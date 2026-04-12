import re
from sentence_transformers import SentenceTransformer, util

# Lightweight model for semantic text similarity
model = SentenceTransformer("all-MiniLM-L6-v2")


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_years_of_experience(text: str) -> int:
    text = clean_text(text)

    patterns = [
        r"(\d+)\+?\s+years",
        r"(\d+)\+?\s+yrs",
        r"experience\s+of\s+(\d+)",
        r"(\d+)\s+year\s+experience"
    ]

    max_years = 0

    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                years = int(match)
                if years > max_years:
                    max_years = years
            except:
                pass

    return max_years


def extract_education_score(text: str) -> float:
    text = clean_text(text)

    education_keywords = {
        "phd": 100,
        "doctorate": 100,
        "m.tech": 90,
        "mtech": 90,
        "master": 85,
        "b.tech": 80,
        "btech": 80,
        "b.e": 75,
        "be": 75,
        "bachelor": 70,
        "diploma": 60,
        "12th": 40
    }

    max_score = 0
    for keyword, score in education_keywords.items():
        if keyword in text:
            max_score = max(max_score, score)

    return max_score


def extract_skill_match_score(resume_text: str, job_text: str):
    resume_text = clean_text(resume_text)
    job_text = clean_text(job_text)

    common_skills = [
        "python", "java", "c++", "javascript", "html", "css",
        "flask", "django", "react", "node", "sql", "postgresql",
        "mysql", "mongodb", "machine learning", "deep learning",
        "nlp", "data analysis", "bootstrap", "git", "github",
        "rest api", "docker", "aws", "excel", "pandas", "numpy"
    ]

    required_skills = [skill for skill in common_skills if skill in job_text]
    matched_skills = [skill for skill in required_skills if skill in resume_text]
    missing_skills = [skill for skill in required_skills if skill not in resume_text]

    if not required_skills:
        return 50.0, [], []

    score = (len(matched_skills) / len(required_skills)) * 100
    return round(score, 2), matched_skills, missing_skills


def semantic_similarity_score(resume_text: str, job_text: str) -> float:
    resume_text = clean_text(resume_text)
    job_text = clean_text(job_text)

    if not resume_text or not job_text:
        return 0.0

    embeddings = model.encode([resume_text, job_text], convert_to_tensor=True)
    similarity = util.cos_sim(embeddings[0], embeddings[1]).item()

    # Convert similarity into score
    score = max(0, min(100, round(similarity * 100, 2)))
    return score


def experience_score_from_resume(resume_text: str, job_text: str) -> float:
    resume_years = extract_years_of_experience(resume_text)
    required_years = extract_years_of_experience(job_text)

    if required_years == 0:
        return 80.0 if resume_years > 0 else 50.0

    if resume_years >= required_years:
        return 100.0

    return round((resume_years / required_years) * 100, 2)


def generate_recommendation(final_score: float) -> str:
    if final_score >= 80:
        return "Strong match. Recommended for shortlist."
    elif final_score >= 60:
        return "Moderate match. Recommended for manual review."
    else:
        return "Weak match. Not recommended for shortlist."


def calculate_hybrid_resume_analysis(resume_text: str, job_text: str) -> dict:
    semantic_score = semantic_similarity_score(resume_text, job_text)
    skill_score, matched_skills, missing_skills = extract_skill_match_score(resume_text, job_text)
    experience_score = experience_score_from_resume(resume_text, job_text)
    education_score = extract_education_score(resume_text)

    final_score = (
        semantic_score * 0.45 +
        skill_score * 0.25 +
        experience_score * 0.20 +
        education_score * 0.10
    )

    final_score = round(final_score, 2)

    strengths = []
    weaknesses = []

    if semantic_score >= 70:
        strengths.append("Resume content is semantically aligned with the job description.")
    else:
        weaknesses.append("Overall resume content is not strongly aligned with the job description.")

    if matched_skills:
        strengths.append(f"Matched key skills: {', '.join(matched_skills)}.")
    if missing_skills:
        weaknesses.append(f"Missing or weak skills: {', '.join(missing_skills)}.")

    if experience_score >= 70:
        strengths.append("Relevant experience level appears suitable for this role.")
    else:
        weaknesses.append("Experience relevance appears limited compared to job expectations.")

    if education_score >= 60:
        strengths.append("Educational qualification is relevant for technical screening.")
    else:
        weaknesses.append("Educational background is not strongly visible or not clearly relevant.")

    recommendation = generate_recommendation(final_score)

    explanation = (
        f"Semantic Score: {semantic_score}%, "
        f"Skill Match Score: {skill_score}%, "
        f"Experience Score: {experience_score}%, "
        f"Education Score: {education_score}%, "
        f"Final AI Score: {final_score}%."
    )

    return {
        "final_score": final_score,
        "semantic_score": semantic_score,
        "skill_score": skill_score,
        "experience_score": experience_score,
        "education_score": education_score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommendation": recommendation,
        "explanation": explanation
    }


def safe_calculate_hybrid_resume_analysis(resume_text: str, job_text: str) -> dict:
    """
    Safe wrapper:
    If semantic model fails for any reason,
    fallback to rule-based scoring so app still works.
    """
    try:
        return calculate_hybrid_resume_analysis(resume_text, job_text)
    except Exception:
        skill_score, matched_skills, missing_skills = extract_skill_match_score(resume_text, job_text)
        experience_score = experience_score_from_resume(resume_text, job_text)
        education_score = extract_education_score(resume_text)

        final_score = (
            skill_score * 0.5 +
            experience_score * 0.3 +
            education_score * 0.2
        )

        final_score = round(final_score, 2)

        strengths = []
        weaknesses = []

        if matched_skills:
            strengths.append(f"Matched key skills: {', '.join(matched_skills)}.")
        if missing_skills:
            weaknesses.append(f"Missing or weak skills: {', '.join(missing_skills)}.")

        if experience_score >= 70:
            strengths.append("Relevant experience level appears suitable for this role.")
        else:
            weaknesses.append("Experience relevance appears limited compared to job expectations.")

        if education_score >= 60:
            strengths.append("Educational qualification is relevant for technical screening.")
        else:
            weaknesses.append("Educational background is not strongly visible or not clearly relevant.")

        recommendation = generate_recommendation(final_score)

        explanation = (
            f"Fallback scoring used. "
            f"Skill Match Score: {skill_score}%, "
            f"Experience Score: {experience_score}%, "
            f"Education Score: {education_score}%, "
            f"Final Score: {final_score}%."
        )

        return {
            "final_score": final_score,
            "semantic_score": 0,
            "skill_score": skill_score,
            "experience_score": experience_score,
            "education_score": education_score,
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "recommendation": recommendation,
            "explanation": explanation
        }