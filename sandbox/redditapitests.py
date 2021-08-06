import requests
import pandas as pd
from requests.api import head

CLIENT_ID = "AmGDABC1cxPw9EaM6yaprw"
SECRET_KEY = "Q6cBND10iDxEo2b0qETp1vBAcPepRQ"

auth = requests.auth.HTTPBasicAuth(CLIENT_ID, SECRET_KEY)

pwd = ""

with open('pwd.txt', 'r') as f:
    pwd = f.readline()

data = {
	'grant_type' : 'password',
	'username': 'shezza46',
	'password': pwd
}

headers = {'User-Agent': 'MyAPI/0.0.1'}

res = requests.post('https://www.reddit.com/api/v1/access_token', auth=auth, data=data, headers=headers)


ACCESS_TOKEN = res.json()['access_token']

headers['Authorization'] = f'bearer {ACCESS_TOKEN}'

res = requests.get('https://oauth.reddit.com/r/abruptchaos/hot', headers=headers, params={'limit': '100'})

# for post in res.json()['data']['children']:
#     print(post['data']['title'])

df = pd.DataFrame()


for post in res.json()['data']['children']:
    print(post['kind'], post['data']['title'])

    df = df.append({
		'subreddit': post['data']['subreddit'],
  		'title':post['data']['title'],
  		'selftext':post['data']['selftext'],
  		'upvote_ratio':post['data']['upvote_ratio'],
  		'ups':post['data']['ups'],
  		'downs':post['data']['downs'],
  		'score':post['data']['score'],
	}, ignore_index=True)
	
	
