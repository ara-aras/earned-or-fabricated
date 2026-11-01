"""Resume-writing knowledge base used by the builder, linter and interviewer.

Plain data, not a model. Compiled from widely taught resume practice
(university career-centre action-verb lists, the "X-Y-Z" accomplishment
formula popularised by Google recruiters, ATS-parsing guidance from the
major applicant-tracking vendors, and common recruiter skim-reading
advice). Every rule the linter enforces has an id here so the UI can say
exactly which guideline a suggestion comes from.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Action verbs by competency. The builder uses these to (a) recognise strong
# openers, (b) swap a repeated opener for a same-meaning synonym, and (c)
# suggest verbs in the UI.
# ---------------------------------------------------------------------------
ACTION_VERBS: dict[str, list[str]] = {
    "build": ["built", "developed", "engineered", "implemented", "created", "designed", "architected",
              "prototyped", "programmed", "coded", "assembled", "constructed", "launched", "shipped",
              "deployed", "released", "delivered", "integrated", "configured", "installed", "set up",
              "contributed", "added", "wrote", "containerized", "ran", "reviewed", "took"],
    "improve": ["optimized", "improved", "accelerated", "streamlined", "refactored", "reduced", "cut",
                "increased", "boosted", "enhanced", "upgraded", "modernized", "simplified", "stabilized",
                "hardened", "scaled", "automated", "consolidated", "migrated", "overhauled", "revamped",
                "restructured", "tuned", "debugged", "fixed", "resolved", "eliminated", "lowered"],
    "lead": ["led", "directed", "headed", "spearheaded", "championed", "drove", "owned", "orchestrated",
             "managed", "supervised", "coordinated", "oversaw", "chaired", "initiated", "established",
             "founded", "mobilized", "delegated", "steered"],
    "analyze": ["analyzed", "evaluated", "assessed", "investigated", "researched", "measured",
                "benchmarked", "modeled", "forecasted", "quantified", "audited", "diagnosed", "surveyed",
                "tested", "validated", "verified", "identified", "mapped", "profiled", "examined"],
    "communicate": ["presented", "authored", "wrote", "documented", "published", "explained", "pitched",
                    "negotiated", "persuaded", "advocated", "collaborated", "partnered", "liaised",
                    "facilitated", "convened", "briefed", "reported", "demonstrated"],
    "teach": ["mentored", "coached", "trained", "taught", "tutored", "onboarded", "guided", "advised",
              "instructed", "educated", "enabled", "supported"],
    "achieve": ["achieved", "won", "earned", "exceeded", "surpassed", "attained", "grew", "expanded",
                "generated", "secured", "saved", "doubled", "tripled", "outperformed", "awarded"],
    "organize": ["organized", "planned", "scheduled", "prioritized", "systematized", "standardized",
                 "cataloged", "administered", "maintained", "monitored", "tracked", "operated", "ran",
                 "handled", "processed", "executed"],
    "create": ["designed", "illustrated", "conceptualized", "composed", "crafted", "curated", "shaped",
               "styled", "visualized", "sketched", "produced", "filmed", "edited"],
    "serve": ["assisted", "served", "resolved", "answered", "helped", "responded", "retained",
              "satisfied", "supported", "triaged"],
}
ALL_VERBS: set[str] = {v for vs in ACTION_VERBS.values() for v in vs}

# Same-meaning swaps used ONLY to break repetition of an opener; each set is
# close enough in meaning that swapping never changes what the user claimed.
SYNONYMS: list[set[str]] = [
    {"built", "developed", "engineered", "implemented"},
    {"created", "designed", "developed"},
    {"led", "directed", "headed"},
    {"improved", "enhanced", "strengthened"},
    {"reduced", "cut", "lowered", "decreased"},
    {"increased", "boosted", "raised", "grew"},
    {"analyzed", "evaluated", "assessed", "examined"},
    {"wrote", "authored", "documented"},
    {"managed", "oversaw", "coordinated"},
    {"optimized", "tuned", "streamlined"},
    {"collaborated", "partnered", "worked"},
    {"mentored", "coached", "guided"},
    {"automated", "scripted"},
    {"deployed", "released", "shipped"},
]

# present/base -> past, for fixing tense on finished roles
PAST_TENSE: dict[str, str] = {
    "build": "built", "lead": "led", "write": "wrote", "run": "ran", "drive": "drove", "cut": "cut",
    "set": "set", "teach": "taught", "grow": "grew", "win": "won", "make": "made", "make up": "made up",
    "develop": "developed", "design": "designed", "create": "created", "implement": "implemented",
    "manage": "managed", "maintain": "maintained", "improve": "improved", "reduce": "reduced",
    "increase": "increased", "analyze": "analyzed", "analyse": "analysed", "optimize": "optimized",
    "automate": "automated", "deploy": "deployed", "launch": "launched", "ship": "shipped",
    "migrate": "migrated", "refactor": "refactored", "test": "tested", "debug": "debugged",
    "fix": "fixed", "mentor": "mentored", "coordinate": "coordinated", "collaborate": "collaborated",
    "support": "supported", "own": "owned", "research": "researched", "present": "presented",
    "document": "documented", "integrate": "integrated", "configure": "configured",
    "monitor": "monitored", "train": "trained", "tutor": "tutored", "organize": "organized",
    "plan": "planned", "deliver": "delivered", "establish": "established", "evaluate": "evaluated",
    "streamline": "streamlined", "scale": "scaled", "architect": "architected", "help": "helped",
    "handle": "handled", "conduct": "conducted", "oversee": "oversaw", "prototype": "prototyped",
    "spearhead": "spearheaded", "work": "worked", "assist": "assisted", "engineer": "engineered",
}
# base -> 3rd person present, for "Builds ..." style on current roles
def present_tense(base: str) -> str:
    if base.endswith(("s", "sh", "ch", "x", "z")):
        return base + "es"
    if base.endswith("y") and base[-2:-1] not in "aeiou":
        return base[:-1] + "ies"
    return base + "s"


# ---------------------------------------------------------------------------
# Weak / vague / filler phrasing. (pattern, replacement or None, rule id, why)
# Replacements keep meaning; None = flag only, never auto-changed.
# ---------------------------------------------------------------------------
WEAK_PHRASES: list[tuple[str, str | None, str, str]] = [
    (r"\bin order to\b", "to", "concise", "“in order to” → “to”"),
    (r"\butili[sz](e|ed|es|ing)\b", "use", "concise", "“utilize” → “use”"),
    (r"\bsuccessfully\s+", "", "concise", "“successfully” adds nothing — the result shows success"),
    (r"\beffectively\s+", "", "concise", "“effectively” is filler"),
    (r"\bvarious\s+", "", "specific", "“various” is vague — name them or drop it"),
    (r"\bseveral\b", None, "specific", "“several” — give the number"),
    (r"\bnumerous\b", None, "specific", "“numerous” — give the number"),
    (r"\ba lot of\b", None, "specific", "“a lot of” — quantify it"),
    (r"\betc\.?", None, "specific", "“etc.” — list what matters and stop"),
    (r"\bvery\s+", "", "concise", "“very” is filler"),
    (r"\breally\s+", "", "concise", "“really” is filler"),
    (r"\bhard[- ]?working\b", None, "show-dont-tell", "“hard-working” — show it with a result instead"),
    (r"\bteam player\b", None, "show-dont-tell", "“team player” — show collaboration in a bullet"),
    (r"\bdetail[- ]oriented\b", None, "show-dont-tell", "“detail-oriented” — cliché"),
    (r"\bresults[- ]driven\b", None, "show-dont-tell", "“results-driven” — show the results"),
    (r"\bgo[- ]getter\b", None, "show-dont-tell", "“go-getter” — cliché"),
    (r"\bself[- ]starter\b", None, "show-dont-tell", "“self-starter” — cliché"),
    (r"\bpassionate about\b", None, "show-dont-tell", "“passionate about” — show it with a project"),
    (r"\bthink outside the box\b", None, "show-dont-tell", "cliché"),
    (r"\bsynergy\b", None, "show-dont-tell", "buzzword"),
    (r"\bfamiliar with\b", None, "confidence", "“familiar with” undersells — list it as a skill or cut it"),
    (r"\bexposure to\b", None, "confidence", "“exposure to” undersells"),
    (r"\breferences available upon request\b", "", "outdated", "outdated line — recruiters assume it"),
    (r"\btasked with\s+", "", "ownership", "“tasked with” is passive — say what you did"),
    (r"\bin charge of\b", "owned", "ownership", "“in charge of” → “owned”"),
    (r"\bwas involved in\b", "contributed to", "ownership", "“was involved in” is passive"),
    (r"\bdealt with\b", "handled", "ownership", "“dealt with” → “handled”"),
]

PRONOUNS = r"\b(I|me|my|mine|we|our|us)\b"

# ---------------------------------------------------------------------------
# Skills taxonomy -> grouped "Technical Skills" block (Languages / Frameworks
# / Data / Cloud & DevOps / Tools). Unknown skills fall into "Other".
# ---------------------------------------------------------------------------
SKILL_GROUPS: dict[str, list[str]] = {
    "Languages": ["python", "java", "javascript", "typescript", "c", "c++", "c#", "go", "golang", "rust",
                  "ruby", "php", "swift", "kotlin", "scala", "r", "matlab", "sql", "bash", "shell",
                  "html", "css", "dart", "elixir", "haskell", "lua", "perl", "julia", "solidity", "verilog"],
    "Frameworks": ["react", "next.js", "nextjs", "vue", "angular", "svelte", "node.js", "node", "express",
                   "django", "flask", "fastapi", "spring", "spring boot", ".net", "rails", "laravel",
                   "react native", "flutter", "tailwind", "redux", "graphql", "jquery", "nestjs",
                   "pytorch", "tensorflow", "keras", "scikit-learn", "pandas", "numpy", "langchain",
                   "hugging face", "opencv", "spark", "three.js"],
    "Data & ML": ["postgresql", "postgres", "mysql", "sqlite", "mongodb", "redis", "elasticsearch",
                  "cassandra", "dynamodb", "snowflake", "bigquery", "databricks", "kafka", "airflow",
                  "dbt", "hadoop", "tableau", "power bi", "excel", "machine learning", "deep learning",
                  "nlp", "computer vision", "llms", "data analysis", "statistics", "a/b testing"],
    "Cloud & DevOps": ["aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "terraform",
                       "ansible", "jenkins", "github actions", "ci/cd", "linux", "nginx", "serverless",
                       "vercel", "heroku", "firebase", "prometheus", "grafana", "helm"],
    "Tools": ["git", "github", "gitlab", "jira", "confluence", "figma", "postman", "vs code", "jupyter",
              "notion", "slack", "webpack", "vite", "jest", "cypress", "selenium", "pytest", "junit",
              "playwright", "storybook", "arduino", "raspberry pi"],
}
_SKILL_TO_GROUP = {s: g for g, ss in SKILL_GROUPS.items() for s in ss}


def skill_group(skill: str) -> str:
    return _SKILL_TO_GROUP.get(skill.strip().lower(), "Other")


# ---------------------------------------------------------------------------
# Role families: the keywords recruiters and ATS filters for each family
# commonly look for. Used to detect the target family and suggest gaps.
# ---------------------------------------------------------------------------
ROLE_FAMILIES: dict[str, dict] = {
    "software engineer": {
        "match": ["software", "developer", "engineer", "full stack", "full-stack", "sde", "programmer"],
        "keywords": ["data structures", "algorithms", "system design", "rest api", "git", "unit testing",
                     "ci/cd", "sql", "cloud", "docker", "code review", "agile", "debugging", "oop"],
    },
    "frontend": {
        "match": ["frontend", "front-end", "front end", "ui engineer", "web developer"],
        "keywords": ["javascript", "typescript", "react", "css", "html", "accessibility", "responsive design",
                     "performance", "testing", "next.js", "state management", "design systems"],
    },
    "backend": {
        "match": ["backend", "back-end", "back end", "api", "platform"],
        "keywords": ["rest api", "microservices", "sql", "postgresql", "redis", "caching", "docker",
                     "kubernetes", "message queues", "scalability", "observability", "security"],
    },
    "data analyst": {
        "match": ["data analyst", "business analyst", "analytics", "bi "],
        "keywords": ["sql", "excel", "tableau", "power bi", "python", "statistics", "dashboards",
                     "a/b testing", "data visualization", "stakeholders", "kpis", "data cleaning"],
    },
    "data scientist": {
        "match": ["data scientist", "data science"],
        "keywords": ["python", "machine learning", "statistics", "sql", "pandas", "scikit-learn",
                     "experimentation", "feature engineering", "modeling", "visualization", "deep learning"],
    },
    "ml engineer": {
        "match": ["machine learning", "ml engineer", "ai engineer", "mlops", "research engineer"],
        "keywords": ["pytorch", "tensorflow", "python", "mlops", "model deployment", "llms", "nlp",
                     "computer vision", "gpu", "data pipelines", "evaluation", "docker", "kubernetes"],
    },
    "devops": {
        "match": ["devops", "sre", "site reliability", "infrastructure", "cloud engineer", "platform engineer"],
        "keywords": ["aws", "kubernetes", "docker", "terraform", "ci/cd", "linux", "monitoring",
                     "incident response", "networking", "automation", "bash", "observability"],
    },
    "mobile": {
        "match": ["mobile", "ios", "android", "react native", "flutter"],
        "keywords": ["swift", "kotlin", "react native", "flutter", "app store", "mobile ui", "rest api",
                     "offline", "performance", "testing"],
    },
    "security": {
        "match": ["security", "cyber", "infosec", "penetration", "soc "],
        "keywords": ["network security", "siem", "incident response", "vulnerability", "owasp", "linux",
                     "python", "threat modeling", "iam", "compliance", "penetration testing"],
    },
    "product manager": {
        "match": ["product manager", "product owner", "pm "],
        "keywords": ["roadmap", "stakeholders", "user research", "metrics", "a/b testing", "prioritization",
                     "agile", "sql", "go-to-market", "requirements", "kpis"],
    },
    "designer": {
        "match": ["designer", "ux", "ui/ux", "product design"],
        "keywords": ["figma", "user research", "prototyping", "design systems", "usability testing",
                     "wireframes", "accessibility", "interaction design"],
    },
}


def role_family(text: str) -> str:
    t = f" {text.lower()} "
    for fam, spec in ROLE_FAMILIES.items():
        if fam == "software engineer":
            continue
        if any(m in t for m in spec["match"]):
            return fam
    return "software engineer"


# ---------------------------------------------------------------------------
# Layout guidance by experience level (drives section order + page budget).
# ---------------------------------------------------------------------------
LEVELS = {
    "student": {"order": ["education", "experience", "projects", "skills"], "pages": 1,
                "summary": False, "max_bullets": 4,
                "why": "students and new grads lead with education; one page"},
    "early": {"order": ["experience", "projects", "skills", "education"], "pages": 1,
              "summary": True, "max_bullets": 5,
              "why": "0–5 years: experience first, education last; one page"},
    "senior": {"order": ["experience", "skills", "projects", "education"], "pages": 2,
               "summary": True, "max_bullets": 6,
               "why": "10+ years: two pages are acceptable"},
}

# ---------------------------------------------------------------------------
# Guideline catalogue shown in the UI. id -> (title, detail)
# ---------------------------------------------------------------------------
GUIDELINES: dict[str, tuple[str, str]] = {
    "one-page": ("Fits the page budget", "One page for students and early career; two only with 10+ years."),
    "contact": ("Contact line up top", "Name, phone, email, LinkedIn/GitHub, city — no photo, no full address."),
    "headings": ("Standard section headings", "Education, Experience, Projects, Technical Skills — ATS parsers look for these words."),
    "single-column": ("Single column, no tables or graphics", "Multi-column layouts and icons scramble ATS parsing."),
    "verb-first": ("Every bullet starts with an action verb", "“Built…”, “Led…”, not “Responsible for…”."),
    "verb-variety": ("Opening verbs don't repeat", "The same verb three times reads as a template."),
    "quantified": ("Bullets show measurable results", "X-Y-Z: accomplished X, measured by Y, by doing Z."),
    "tense": ("Past tense for past roles, present for current", "Mixed tense is the most common copy-edit flag."),
    "no-pronouns": ("No first-person pronouns", "Resumes drop “I”, “my”, “we”."),
    "concise": ("Bullets are one to two lines", "Aim for 8–28 words; cut filler adverbs."),
    "specific": ("Specific, not vague", "Replace “various”, “several”, “etc.” with the actual thing."),
    "show-dont-tell": ("Show, don't tell", "Self-descriptions like “team player” carry no evidence."),
    "keywords": ("Mirrors the listing's keywords", "Use the listing's exact phrasing for skills you really have."),
    "dates": ("Consistent dates", "“Jun 2024 – Aug 2024” everywhere, right-aligned."),
    "skills-grouped": ("Skills grouped by type", "Languages, Frameworks, Data, Cloud & DevOps, Tools."),
    "ownership": ("Active, owned phrasing", "“Owned”, “Led”, not “tasked with” or “was involved in”."),
    "confidence": ("No hedging", "“Familiar with” and “exposure to” undersell."),
    "outdated": ("No outdated lines", "No objective statement, no “references available”."),
}

# ---------------------------------------------------------------------------
# Interview question bank (the interviewer picks from these by role/gaps).
# ---------------------------------------------------------------------------
BEHAVIORAL_QUESTIONS = [
    ("ownership", "Tell me about a project you owned end to end. What did you decide, and how did it turn out?"),
    ("failure", "Describe a time something you built broke or failed. What did you do, and what changed afterwards?"),
    ("conflict", "Tell me about a disagreement with a teammate about a technical decision. How was it resolved?"),
    ("ambiguity", "Tell me about a time the requirements were unclear. How did you decide what to build?"),
    ("deadline", "Describe a time you had to deliver under a tight deadline. What did you cut, and why?"),
    ("learning", "Tell me about the fastest you've had to learn a new technology. How did you do it?"),
    ("feedback", "Tell me about critical feedback you received and what you did with it."),
    ("impact", "What's the piece of work you're proudest of, and how do you know it mattered?"),
    ("prioritize", "Tell me about a time you had more work than time. How did you prioritize?"),
    ("initiative", "Tell me about something you improved that nobody asked you to."),
]

TECH_QUESTION_TEMPLATES = {
    "Languages": "What's something about {skill} that tripped you up at first, and how did you work it out on a real project?",
    "Frameworks": "Walk me through how you structured a real {skill} project. What would you do differently now?",
    "Data & ML": "Tell me about a time you used {skill} to answer a real question. How did you know the answer was right?",
    "Cloud & DevOps": "How have you used {skill} in practice? Describe a problem you hit and how you debugged it.",
    "Tools": "How do you use {skill} day to day, and what's a habit that makes you faster with it?",
    "Other": "Tell me about something real you built with {skill}. What was hard, and how did it turn out?",
}

ROLE_QUESTIONS = {
    "frontend": "How would you find and fix a React page that feels slow when users type?",
    "backend": "An API endpoint's latency doubled after a deploy. Walk me through how you'd find the cause.",
    "data analyst": "A dashboard metric dropped 20% overnight. How do you figure out whether it's real?",
    "data scientist": "How would you decide whether a new model is actually better than the old one?",
    "ml engineer": "How would you take a model from a notebook to something serving real traffic?",
    "devops": "A service is down at 2 a.m. Walk me through your first 15 minutes.",
    "mobile": "Users say the app is slow on older phones. How would you investigate?",
    "security": "How would you triage a report that credentials may have leaked?",
    "product manager": "How would you decide what to build next quarter with three competing requests?",
    "designer": "Walk me through how you'd validate a design before engineers build it.",
    "software engineer": "How would you design a URL shortener? Start simple, then tell me what breaks at scale.",
}
