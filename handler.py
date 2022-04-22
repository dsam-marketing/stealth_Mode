import os
import json
import logging
import base64
import boto3
import mailparser
from watson_emotion_score import run

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.resource('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(f"Master-{os.environ['STAGE']}")


def extract_attachment_and_body(message_id):
    """
    Extract an attachment and body from the email in email bucket and store it attachment bucket

    Returns key of attachment object and body
    """
    # 1. Read email from S3 bucket
    bucket_name = os.environ['BUCKET']
    email_object = s3.Object(bucket_name, f'{message_id}')
    body = email_object.get()['Body'].read()
    logger.info('Got read email object of messageId: %s from bucket', message_id)

    # 2. Try to extract an attachment from email
    mail = mailparser.parse_from_bytes(body)
    result = {'body': mail.body}

    if mail.attachments and len(mail.attachments) > 0:
        attachment = mail.attachments[0]
        payload = attachment['payload']
        payload = base64.b64decode(payload)
        logger.info('Parsed email and extracted attachment')

        # 3. Store an attachment to S3 bucket
        attachment_bucket = os.environ['ATTACHMENT_BUCKET']
        key = f"{message_id}-{attachment['filename']}"
        attachment_object = s3.Object(
            attachment_bucket,
            key
        )
        attachment_object.put(Body=payload)
        logger.info('Saved attachment file: %s in bucket', key)

        result['key'] = key

    # 4. Delete email from S3 bucket
    email_object.delete()
    logger.info('Deleted email object: %s from bucket', message_id)

    return result


def analyze(event, context):
    """
    This handles incoming email
    """
    logger.info(json.dumps(event))

    try:
        # 1. Get messageId to handle
        record = event['Records'][0]
        mail = record['ses']['mail']
        message_id = mail['messageId']
        logger.info('Handling email corresponding to messageId: %s', message_id)

        # 2. Extract email subject, body, sender, date
        sender = mail['source']

        # if sender != 'dsam.marketing@gmail.com':
        if sender != 'harleyguru@outlook.com':
            return

        subject = mail['commonHeaders']['subject']
        date = mail['timestamp']

        # 3. Extract email attachment
        result = extract_attachment_and_body(message_id)
        logger.info('Extracted necessary info from email: %s', message_id)

        # 4. Analyze email body using IBM Watson
        score_dictionary = run(result['body'])
        score = max(score_dictionary['sentiment']['positif'],
                    score_dictionary['sentiment']['negatif'])

        # 5. Save parsed email to DynamoDB table including emotion score
        values = {
            ':date': date,
            ':subject': subject,
            ':sender': sender,
            ':body': result['body'],
            ':score': score,
        }
        if result['attachment']:
            values[':attachment'] = result['attachment']

        table.put_item(
            Item={
                '#date': ':date',
                '#subject': ':subject',
                '#sender': ':sender',
                '#body': ':body',
                '#attachment': ':attachment',
                '#score': ':score',
            },
            ExpressionAttributeNames={
                '#date': 'date',
                '#subject': 'subject',
                '#sender': 'sender',
                '#body': 'body',
                '#attachment': 'attachment',
                '#score': 'score',
            },
            ExpressionAttributeValues=values
        )

        logger.info('Successfully processed the email')
    except Exception as e:
        logger.error(e)
        logger.exception('Error')
