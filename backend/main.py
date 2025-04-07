import os
import json
from flask import Flask, request, Response, jsonify
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configure Google Generative AI
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("No GOOGLE_API_KEY found in environment variables")

genai.configure(api_key=GOOGLE_API_KEY)

# Get Gemini model
model = genai.GenerativeModel('gemini-2.0-flash')

@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({"status": "ok"})

@app.route('/process-text', methods=['POST'])
def process_text():
    """Process text with Gemini API"""
    try:
        data = request.json
        if not data or 'prompt' not in data:
            return jsonify({"error": "Missing prompt parameter"}), 400
        
        prompt = data['prompt']
        
        print("Received request:", request.json)
        # Call Gemini API
        response = model.generate_content(prompt)
        
        # Extract the text response
        text_response = response.text
        
        print(text_response)
        # Check if response contains JSON
        try:
            # Try to extract JSON if it's wrapped in code blocks
            json_match = text_response.split("```json")[1].split("```")[0].strip() if "```json" in text_response else None
            if not json_match and "```" in text_response:
                # Try generic code block
                json_match = text_response.split("```")[1].split("```")[0].strip()
            
            if json_match:
                # Parse and return the JSON
                parsed_json = json.loads(json_match)
                return jsonify(parsed_json)
            else:
                # Try parsing the whole response as JSON
                parsed_json = json.loads(text_response)
                return jsonify(parsed_json)
        except (json.JSONDecodeError, IndexError):
            # If not valid JSON, return the raw text
            return jsonify({
                "mode": "plain_text",
                "content": text_response
            })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/stream-text', methods=['POST'])
def stream_text():
    """Stream text from Gemini API"""
    try:
        data = request.json
        if not data or 'prompt' not in data:
            return jsonify({"error": "Missing prompt parameter"}), 400
        
        prompt = data['prompt']
        
        def generate():
            response = model.generate_content(prompt, stream=True)
            
            buffer = ""
            for chunk in response:
                if not chunk.text:
                    continue
                
                buffer += chunk.text
                yield f"data: {json.dumps({'chunk': chunk.text, 'buffer': buffer})}\n\n"
                
            # Send final message to indicate completion
            yield f"data: {json.dumps({'complete': True, 'final_text': buffer})}\n\n"
        
        return Response(generate(), mimetype='text/event-stream')
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Get port from environment variable or default to 5000
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)