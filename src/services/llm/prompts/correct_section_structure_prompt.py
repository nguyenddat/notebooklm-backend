prompt = """
You are given a list of section headers extracted from a PDF document.
Each header has an original order index, title, and page range.

Your task:
1. Infer the correct hierarchical structure (chapter / section / subsection) and assign into a hierarchical tree structure.
3. Keep the id provided in the input. Do NOT reassign or change them.
4. Root node should be level 0 with title "ROOT".
5. Do NOT invent or remove sections.
6. Do NOT modify titles.
7. Output ONLY valid JSON matching the provided schema.

Rules:
- Level 1: top-level chapters
- Level 2+: subsections
- Sections with similar titles and nearby pages are likely siblings.

Input sections:
{sections}

Please return the answer in the following json schema:
"""