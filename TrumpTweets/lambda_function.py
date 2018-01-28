import boto3
from boto3.dynamodb.conditions import Key
import twitter
import os
import json
from base64 import b64decode


#Handle encrypted ENV variables
ENCRYPTED = os.environ['CUST_KEY']
ENCRYPTED2 = os.environ['CUST_SEC']
customer_key = boto3.client('kms').decrypt(CiphertextBlob=b64decode(ENCRYPTED))['Plaintext']
customer_secret = boto3.client('kms').decrypt(CiphertextBlob=b64decode(ENCRYPTED2))['Plaintext']

#Create Twitter connection
token = twitter.oauth2_dance(customer_key, customer_secret)
t = twitter.Twitter(auth=twitter.OAuth2(bearer_token=token))

#Create Dynamo globals
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
table = dynamodb.Table('Tweets')

#Boto lambda client
lambda_client = boto3.client('lambda')


def check_tweets(number):
    
    res = t.statuses.user_timeline(screen_name='realDonaldTrump', count=number)
    return res


def check_last(source_user):
    
    response = table.query(
        KeyConditionExpression=Key('source_user').eq(source_user),
        ScanIndexForward=False,
        Limit=1)
    return response["Items"][0]["id"]


def handle_new(to_add):
    
    print("calling lambda with payload: ", end=" ")
    print(to_add)
    
    response = lambda_client.invoke(
        FunctionName='arn:aws:lambda:us-west-2:323743701987:function:cloud9-TrumpTweets-GetTranslation-1909MYAK1W4MJ',
        InvocationType='Event',
        Payload=json.dumps(to_add))
    
    return_msg = "Processed " + str(len(to_add))
    print(return_msg)
    
    
def main_handler(event, context):
    
    res = check_tweets(1)
    last_tweet = check_last('trump')
    
    print(res[0]["id"])
    
    if res[0]["id"] == last_tweet:
    
        print('Up to date')
        print('Twitter ID: ', end=' ***')
        print(res[0]["id"], end='*** matched DB tweet ***')
        print(last_tweet, end='***\n')
        return("Nothing new here boss.")
    
    elif res[0]["id"] != last_tweet:
    
        print("DB didn't match twitter. Checking next 5.")
        print("Twitter's most recent is %i" % res[0]["id"])
        print("DB last tweet is %i" % last_tweet)
        res = check_tweets(5)
    
    else:
    
        print('Something is terribly wrong')
        quit()
    
    
    to_add = []
    
    
    for i in res:
    
        if i["id"] == last_tweet:
            print('Up to date - finished adding tweets to be processed.')
            break
    
        elif i["id"] != last_tweet:
            print("Adding %i to be processed" % i["id"])
            to_add.append(i["id"])
    
        else:
            print('Something is wrong trying to find the last tweet processed')
            print(last_tweet)
            print(res)
    
    handle_new(to_add)