from flask import Flask, request, jsonify
import requests
import os
from flask_cors import CORS
import json
import logging
from alibabacloud_fc_open20210406.client import Client
from alibabacloud_fc_open20210406.models import InvokeFunctionHeaders, InvokeFunctionRequest
from alibabacloud_tea_openapi.models import Config
from datetime import datetime
import config

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)
DATA_SERVICE_URL = config.DATA_SERVICE_URL
# All settings read from environment variables
# DATA_SERVICE_URL = os.environ.get('DATA_SERVICE_URL', 'http://data_service:5003')
# DATA_SERVICE_URL = os.environ.get('DATA_SERVICE_URL', 'http://localhost:5003')


ALIYUN_REGION = os.environ.get('ALIYUN_REGION', 'cn-hangzhou')
ACCESS_KEY_ID = os.environ.get('ALIYUN_ACCESS_KEY_ID')
ACCESS_KEY_SECRET = os.environ.get('ALIYUN_ACCESS_KEY_SECRET')
FC_SERVICE_NAME = os.environ.get('FC_SERVICE_NAME', 'CampusBuzzService')
FC_FUNCTION_NAME = os.environ.get('FC_FUNCTION_NAME', 'submission-event')

acs_client = None
if ACCESS_KEY_ID and ACCESS_KEY_SECRET:
    acs_client = Client(ACCESS_KEY_ID, ACCESS_KEY_SECRET, ALIYUN_REGION)
else:
    app.logger.warning("Alibaba Cloud AccessKey not configured. Function Compute invocation disabled.")

def process_event_locally(event_id, data):
    """
    Apply all validation rules and update the event record directly via Data Service.
    This replaces the cloud function logic when running locally.
    """
    # Rule 1: Completeness check
    required_fields = ['title', 'description', 'location', 'date', 'organizer']
    for field in required_fields:
        if field not in data or not data[field] or str(data[field]).strip() == '':
            update_event_record(event_id, 'INCOMPLETE', None, None,
                                'Missing required field(s).')
            return

    # Rule 2: Date format validation
    try:
        datetime.strptime(data['date'], '%Y-%m-%d')
    except ValueError:
        update_event_record(event_id, 'NEEDS REVISION', None, None,
                            'Invalid date format. Expected YYYY-MM-DD.')
        return

    # Rule 3: Description length
    if len(data['description']) < 40:
        update_event_record(event_id, 'NEEDS REVISION', None, None,
                            'Description must be at least 40 characters long.')
        return

    # Rule 4: Category assignment
    text = (data['title'] + ' ' + data['description']).lower()
    category = 'GENERAL'
    if any(kw in text for kw in ['career', 'internship', 'recruitment']):
        category = 'OPPORTUNITY'
    elif any(kw in text for kw in ['workshop', 'seminar', 'lecture']):
        category = 'ACADEMIC'
    elif any(kw in text for kw in ['club', 'society', 'social']):
        category = 'SOCIAL'

    # Rule 5: Priority mapping
    priority_map = {
        'OPPORTUNITY': 'HIGH',
        'ACADEMIC': 'MEDIUM',
        'SOCIAL': 'NORMAL',
        'GENERAL': 'NORMAL'
    }
    priority = priority_map[category]

    # Rule 6: Approved
    update_event_record(event_id, 'APPROVED', category, priority,
                        'Event has been approved.')



def update_event_record(event_id, status, category, priority, note):
    """Directly update the event via Data Service REST API."""
    try:
        url = f"{DATA_SERVICE_URL}/event/{event_id}"
        payload = {
            'status': status,
            'category': category,
            'priority': priority,
            'note': note
        }
        resp = requests.put(url, json=payload, timeout=5)
        resp.raise_for_status()
        app.logger.info(f"Event {event_id} updated locally: {status}")
    except Exception as e:
        app.logger.error(f"Failed to update event {event_id} locally: {e}")



# @app.route('/submit', methods=['POST'])
# def submit_event():
#     form_data = request.json
#
#     # Step 1: Create record via Data Service
#     try:
#         resp = requests.post(f"{DATA_SERVICE_URL}/event", json=form_data, timeout=5)
#         resp.raise_for_status()
#         event_id = resp.json()['event_id']
#         app.logger.info(f"Event created: {event_id}")
#     except Exception as e:
#         app.logger.error(f"Failed to create event: {e}")
#         return jsonify({'error': 'Failed to create event'}), 500
#
#     # Step 2: Trigger Function Compute asynchronously (if configured)
#     if acs_client:
#         try:
#             invoke_request = InvokeFunctionRequest.InvokeFunctionRequest()
#             invoke_request.set_ServiceName(FC_SERVICE_NAME)
#             invoke_request.set_FunctionName(FC_FUNCTION_NAME)
#             invoke_request.set_Qualifier("LATEST")
#             invoke_request.set_headers({"X-Fc-Invocation-Type": "Async"})
#             payload = json.dumps({'event_id': event_id, 'data': form_data})
#             invoke_request.set_Payload(payload)
#
#             response = acs_client.do_action_with_exception(invoke_request)
#             app.logger.info(f"FC triggered: {response}")
#         except Exception as e:
#             app.logger.error(f"Failed to trigger FC: {e}")
#     else:
#         app.logger.warning("Skipping FC invocation (no AccessKey)")
#
#     return jsonify({'event_id': event_id}), 202
@app.route('/submit', methods=['POST'])
def submit_event():
    form_data = request.json

    # Step 1: Create record via Data Service
    try:
        resp = requests.post(f"{DATA_SERVICE_URL}/event", json=form_data, timeout=5)
        resp.raise_for_status()
        event_id = resp.json()['event_id']
        app.logger.info(f"Event created: {event_id}")
    except Exception as e:
        app.logger.error(f"Failed to create event: {e}")
        return jsonify({'error': 'Failed to create event'}), 500

    # Step 2: Process locally (apply all rules and update status)
    app.logger.info(f"Processing event locally: {event_id}")
    process_event_locally(event_id, form_data)

    # Step 3: Optionally trigger cloud function (if needed for hybrid deployment)
    if acs_client:
        try:
            invoke_headers = InvokeFunctionHeaders()
            invoke_headers.x_fc_invocation_type = 'Async'
            invoke_request = InvokeFunctionRequest(
                service_name=FC_SERVICE_NAME,
                function_name=FC_FUNCTION_NAME,
                headers=invoke_headers,
                body=json.dumps({'event_id': event_id, 'data': form_data}).encode('utf-8'),
                qualifier='LATEST'
            )
            response = acs_client.invoke_function(invoke_request)
            app.logger.info(f"FC triggered: {response}")
        except Exception as e:
            app.logger.error(f"Failed to trigger FC: {e}")
    else:
        app.logger.warning("Skipping FC invocation (no AccessKey)")

    return jsonify({'event_id': event_id}), 202

@app.route('/status/<event_id>', methods=['GET'])
def check_status(event_id):
    try:
        resp = requests.get(f"{DATA_SERVICE_URL}/event/{event_id}", timeout=5)
        resp.raise_for_status()
        return jsonify(resp.json())
    except Exception as e:
        app.logger.error(f"Failed to get status: {e}")
        return jsonify({'error': 'Event not found'}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5002))
    app.run(host='0.0.0.0', port=port)