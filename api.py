import os
import json
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes


# Health check endpoint
@app.route("/health")
def health_check():
    return jsonify({"status": "healthy"})


def send_to_webhook(data, webhook_url):
    """
    Send the processed data to a webhook URL
    """
    try:
        response = requests.post(webhook_url, json=data)
        response.raise_for_status()  # Raise an exception for bad status codes
        return True
    except requests.exceptions.RequestException as e:
        print(f"Webhook error: {str(e)}")
        return False


@app.route("/ask", methods=["POST"])
def ask_manka():
    request_data = request.get_json()

    if not request_data or "expenses" not in request_data:
        return jsonify({"error": "No message provided"}), 400

    user_message = request_data["expenses"]

    completion = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[
            {
                "role": "system",
                "content": 'today is Tue Dec 3 2024, Extract transaction details from ${msg} using this JSON Schema:\n{\n  "type": "object",\n  "properties": {\n    "amount": {\n      "type": "number",\n      "minimum": 0.01,\n      "description": "The amount of the expense (positive number)"\n    },\n    "date": {\n      "type": "string",\n      "format": "date",\n      "description": "The date of the expense (YYYY-MM-DD format)"\n    },\n    "category": {\n      "type": "string",\n      "description": "The category of the expense (e.g., Groceries, Rent)"\n    },\n    "description": {\n      "type": "string",\n      "description": "Optional description of the expense"\n    },\n    "transaction_id": {\n      "type": "string",\n      "description": "Optional transaction ID of the expense"\n    },\n    "payment_method": {\n      "type": "string",\n      "enum": [\n        "Cash",\n        "Bank Card",\n        "Mobile Money",\n        "Other"\n      ],\n      "description": "Optional payment method for the expense"\n    }\n  }\n}',
            },
            {"role": "user", "content": user_message},
        ],
        temperature=1,
        max_tokens=1024,
        top_p=1,
        stream=False,
        response_format={"type": "json_object"},
        stop=None,
    )
    # Get the response content
    response_content = completion.choices[0].message.content

    # Return the actual response from the model
    # return jsonify(completion.choices[0].message.content)
    # return completion.choices[0].message.content
    # Send to webhook
    webhook_success = send_to_webhook(
        {"original_message": user_message, "processed_data": response_content},
        "https://app.openfn.org/i/707fb77f-6814-4bfe-8346-3c285724e6c2",
    )

    formatted_message = format_response_message(response_content)

    # Return both the processed data and webhook status
    return jsonify(
        {
            "text": formatted_message,
            "data": response_content,
            "webhook_delivered": webhook_success,
        }
    )


def format_response_message(json_data):
    """
    Format the JSON response into a readable message
    """
    try:
        # Parse the JSON string if it's a string
        if isinstance(json_data, str):
            data = json.loads(json_data)
        else:
            data = json_data

        # Create the formatted message
        message = (
            f"*Manka Magic 🪄...*\n\n"
            f"*Amount:* `{data.get('amount', 'N/A')}`\n"
            f"*Category:* `{data.get('category', 'N/A')}`\n"
            f"*Description:* `{data.get('description', 'N/A')}`\n"
            f"*Payment Method:* `{data.get('payment_method', 'N/A')}`\n"
            f"*Date:* `{data.get('date', 'N/A')}`\n"
            f"*Transaction ID:* `{data.get('transaction_id', 'N/A')}`"
        )
        return message
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {str(e)}")
        return "Error formatting response"


# Main routes
@app.route("/api/v1/")
def hello_world():
    return jsonify({"message": "Welcome to the API", "version": "1.0.0"})


# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5500, debug=True)
