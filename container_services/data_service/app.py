from flask import Flask, request, jsonify
import uuid
import os

app = Flask(__name__)

# In-memory storage (replace with TableStore / RDS for production)
db = {}

@app.route('/event', methods=['POST'])
def create_event():
    data = request.json
    event_id = str(uuid.uuid4())
    record = {
        'eventId': event_id,
        'title': data.get('title'),
        'description': data.get('description'),
        'location': data.get('location'),
        'date': data.get('date'),
        'organizer': data.get('organizer'),
        'status': 'SUBMITTED',
        'category': None,
        'priority': None,
        'note': None
    }
    db[event_id] = record
    return jsonify({'event_id': event_id, 'record': record}), 201

@app.route('/event/<event_id>', methods=['GET'])
def get_event(event_id):
    record = db.get(event_id)
    if not record:
        return jsonify({'error': 'Event not found'}), 404
    return jsonify(record)

@app.route('/event/<event_id>', methods=['PUT'])
def update_event(event_id):
    if event_id not in db:
        return jsonify({'error': 'Event not found'}), 404
    data = request.json
    allowed_fields = ['status', 'category', 'priority', 'note']
    for field in allowed_fields:
        if field in data:
            db[event_id][field] = data[field]
    return jsonify(db[event_id])

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5003))
    app.run(host='0.0.0.0', port=port)