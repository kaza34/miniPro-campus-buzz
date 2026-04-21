# -*- coding: utf-8 -*-
import json
import logging
import requests
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

DATA_SERVICE_URL = os.environ.get('DATA_SERVICE_URL')


def handler(event, context):
    try:
        payload = json.loads(event)
        event_id = payload['event_id']
        update_data = {
            'status': payload['status'],
            'category': payload['category'],
            'priority': payload['priority'],
            'note': payload['note']
        }
        logger.info(f"Updating event {event_id} with {update_data}")
        
        if not DATA_SERVICE_URL:
            raise ValueError("Environment variable DATA_SERVICE_URL is not set")
        
        url = f"{DATA_SERVICE_URL}/event/{event_id}"
        resp = requests.put(url, json=update_data, timeout=5)
        resp.raise_for_status()
        
        return {'statusCode': 200}
    except Exception as e:
        logger.error(f"Update failed: {e}")
        raise