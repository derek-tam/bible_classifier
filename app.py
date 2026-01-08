from flask import Flask, request, jsonify
from openai import OpenAI
import os

app = Flask(__name__)

# Groq API client setup
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),  # set your env var
    base_url="https://api.groq.com/openai/v1"
)

# Allowed categories for validation
ALLOWED_CATEGORIES = ["BILLING", "TECHNICAL", "COMPLAINT", "PRAISE"]

def classify_ticket(ticket_text: str) -> str:
    """
    Calls Groq LLM to classify a ticket.
    Returns a valid category or 'HUMAN_REVIEW' if output is unexpected.
    """
    prompt = f"""
    You are a strict ticket classifier.
    Categories: BILLING, TECHNICAL, COMPLAINT, PRAISE
    Return only one of these categories.

    Ticket:
    {ticket_text}
    """

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You are a helpful classifier."},
            {"role": "user", "content": prompt}
        ]
    )

    # Extract the model's response
    category = response.choices[0].message.content.strip().upper()

    # Validate the category
    if category not in ALLOWED_CATEGORIES:
        return "HUMAN_REVIEW"

    return category

@app.route("/submit_ticket", methods=["POST"])
def submit_ticket():
    """
    Expects JSON: {"ticket": "Ticket text here"}
    """
    data = request.json
    ticket_text = data.get("ticket", "").strip()

    if not ticket_text:
        return jsonify({"error": "No ticket provided"}), 400

    # Step 1: classify ticket
    category = classify_ticket(ticket_text)

    # Step 2: route / log
    # Here we just print to console (replace with DB or queue in production)
    print(f"Ticket: {ticket_text}")
    print(f"Assigned Category: {category}")

    return jsonify({"ticket": ticket_text, "category": category})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
