from flask import Flask, request, render_template_string
from groq import Groq
import os
import requests
import json
import re

app = Flask(__name__)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# -----------------------------
# Bible Chapter Fetch
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
# Category Lists
# -----------------------------
DOCTRINE_LIST = [
    # 1. Theology Proper (Doctrine of God)
    "Existence of God",
    "Attributes of God",
    "Trinity",
    "Names of God",
    "Works of God",
    "Providence",
    "Sovereignty of God",

    # 2. Christology (Doctrine of Christ)
    "Deity of Christ",
    "Humanity of Christ",
    "Incarnation",
    "Virgin Birth",
    "Atonement",
    "Resurrection of Christ",
    "Ascension",
    "Second Coming",

    # 3. Pneumatology (Doctrine of the Holy Spirit)
    "Personhood of the Holy Spirit",
    "Deity of the Holy Spirit",
    "Work of the Holy Spirit",
    "Indwelling of the Spirit",
    "Filling of the Spirit",
    "Spiritual Gifts",

    # 4. Anthropology (Doctrine of Man)
    "Creation of Man",
    "Image of God",
    "Nature of Man",
    "Body, Soul, and Spirit",
    "Free Will",
    "Human Responsibility",

    # 5. Hamartiology (Doctrine of Sin)
    "Origin of Sin",
    "Nature of Sin",
    "Total Depravity",
    "Effects of Sin",
    "Consequences of Sin",

    # 6. Soteriology (Doctrine of Salvation)
    "Election",
    "Calling",
    "Regeneration",
    "Repentance",
    "Faith",
    "Justification",
    "Adoption",
    "Sanctification",
    "Perseverance",
    "Glorification",

    # 7. Ecclesiology (Doctrine of the Church)
    "Nature of the Church",
    "Purpose of the Church",
    "Unity of the Church",
    "Leadership in the Church",
    "Spiritual Authority",
    "Baptism",
    "Lord’s Supper",

    # 8. Angelology (Doctrine of Angels)
    "Nature of Angels",
    "Ministry of Angels",
    "Ranks of Angels",
    "Guardian Angels",

    # 9. Demonology (Doctrine of Satan and Demons)
    "Satan",
    "Demons",
    "Fall of Satan",
    "Spiritual Warfare",
    "Demonic Influence",

    # 10. Eschatology (Doctrine of Last Things)
    "Death",
    "Intermediate State",
    "Resurrection of the Dead",
    "Second Coming of Christ",
    "Tribulation",
    "Millennium",
    "Final Judgment",
    "Heaven",
    "Hell",
    "New Creation",

    # 11. The Kingdom of God
    "Kingdom of God",
    "Reign of Christ",
    "Already and Not Yet Kingdom",
    "Eternal Life"
]

GROWTH_LIST = [
    "Prayer", "Faith", "Obedience", "Discipleship", "Worship", "Service",
    "Stewardship", "Perseverance", "Spiritual Growth", "Humility",
    "Repentance", "Love", "Trust in God", "Walking in the Spirit",
    "Spiritual Warfare", "Calling"
]

CHARLES_STANLEY_30 = [
    "Intimacy with God",
    "Obey God and leave all the consequences to Him",
    "God’s Word is an anchor in times of trouble",
    "Awareness of God’s presence",
    "Obey God even when it seems unreasonable",
    "You reap what you sow",
    "Dark moments serve God’s purpose",
    "Fight all your battles on your knees",
    "Trust God beyond what you see",
    "God moves heaven and earth to show you His will",
    "God provides when we obey Him",
    "Peace with God",
    "Listening to God",
    "God acts on behalf of those who wait for Him",
    "Brokenness is God’s requirement for usefulness",
    "Outside God’s will everything becomes ashes",
    "You stand tallest when you are on your knees",
    "You are never a victim of your circumstances",
    "Let go of what you hold too tightly",
    "Disappointments are inevitable, discouragement is a choice",
    "Obedience always brings blessing",
    "Walk in the Spirit and obey His promptings",
    "You can never outgive God",
    "Let Jesus live His life in and through you",
    "God blesses us so we can bless others",
    "Adversity deepens our relationship with God",
    "Prayer is life’s greatest time-saver",
    "Never go it alone in your faith",
    "God uses valleys to teach us",
    "Eager anticipation of Christ’s return"
]

# -----------------------------
# Format key verse
# -----------------------------
def format_key_verse(verse_text, chapter_ref):
    m = re.match(r'(\d+):\s*(.*)', verse_text)
    if m:
        verse_num, text = m.groups()
        return f"{text.strip()} ({chapter_ref}:{verse_num})"
    else:
        return f"{verse_text.strip()} ({chapter_ref})"

# -----------------------------
# Fix LLM JSON output
# -----------------------------
def fix_json(text):
    """
    Safely parse LLM JSON output even if scripture contains quotes.
    """
    import json
    import re

    # Normalize smart quotes and apostrophes
    cleaned = text.replace("“", "'")
    cleaned = re.sub(r'["“”]\s*(?=\()', '', cleaned)
    cleaned = re.sub(r'[\"“”]{2}', '"', cleaned)
    cleaned = re.sub(r'[“”](?=.)', "'", cleaned)
#   cleaned = cleaned.replace("”", "\"")

#    print("last char = " + cleaned[-1])
#    if cleaned.endswith("”"):
#        cleaned = cleaned[:-1] + "\""
#    else:
#        cleaned.replace("”", "'")

    # Find all "key": "value" patterns and escape inner quotes
    def escape_inner_quotes(match):
        key = match.group(1)
        value = match.group(2)
        value = value.replace('\'', '\\"')  # Escape quotes inside the value
        return f'"{key}": "{value}"'

    # Apply to all key-value pairs
    cleaned = re.sub(r'"([^"]+)":\s*"([^"]*?)"', escape_inner_quotes, cleaned)

    # Extract JSON object
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in LLM output.")

    json_text = match.group(0)

    # Parse safely
    try:
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON after fix:\n{json_text}\n\nError: {e}")






# -----------------------------
# Normalize categories and lessons
# -----------------------------
def normalize_categories(result):
    def pick_category(text):
        # Stanley 30
        for i, lesson in enumerate(CHARLES_STANLEY_30, start=1):
            if lesson.lower() in text.lower():
                return "Charles Stanley Life Principles", f"Charles Stanley Life Principle {i}", lesson
        # Doctrine
        for d in DOCTRINE_LIST:
            if d.lower() in text.lower():
                return "Doctrine", d, d
        # Growth
        for g in GROWTH_LIST:
            if g.lower() in text.lower():
                return "Christian Growth", g, g
        # Other
        return "Other", text, text

    # Main lesson
    cat, lesson_name, lesson_text = pick_category(result["main_lesson"]["lesson"])
    result["main_lesson"]["category"] = cat
    result["main_lesson"]["lesson_name"] = lesson_name
    result["main_lesson"]["lesson_text"] = lesson_text or result["main_lesson"]["lesson"]

    # Other lessons
    for l in result.get("other_lessons", []):
        cat, lesson_name, lesson_text = pick_category(l["lesson"])
        l["category"] = cat
        l["lesson_name"] = lesson_name
        l["lesson_text"] = lesson_text or l["lesson"]

    return result

# -----------------------------
# Enrich key verses from chapter
# -----------------------------
def enrich_key_verses(result, chapter_ref):
    verses = fetch_bible_chapter(chapter_ref)
    verse_map = {str(v['verse']): v['text'] for v in verses}

    def format_key_verse(kv):
        match = re.match(r'(\d+)', kv)
        if not match:
            return kv
        verse_num = match.group(1)
        text = verse_map.get(verse_num, "")
        # Escape quotes for JSON safety
        text = text.replace('"', '\\"')
        return f"{text} ({chapter_ref}:{verse_num})"

    # Main lesson
    if 'main_lesson' in result:
        kv = result['main_lesson'].get('key_verse', '')
        result['main_lesson']['key_verse'] = format_key_verse(kv)

    # Other lessons
    for lesson in result.get('other_lessons', []):
        kv = lesson.get('key_verse', '')
        lesson['key_verse'] = format_key_verse(kv)

    return result


# -----------------------------
# LLM Classification
# -----------------------------
def classify_chapter_internal(chapter_ref):
    verses = fetch_bible_chapter(chapter_ref)
    if not verses:
        raise ValueError("Chapter not found.")

    chapter_text = " ".join(f"{v['verse']}: {v['text']}" for v in verses)
    doctrine_text = "\n".join(DOCTRINE_LIST)
    growth_text = "\n".join(GROWTH_LIST)
    stanley_text = "\n".join([f"{i}. {lesson}" for i, lesson in enumerate(CHARLES_STANLEY_30, start=1)])

    prompt = f"""
    You are a Bible scholar.

    Classify the chapter {chapter_ref} into:
    - ONE main lesson
    - Up to TWO other lessons

    Each lesson must include:
    - category (Charles Stanley 30 Life Principles / Doctrine / Christian Growth /  Other)
    - match category as per following precedence: Charles Stanley 30 Life Principles, Doctrine, Christian Growth, Other
    - lesson (text from the list item)
    - ONE key verse (must be from the chapter and must directly support the lesson)

    IMPORTANT RULES:
    1. The key verse must clearly and explicitly support the lesson stated.
    2. Do NOT reuse the same lesson or the same key verse for multiple lessons.
    3. Only choose a Charles Stanley Life Principle if the chapter clearly teaches that principle.
       Do NOT force a match.
    4. If no verse in the chapter clearly supports a lesson, do NOT include that lesson.
    5. Avoid vague or generic theology. The verse must prove the lesson.

    Category sources:

    Doctrine:
    {doctrine_text}

    Christian Growth:
    {growth_text}

    Charles Stanley 30 Life Principles:
    {stanley_text}

    Return ONLY valid JSON. Example format:
    {{
      "main_lesson": {{
          "category": "...",
          "lesson": "...",
          "key_verse": "..."
      }},
      "other_lessons": [
          {{
              "category": "...",
              "lesson": "...",
              "key_verse": "..."
          }}
      ]
    }}

    Chapter text:
    \"\"\"{chapter_text}\"\"\"
    """

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You are a precise theological classifier. Output strict JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    raw_output = response.choices[0].message.content.strip()
    result = fix_json(raw_output)
    result = enrich_key_verses(result, chapter_ref)
    result = normalize_categories(result)
    return result

# -----------------------------
# HTML Template
# -----------------------------
HTML_TEMPLATE = """
<!doctype html>
<html>
<head>
  <title>Bible Chapter Classifier</title>
  <style>
    body { font-family: Arial; margin: 40px; }
    .card { border: 1px solid #ccc; padding: 15px; margin: 10px 0; border-radius: 8px; }
    .Doctrine { color: blue; font-weight: bold; }
    .Christian_Growth { color: green; font-weight: bold; }
    .Other { color: gray; font-weight: bold; }
    .Charles_Stanley { color: purple; font-weight: bold; font-style: italic; }
  </style>
</head>
<body>
<h1>Bible Chapter Classifier</h1>

<form method="post">
  Chapter: <input type="text" name="chapter" value="{{ request.form.get('chapter','') }}">
  <input type="submit" value="Classify">
</form>

{% if error %}
<p style="color:red;">{{ error }}</p>
{% endif %}

{% if result %}
<div class="card">
  <p>Category:
    {% if result.main_lesson.category == "Charles Stanley Life Principles" %}
      <span class="Charles_Stanley">{{ result.main_lesson.lesson_name }}</span>
    {% else %}
      <span class="{{ result.main_lesson.category.replace(' ', '_') }}">{{ result.main_lesson.category }}</span>
    {% endif %}
  </p>
  <h3>Main Lesson: {{ result.main_lesson.lesson_text }}</h3>
  <p><strong>Key Verse:</strong> {{ result.main_lesson.key_verse }}</p>
</div>

{% for l in result.other_lessons %}
<div class="card">
  <p>Category:
    {% if l.category == "Charles Stanley Life Principles" %}
      <span class="Charles_Stanley">{{ l.lesson_name }}</span>
    {% else %}
      <span class="{{ l.category.replace(' ', '_') }}">{{ l.category }}</span>
    {% endif %}
  </p>
  <h4>Other Lesson: {{ l.lesson_text }}</h4>
  <p><strong>Key Verse:</strong> {{ l.key_verse }}</p>
</div>
{% endfor %}
{% endif %}
</body>
</html>
"""

# -----------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None
    if request.method == "POST":
        chapter = request.form.get("chapter", "").strip()
        try:
            result = classify_chapter_internal(chapter)
        except Exception as e:
            error = str(e)
    return render_template_string(HTML_TEMPLATE, result=result, error=error)

# -----------------------------
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
