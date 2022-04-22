import os
import json
import logging
import base64
from decimal import Decimal
import boto3
import mailparser
from watson_emotion_score import run

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.resource('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(f"Master-{os.environ['STAGE']}")


def delete_email(message_id):
    """
    Delete email object from S3 bucket
    """
    # 1. Read email from S3 bucket
    bucket_name = os.environ['BUCKET']
    email_object = s3.Object(bucket_name, f'{message_id}')
    email_object.delete()
    logger.info('Deleted email object: %s from bucket', message_id)


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
    result = {}
    if mail.text_plain and isinstance(mail.text_plain, list) and len(mail.text_plain) > 0:
        result['body'] = mail.text_plain[0]

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

        result['attachment'] = key

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

        if sender != os.environ['SENDER']:
            delete_email(message_id)
            return

        subject = mail['commonHeaders']['subject']
        date = mail['timestamp']

        # 3. Extract email attachment
        result = extract_attachment_and_body(message_id)
        logger.info('Extracted necessary info from email: %s', message_id)

        # 4. Analyze email body using IBM Watson
        score = 0
        if 'body' in result:
            score_dictionary = run(result['body'])
            score = max(score_dictionary['sentiment']['positif'],
                        score_dictionary['sentiment']['negatif'])

        # 5. Save parsed email to DynamoDB table including emotion score
        item = {
            'date': date,
            'subject': subject,
            'sender': sender,
            'body': result['body'],
            'score': str(score),
        }
        if 'attachment' in result:
            item['attachment'] = result['attachment']

        item = json.loads(json.dumps(item), parse_float=Decimal)

        logger.info('Processing result:')
        logger.info(item)

        table.put_item(
            Item=item
        )

        logger.info('Successfully processed the email')
    except Exception as e:
        logger.error(e)
        logger.exception('Error')


if __name__ == '__main__':
    test_event = {
        "Records": [
            {
                "eventSource": "aws:ses",
                "eventVersion": "1.0",
                "ses": {
                    "mail": {
                        "timestamp": "2022-04-22T17:32:51.765Z",
                        "source": "harleyguru@outlook.com",
                        "messageId": "qeg6875pkpance3umhhlgdbhu48aosffidhv3jo1",
                        "destination": [
                            "sam@networkerspace.com"
                        ],
                        "commonHeaders": {
                            "returnPath": "harleyguru@outlook.com",
                            "from": [
                                "harley guru <harleyguru@outlook.com>"
                            ],
                            "date": "Fri, 22 Apr 2022 17:32:49 +0000",
                            "to": [
                                "\"sam@networkerspace.com\" <sam@networkerspace.com>"
                            ],
                            "messageId": "<BD8EB966-EDC9-4D86-8928-1D9C5F22AFC3@outlook.com>",
                            "subject": "Re: Test subject"
                        }
                    },
                }
            }
        ]
    }

    analyze(test_event, None)
