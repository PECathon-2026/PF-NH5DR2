"""
PrivacyLens Demo Server
Simple Flask app for PII detection demo
"""
from flask import Flask, render_template, request, jsonify
import sys
sys.path.insert(0, 'F:/Hackthon')
from src.detection.ensemble import ensemble_detect, redact_text

app = Flask(__name__)

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>PrivacyLens - PII Detection Demo</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            .container { background: #f5f5f5; padding: 30px; border-radius: 10px; }
            h1 { color: #333; }
            textarea { width: 100%; height: 150px; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
            button { background: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
            button:hover { background: #45a049; }
            .result { margin-top: 20px; padding: 15px; background: white; border-radius: 5px; }
            .entity { display: inline-block; background: #ffeb3b; padding: 2px 6px; margin: 2px; border-radius: 3px; }
            .redacted { background: #f44336; color: white; padding: 2px 6px; margin: 2px; border-radius: 3px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔒 PrivacyLens</h1>
            <p>AI-Powered PII Detection & Redaction</p>
            
            <textarea id="inputText" placeholder="Enter text with PII (cards, phones, emails, OTPs, PAN, IP, URLs)...">
My card number is 4532 0151 1283 0366 and my phone is 9876543210.
OTP for login is 126225 sent to 9876543210.
Contact John at john@example.com or visit https://example.com.
IP: 192.168.1.1, PAN: ABCDE1234F
            </textarea>
            <br><br>
            <button onclick="detectPII()">Detect & Redact PII</button>
            
            <div id="result" class="result" style="display:none;">
                <h3>Detected Entities:</h3>
                <div id="entities"></div>
                <h3>Redacted Text:</h3>
                <div id="redacted"></div>
            </div>
        </div>
        
        <script>
            async function detectPII() {
                const text = document.getElementById('inputText').value;
                const response = await fetch('/api/detect', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: text })
                });
                const data = await response.json();
                
                const entitiesDiv = document.getElementById('entities');
                entitiesDiv.innerHTML = data.entities.map(e => 
                    `<span class="entity">${e.type}: ${e.text}</span>`
                ).join('');
                
                document.getElementById('redacted').innerHTML = 
                    `<pre>${data.redacted}</pre>`;
                
                document.getElementById('result').style.display = 'block';
            }
        </script>
    </body>
    </html>
    '''

@app.route('/api/detect', methods=['POST'])
def detect():
    data = request.get_json()
    text = data.get('text', '')
    
    entities = ensemble_detect(text)
    redacted = redact_text(text, entities)
    
    return jsonify({
        'entities': entities,
        'redacted': redacted,
        'count': len(entities)
    })

if __name__ == '__main__':
    print("Starting PrivacyLens Demo Server...")
    print("Open http://localhost:5000 in your browser")
    app.run(host='0.0.0.0', port=5000, debug=True)
