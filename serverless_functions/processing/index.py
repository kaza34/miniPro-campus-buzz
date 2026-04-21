# -*- coding: utf-8 -*-
import json
import logging
import os
from datetime import datetime
# from aliyunsdkcore.client import AcsClient
# from aliyunsdkfc_open.request.v20210406 import InvokeFunctionRequest
from alibabacloud_fc_open20210406.client import Client
from alibabacloud_fc_open20210406.models import InvokeFunctionHeaders, InvokeFunctionRequest
from alibabacloud_tea_openapi.models import Config

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = os.environ.get('ALIYUN_REGION', 'cn-hangzhou')
ACCESS_KEY_ID = os.environ.get('ALIYUN_ACCESS_KEY_ID')
ACCESS_KEY_SECRET = os.environ.get('ALIYUN_ACCESS_KEY_SECRET')
UPDATE_SERVICE = os.environ.get('UPDATE_SERVICE', 'CampusBuzzService')
UPDATE_FUNCTION = os.environ.get('UPDATE_FUNCTION', 'result-update')

client = Client(ACCESS_KEY_ID, ACCESS_KEY_SECRET, REGION)

def handler(event, context):
    try:
        payload = json.loads(event)
        event_id = payload['event_id']
        data = payload['data']
        logger.info(f"Processing event: {event_id}")

        # Rule 1: Completeness check
        required_fields = ['title', 'description', 'location', 'date', 'organizer']
        for field in required_fields:
            if field not in data or not data[field]:
                update_result(event_id, 'INCOMPLETE', None, None, 'Missing required fields')
                return {'statusCode': 200}

        # Rule 2: Date format validation
        try:
            datetime.strptime(data['date'], '%Y-%m-%d')
        except ValueError:
            update_result(event_id, 'DATE NEEDS REVISION', None, None, 'Invalid date format (expected YYYY-MM-DD)')
            return {'statusCode': 200}

        # Rule 3: Description length
        if len(data['description']) < 40:
            update_result(event_id, 'DESCRIPTION NEEDS REVISION', None, None, 'Description must be at least 40 characters')
            return {'statusCode': 200}

        # Rule 4: Category assignment (ordered precedence)
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
        update_result(event_id, 'APPROVED', category, priority, 'Approved')
        return {'statusCode': 200}

    except Exception as e:
        logger.error(f"Processing error: {e}")
        raise

def update_result(event_id, status, category, priority, note):
    invoke_request = InvokeFunctionRequest.InvokeFunctionRequest()
    invoke_request.set_ServiceName(UPDATE_SERVICE)
    invoke_request.set_FunctionName(UPDATE_FUNCTION)
    invoke_request.set_Qualifier("LATEST")
    invoke_request.set_headers({"X-Fc-Invocation-Type": "Async"})
    payload = json.dumps({
        'event_id': event_id,
        'status': status,
        'category': category,
        'priority': priority,
        'note': note
    })
    invoke_request.set_Payload(payload)
    response = client.do_action_with_exception(invoke_request)
    logger.info(f"Update function invoked: {response}")