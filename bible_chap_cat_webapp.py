from flask import Flask, request, render_template_string
from groq import Groq
import os
import requests
import json

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
    return data.get("verses", [])

# -----------------------------
# Web page template with widgets
# -----------------------------
HTML_TEMPLATE = """
<!doctype html>
<html>
<head>
  <title>Bible Chapter Classifier</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 40px; }
    input[type=text] { width: 300px; padding: 5px; }
    input[type=submit] { padding: 5px 10px; }
    .card { border: 1px solid #ccc; padding: 15px; margin: 10px 0; border-radius: 8px; background-color: #f9f9f9; }
    .card h3 { margin: 0 0 5px 0; }
    .error { color: red; }
  </style>
</head>
<body>
  <h1>Bible Chapter Classifier</h1>
  <form method="post">
    Chapter Reference: <input type="text" name="chapter" placeholder="Romans 3">
    <input type="submit" value="Classify">
  </form>

  {% if error %}
    <p class="error">{{ error }}</p>
  {% endif %}

  {% if result %}
    <div class="card">
      <h3>Main Theme: {{ result.main_theme.theme }}</h3>
      <p><strong>Key Verse:</strong> {{ result.main_theme.key_verse }}</p>
    </div>

    {% for sub in result.sub_themes %}
    <div class="card">
      <h4>Sub-Theme: {{ sub.theme }}</h4>
      <p><strong>Key Verse:</strong> {{ sub.key_verse }}</p>
    </div>
    {% endfor %}
  {% endif %}
</body>
</html>
"""

# -----------------------------
# Internal classification
# -----------------------------
def classify_chapter_internal(chapter_ref):
    verses_data = fetch_bible_chapter(chapter_ref)
    if not verses_data:
        raise ValueError(f"Could not find chapter: {chapter_ref}")

    chapter_text = " ".join(f"{v['verse']}: {v['text']}" for v in verses_data)

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

    prompt = f"""
You are a Bible scholar. Read the chapter below and:

1️⃣ Pick **one main theme** from this list:
{MAIN_THEMES}

2️⃣ Pick **up to 2 sub-themes** from this list:
{SUB_THEMES}

3️⃣ For each theme/sub-theme, choose **one verse (with verse number)** from this chapter that best represents it.

Return EXACTLY in JSON format like this:

{{
  "main_theme": {{ "theme": "<name>", "key_verse": "<verse_number>: <verse_text>" }},
  "sub_themes": [ {{ "theme": "<name>", "key_verse": "<verse_number>: <verse_text>" }} ]
}}

Chapter:
\"\"\"
{chapter_text}
\"\"\"
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You are a precise theological classifier."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    output_text = response.choices[0].message.content.strip()
    try:
        return json.loads(output_text)
    except Exception:
        raise ValueError(f"LLM did not return valid JSON:\n{output_text}")

# -----------------------------
# Flask route
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None
    if request.method == "POST":
        chapter_ref = request.form.get("chapter", "").strip()
        if not chapter_ref:
            error = "Please enter a chapter reference."
        else:
            try:
                result = classify_chapter_internal(chapter_ref)
            except Exception as e:
                error = str(e)
    return render_template_string(HTML_TEMPLATE, result=result, error=error)

# -----------------------------
# Run server
# -----------------------------
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)
