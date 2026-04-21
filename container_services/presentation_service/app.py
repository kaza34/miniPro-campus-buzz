from flask import Flask, render_template
import os

app = Flask(__name__)

WORKFLOW_URL = os.environ.get('WORKFLOW_URL', '')

@app.route('/')
def index():
    return render_template('index.html', workflow_url=WORKFLOW_URL)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port)