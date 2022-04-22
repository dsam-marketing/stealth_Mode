# Stealth Backend

Perform text anaylysis for incoming emails to the specified email address on IBM Watson NLP and store email content with emotion score into DynamoDB table

## Prerequisites

- Python3.8
- Pipenv
- NodeJS v14 over
- Yarn
- Serverless Framework
- AWS CLI
```
$ aws configure --profile stealth # configure the credentials and region: us-east-1
```
- Configure Parameter Store

Set `SENDER` and `RECIPIENT` parameters in AWS SSM's Parameter Store console before deploying the app below.

These are environment variables for the app.

## Install 

Install dev dependencies
```
$ yarn # in root directory
```

Install dependencies for app
```
$ pipenv --three --site-packages # this creates venv for the project

$ pipenv shell # get into the venv
$ pipenv # install dependencies
```

## Deploy

```
$ sls deploy # This deployes the app to AWS
```

You might also want to deploy only updated function after you'd make some changes in `handler.py` file.
In this case, you don't have to deploy the entire app as it will take much longer time.
```
$ sls deploy -f Analyze # This is very fast deployment
```
## Teardown
```
$ sls remove # This removes all deployed resources from AWS
```