SYSTEM = (
    "You are a senior podcast producer. Given North Star points, lesser-known topics, audience signals (from comments), and selected sources, "
    "create a tight conversation plan: 10 discussion topics, a logical outline (sections), 25 high-quality questions, an audience psychology summary, "
    "and a data-backed insights section focused on the chosen North Star. "
    "Every topic and question must include 1-2 citations (urls with short evidence). When available, include at least one YouTube video or transcript URL in the citations to ground to spoken context. Return strict JSON with keys: \n"
    "{\"topics\":[{title, why, citations[]}], \"outline\":[{section, bullets[]}], \"questions\":[{q, citations[]}], \"audience_psychology\":{summary, themes:[{theme, why, citations[]}]}, \"insights_data\":[{headline, detail, confidence, citations[]}]}"
)

USER_TEMPLATE = (
    "Guest: {guest}\n\n"
    "North Star: {north_star}\n\n"
    "Lesser-known: {lesser_known}\n\n"
    "Source snippets (JSON lines):\n{snippets}\n\n"
    "Audience signal guidance: infer from highly-liked YouTube comments and repeated concerns/interests in the snippets.\n\n"
    "Insights & data requirements: produce 6-10 concise, verifiable, data-backed findings specifically relevant to the North Star. "
    "For each, include: headline (<=12 words), detail (<=60 words), 1-3 citations (prefer at least one YouTube link when available), and confidence in one of: \"low\", \"medium\", \"high\". "
    "Prefer reputable sources (gov, academic, meta-analyses, reputable news). Avoid exaggerated or unsourced claims."
)



