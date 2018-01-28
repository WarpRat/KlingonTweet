import boto3
import twitter
import http.client, urllib.parse
import xml.etree.ElementTree as etree
import xml.sax.saxutils as saxutils
import time
import os
from base64 import b64decode
import re


#Handle encrypted ENV variables

ENCRYPTED = os.environ['CUST_KEY']
ENCRYPTED2 = os.environ['CUST_SEC']
ENCRYPTED3 = os.environ['TOKEN']
ENCRYPTED4 = os.environ['TOKEN_SECRET']
ENCRYPTED5 = os.environ['AZ_KEY']

in_customer_key = boto3.client('kms').decrypt(CiphertextBlob=b64decode(ENCRYPTED))['Plaintext']
in_customer_secret = boto3.client('kms').decrypt(CiphertextBlob=b64decode(ENCRYPTED2))['Plaintext']
in_token = boto3.client('kms').decrypt(CiphertextBlob=b64decode(ENCRYPTED3))['Plaintext']
in_token_secret = boto3.client('kms').decrypt(CiphertextBlob=b64decode(ENCRYPTED4))['Plaintext']
in_az_key = boto3.client('kms').decrypt(CiphertextBlob=b64decode(ENCRYPTED5))['Plaintext']

#Global twitter auth (REPLACE WITH ENV VARIALES)
t = twitter.Twitter(auth=twitter.OAuth(consumer_key=in_consumer_key, consumer_secret=in_consumer_secret, token=in_token, token_secret=in_token_secret))


#Create SNS client **REMOVE AFTER ADDING NEXT LAMBDA**

sns_client = boto3.client('sns')

dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
table = dynamodb.Table('Tweets')

def GetTranslations(to_trans):

    #Azure API info (REPLACE WITH ENV VARIABLES)
    subscriptionKey = in_az_key
    host = 'api.microsofttranslator.com'
    path = '/V2/Http.svc/GetTranslations'

    from_language = "en-us"
    to_language = "tlh"
    text = to_trans
    maxTranslations = "1"
    params = "?from=" + from_language + "&to=" + to_language + "&maxTranslations=" + maxTranslations + "&text=" + urllib.parse.quote(text)
    body = ''
    
    headers = {
		'Ocp-Apim-Subscription-Key': subscriptionKey,
		'Content-type': 'text/xml'
    }
    
    conn = http.client.HTTPSConnection(host)
    conn.request ("POST", path + params, body, headers)
    result_initial = conn.getresponse ()
    result = result_initial.read()
    result_formatted = etree.fromstring(result.decode("utf-8"))
    to_post = saxutils.unescape(result_formatted[1][0][4].text)
    
    return to_post

def get_trans_handler(tweet, context):

    print(tweet)

    for i in tweet:

        latest = t.statuses.show(_id=i, tweet_mode='extended')
        to_trans = str(latest["full_text"])
        
        clean_tt = re.search('(https://t\.co.*$)', to_trans)
        
        if clean_tt:
            clean_rem = clean_tt.group(0)
            to_trans = to_trans.replace(clean_rem, '')
        
        print("Sending %s to be translated" % to_trans)
        
        to_post = GetTranslations(to_trans)
        
        if clean_tt:
            to_post = to_post + clean_rem
        
        print("Posting %s to Titter, translated from:\n %s" % (to_post, to_trans))
        
        '''
        t.statuses.update(
                status=to_post)
        
        '''
        
        try:
            tw_response = t.statuses.update(
                status=to_post)
        except:
            print(tw_response)
            Message_Body = 'IEEE something is fucked, GO CHECK: ' + str(i) + '\n' + to_post[:50]
            sns_client.publish(
                TopicArn = 'arn:aws:sns:us-west-2:323743701987:Tweet_test',
                Message = Message_Body
                )
            break
        
        '''
        Message_Body = 'That asshole is at it again: ' + str(i) + '\n' + to_post[:50]
        sns_client.publish(
            TopicArn = 'arn:aws:sns:us-west-2:323743701987:Tweet_test',
            Message = Message_Body)
        '''    
        proc_time = int(time.time())
        ttl_time = proc_time + 604800

        response = table.put_item(
            Item={
                'source_user': 'trump',
                'proccessed_epoch': proc_time,
                'id': i,
                'ttl': ttl_time
            })
