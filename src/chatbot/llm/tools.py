from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from src.chatbot.llm.rag import retrieve_context
from datetime import datetime
from typing import Literal
import sqlite3

APP_DB_PATH = "/tmp/job_tracker.db"

def _init_tracker_db():
    with sqlite3.connect(APP_DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS job_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                company TEXT NOT NULL,
                role TEXT NOT NULL,
                status TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, company, role)
            )
        """)


_init_tracker_db()

@tool(parse_docstring=True)
def search_career_documents(query: str, config: RunnableConfig) -> str:
    """Search the user's uploaded resume, cover letters, and job descriptions for specific skills, experience, projects, or metrics.

    Use this tool whenever you need factual details from the user's career documents before answering or giving feedback.

    Args:
        query: Specific search query targeting skills, roles, projects, education, or job requirements.
    """
    userid = config['configurable']['thread_id']
    return retrieve_context(query, userid)


@tool(parse_docstring=True)
def analyze_jd_match(job_description: str, config: RunnableConfig) -> str:
    """Retrieve the user's background from their uploaded resume and compare it against a target job description to identify matched skills, missing keywords, and alignment gaps.

    Use this tool when the user pastes a job description or asks how well their profile fits a specific role.

    Args:
        job_description: Full text or key requirements of the target job posting.
    """
    ...
    userid = config['configurable']['thread_id']
    resume_context = retrieve_context(job_description,userid)

    if resume_context == 'No context available':
        return 'No uploaded resume found for this user. Ask the user to upload their resume first.'

    return (
        f"CANDIDATE RESUME CONTEXT:\n{resume_context}\n\n"
        f"TARGET JOB DESCRIPTION:\n{job_description}\n\n"
        "Compare the candidate's actual resume context above against the job description. "
        "List: (1) Matched skills & projects with evidence, (2) Missing keywords or skill gaps, "
        "and (3) An honest overall fit verdict."
    )

@tool(parse_docstring=True)
def generate_interview_questions(target_role: str, focus_area: str = "technical", config: RunnableConfig = None) -> str:
    """Retrieve the user's projects and work experience to generate tailored interview questions grounded in their actual tech stack and background.

    Use this tool when the user asks to practice for an interview or wants mock questions for a role.

    Args:
        target_role: The job title the user is preparing for (e.g., "AI/ML Engineer", "Backend Developer").
        focus_area: Interview category to emphasize, such as "technical", "system_design", or "behavioral".
    """
    userid = config['configurable']['thread_id']
    resume_context = retrieve_context(query=f'{target_role} {focus_area} experience project skills')

    if resume_context == 'No context available':
        return 'No uploaded resume found for this user. Ask the user to upload their resume first.'

    return (
        f"Target Role: \n{target_role}\n\n"
        f"Focus Area: \n{focus_area}\n\n"
        f"Resume Contect: \n{resume_context}\n\n"
        f"Provide a set of questions based on the above information and from fetched resume. If resume has multiple experience in different fields then provide a set of 5 questions based on each experience. Follow the similar pattern in case of multiple projects.\n\n"
    )


@tool(parse_docstring=True)
def log_job_application(company: str, role: str, status: Literal['Applied','Interviewing','Offer','Rejected','Ghosted'], config: RunnableConfig) -> str:
    """Create or update a job application entry in the user's personal application tracker.

    Use this tool when the user mentions applying to a company, scheduling an interview, receiving an offer, or wanting to track an application status.

    Args:
        company: Name of the company (e.g., "Google", "Razorpay").
        role: Position title applied for.
        status: Current stage of the application (e.g., "Applied", "Interviewing", "Offer", "Rejected").
    """

    userid = config['configurable']['thread_id']
    now_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    # resume_context = retrieve_context(query=f'{company} {role} {status} create or update the application')

    with sqlite3.connect(APP_DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO job_applications(user_id, company, role, status, updated_at)
            VALUES(?,?,?,?,?)
            ON CONFLICT(user_id,company,role)
            DO UPDATE SET status = excluded.status, updated_at = excluded.updated_at
            """,
            (userid, company.strip(), role.strip(), status, now_time),
        )

    return (
        f"Saved in tracker -> Company: {company} | Role: {role} | Status: {status} (Updated: {now_time}). "
        "Confirm this update clearly to the user."
    )

@tool
def get_job_application(config:RunnableConfig):
    """Fetch details of job applications entry in the user's personal application tracker.

    Use this tool when the user mentions wanting to know all applications they have applied so far to.
    """
    userid = config['configurable']['thread_id']

    with sqlite3.connect(APP_DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT company, role, status, updated_at 
            FROM job_applications 
            WHERE user_id = ?
            ORDER BY updated_at DESC         
            """,
            (userid),
        ).fetchall()


    if not rows:
        return "No job applications found in the tracker for this user yet."

    formatted_rows = "\n".join(
        f"- {company} | {role} | Status: {status} (Updated: {updated_at})"
        for company, role, status, updated_at in rows
    )

    return (
            f"TRACKED JOB APPLICATIONS:\n{formatted_rows}\n\n"
            "Present these tracked applications clearly to the user."
    )