# -*- coding: utf-8 -*-
import json
import logging
import os
from alibabacloud_fc_open20210406.client import Client
from alibabacloud_fc_open20210406.models import InvokeFunctionHeaders, InvokeFunctionRequest
from alibabacloud_tea_openapi.models import Config
# from aliyunsdkcore.client import AcsClient
# from aliyunsdkfc_open.request.v20210406 import InvokeFunctionRequest

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = os.environ.get('ALIYUN_REGION', 'cn-hangzhou')
ACCESS_KEY_ID = os.environ.get('ALIYUN_ACCESS_KEY_ID')
ACCESS_KEY_SECRET = os.environ.get('ALIYUN_ACCESS_KEY_SECRET')
PROCESSING_SERVICE = os.environ.get('PROCESSING_SERVICE', 'CampusBuzzService')
PROCESSING_FUNCTION = os.environ.get('PROCESSING_FUNCTION', 'processing')

client = Client(ACCESS_KEY_ID, ACCESS_KEY_SECRET, REGION)


def handler(event, context):
    try:
        payload = json.loads(event)
        event_id = payload.get('event_id')
        data = payload.get('data')
        logger.info(f"Received submission event: {event_id}")
        
        invoke_request = InvokeFunctionRequest.InvokeFunctionRequest()
        invoke_request.set_ServiceName(PROCESSING_SERVICE)
        invoke_request.set_FunctionName(PROCESSING_FUNCTION)
        invoke_request.set_Qualifier("LATEST")
        invoke_request.set_headers({"X-Fc-Invocation-Type": "Async"})
        processing_payload = json.dumps({'event_id': event_id, 'data': data})
        invoke_request.set_Payload(processing_payload)
        
        response = client.do_action_with_exception(invoke_request)
        logger.info(f"Processing function invoked: {response}")
        return {'statusCode': 200}
    except Exception as e:
        logger.error(f"Error in submission_event: {e}")
        raise