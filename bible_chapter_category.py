from flask import Flask, request, jsonify
from groq import Groq
import os
import requests

app = Flask(__name__)

# -----------------------------
# Initialize Groq client
# -----------------------------
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# -----------------------------
# Bible chapter fetcher
# -----------------------------
def fetch_bible_chapter(chapter_ref):
    query = chapter_ref.lower().replace(" ", "+")
    url = f"https://bible-api.com/{query}"
    response = requests.get(url)
    if response.status_code != 200:
        return None
    data = response.json()
    verses = data.get("verses", [])
    return verses  # list of dicts: {"verse": 1, "text": "..."} 

# -----------------------------
# Flask route
# -----------------------------
@app.route("/classify_chapter", methods=["POST"])
def classify_chapter():
    data = request.get_json()
    if not data or "chapter" not in data:
        return jsonify({"error": "Missing 'chapter' field"}), 400

    chapter_ref = data["chapter"].strip()

    # 1️⃣ Fetch chapter verses
    verses_data = fetch_bible_chapter(chapter_ref)
    if not verses_data:
        return jsonify({"error": f"Could not find chapter: {chapter_ref}"}), 404

    # Combine all verses for LLM
    chapter_text = " ".join(v["text"] for v in verses_data)

    # 2️⃣ Themes
    MAIN_THEMES = """
SIN_AND_JUDGMENT
JUSTIFICATION
SALVATION
ATONEMENT
RIGHTEOUSNESS
LOVE
PRAISE
TRUST_IN_GOD
REPENTANCE
"""
    SUB_THEMES = """
FAITH
CHRISTOLOGY
HOLY_SPIRIT
DISCIPLESHIP
SOCIAL_JUSTICE
MESSIANIC_PROPHECY
POETRY_PRAISE
DIVINE_PROTECTION
"""

    # 3️⃣ Prompt for LLM (curly braces escaped)
    prompt = f"""
You are a Bible scholar. Read the chapter below and:

1️⃣ Pick **one main theme** from this list:
{MAIN_THEMES}

2️⃣ Pick **up to 2 sub-themes** from this list:
{SUB_THEMES}

3️⃣ For each theme/sub-theme, choose **one verse from this chapter** that best represents it.

Return EXACTLY in JSON format like this:

{{
  "main_theme": {{ "theme": "<name>", "key_verse": "<verse_text>" }},
  "sub_themes": [ {{ "theme": "<name>", "key_verse": "<verse_text>" }} ]
}}

Chapter:
\"\"\"
{chapter_text}
\"\"\"
"""

    # 4️⃣ LLM call
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You are a precise theological classifier."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    output = response.choices[0].message.content.strip()

    # 5️⃣ Return JSON (LLM returns JSON string)
    return output

# -----------------------------
# Run the server
# -----------------------------
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)
