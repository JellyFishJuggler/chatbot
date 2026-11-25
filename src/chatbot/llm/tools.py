from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig


@tool(parse_docstring=True)
def search_career_documents(query: str, config: RunnableConfig) -> str:
    """Search the user's uploaded resume, cover letters, and job descriptions for specific skills, experience, projects, or metrics.

    Use this tool whenever you need factual details from the user's career documents before answering or giving feedback.

    Args:
        query: Specific search query targeting skills, roles, projects, education, or job requirements.
    """
    ...


@tool(parse_docstring=True)
def analyze_jd_match(job_description: str, config: RunnableConfig) -> str:
    """Retrieve the user's background from their uploaded resume and compare it against a target job description to identify matched skills, missing keywords, and alignment gaps.

    Use this tool when the user pastes a job description or asks how well their profile fits a specific role.

    Args:
        job_description: Full text or key requirements of the target job posting.
    """
    ...


@tool(parse_docstring=True)
def generate_interview_questions(target_role: str, focus_area: str = "technical", config: RunnableConfig = None) -> str:
    """Retrieve the user's projects and work experience to generate tailored interview questions grounded in their actual tech stack and background.

    Use this tool when the user asks to practice for an interview or wants mock questions for a role.

    Args:
        target_role: The job title the user is preparing for (e.g., "AI/ML Engineer", "Backend Developer").
        focus_area: Interview category to emphasize, such as "technical", "system_design", or "behavioral".
    """
    ...


@tool(parse_docstring=True)
def log_job_application(company: str, role: str, status: str, config: RunnableConfig) -> str:
    """Create or update a job application entry in the user's personal application tracker.

    Use this tool when the user mentions applying to a company, scheduling an interview, receiving an offer, or wanting to track an application status.

    Args:
        company: Name of the company (e.g., "Google", "Razorpay").
        role: Position title applied for.
        status: Current stage of the application (e.g., "Applied", "Interviewing", "Offer", "Rejected").
    """
    ...