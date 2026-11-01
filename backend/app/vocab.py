"""Static resume vocabulary shared by the rule layers (text_rules, ats) and the
research verifier."""

# Static vocabulary: resume/tech/job keywords, degree terms, action verbs,
# and generic filler words (used to *detect* weakly-written resumes -- their
# presence pushes the filler_noise channel target up during training).
SKILL_TERMS = [
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
    "ruby", "php", "swift", "kotlin", "scala", "sql", "nosql", "html", "css",
    "react", "angular", "vue", "node.js", "next.js", "django", "flask",
    "fastapi", "spring", "express", "graphql", "rest api", "grpc",
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ansible",
    "jenkins", "ci/cd", "git", "github", "gitlab", "linux", "bash",
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "kafka",
    "spark", "hadoop", "airflow", "snowflake", "databricks", "tableau",
    "power bi", "excel", "pandas", "numpy", "scikit-learn", "tensorflow",
    "pytorch", "keras", "machine learning", "deep learning", "nlp",
    "computer vision", "data science", "data engineering", "data analysis",
    "statistics", "a/b testing", "microservices", "distributed systems",
    "system design", "api design", "object-oriented programming", "agile",
    "scrum", "kanban", "jira", "confluence", "figma", "ui/ux", "product design",
    "cybersecurity", "penetration testing", "networking", "devops", "sre",
    "unit testing", "integration testing", "test automation", "selenium",
    "cypress", "react native", "flutter", "ios", "android", "mobile development",
    "cloud architecture", "serverless", "load balancing", "caching",
    "message queues", "webrtc", "websockets", "oauth", "jwt", "security",
]

DEGREE_TERMS = [
    "bachelor", "bachelor of science", "bachelor of arts", "master",
    "master of science", "mba", "phd", "doctorate", "computer science",
    "software engineering", "electrical engineering", "information technology",
    "data science degree", "mathematics", "statistics degree", "physics",
    "university", "college", "gpa", "coursework", "diploma", "certification",
    "certified", "bootcamp",
]

ACTION_VERBS = [
    "led", "built", "designed", "developed", "implemented", "architected",
    "launched", "shipped", "optimized", "improved", "reduced", "increased",
    "automated", "streamlined", "scaled", "migrated", "refactored",
    "mentored", "managed", "coordinated", "collaborated", "delivered",
    "created", "engineered", "deployed", "debugged", "analyzed", "researched",
    "presented", "negotiated", "spearheaded", "owned", "drove", "established",
]

SENIORITY_TERMS = [
    "senior", "lead", "principal", "staff", "junior", "entry-level", "intern",
    "internship", "manager", "director", "head of", "vp", "years of experience",
    "years experience",
]

FILLER_WORDS = [
    "hardworking", "team player", "detail-oriented", "self-starter",
    "go-getter", "results-driven", "passionate", "motivated", "dynamic",
    "synergy", "proactive", "think outside the box", "fast learner",
    "people person", "works well", "responsible for", "duties included",
    "helped with", "assisted with", "familiar with", "exposure to",
]

MISC_TERMS = [
    "communication", "leadership", "problem solving", "critical thinking",
    "teamwork", "time management", "project management", "stakeholder",
    "cross-functional", "remote", "hybrid", "full-time", "contract",
    "startup", "enterprise", "fintech", "healthtech", "e-commerce",
    "saas", "b2b", "b2c", "kpi", "roi", "revenue", "budget", "quarterly",
    "achievement", "award", "publication", "patent", "open source",
    "hackathon", "conference", "speaker", "volunteer", "internship",
]
