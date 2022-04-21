import json
import logging
from datetime import datetime
import base64
import boto3
import mailparser
from watson_emotion_score import run

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.resource('s3')

def extract_attachment(message_id):
    """
    Extract an attachment from email in S3 bucket and store it back
    """
    # 1. Read email from S3 bucket
    email_object = s3.Object('irrcap-projects', f'portfolios/{message_id}')
    body = email_object.get()['Body'].read()
    logger.info('Got read email object of messageId: %s from bucket', message_id)

    # 2. Extract an attachment from email
    mail = mailparser.parse_from_bytes(body)
    attachment = mail.attachments[0]
    payload = attachment['payload']
    payload = base64.b64decode(payload)
    logger.info('Parsed email and extracted attachment')

    # 3. Store an attachment to S3 bucket
    attachment_object = s3.Object(
        'irrcap-projects',
        f"portfolios/{attachment['filename']}"
    )
    attachment_object.put(Body=payload)
    logger.info('Saved attachment file in bucket')

    # 4. Delete email from S3 bucket
    email_object.delete()
    logger.info('Deleted email object from bucket')

def analyze(event):
    """
    This handles incoming email
    """
    logger.info(json.dumps(event))

    # 1. Get messageId to handle
    record = event['Records'][0]
    message_id = record['ses']['mail']['messageId']
    logger.info('Handling email corresponding to messageId: %s', message_id)

    # 2. Extract email subject, body, sender, date

    # 3. Extract attachment from email corresponding to the specific messageId
    extract_attachment(message_id)
    logger.info('Extracted attachment from email: %s', message_id)

    # 4. Analyze email body using IBM Watson

    # 5. Save parsed email to DynamoDB table including emotion score
