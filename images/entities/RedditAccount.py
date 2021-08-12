import requests


class RedditAccount:
    def __init__(self, subreddit, ddb):
        self.subreddit = subreddit
        self.client_id = None
        self.secret_key = None
        self.username = None
        self.password = None
        self.auth = None
        self.headers = {"User-Agent": f"{subreddit}API/0.0.1"}
        self.data = {"grant_type": "password", "username": None, "password": None}
        self.access_token = None
        self.ddb = ddb

    def key(self):
        return {"PK": {"S": self.subreddit}}

    def fetch_and_update_account_details(self, REDDIT_ACCOUNTS_TABLE_NAME):
        try:
            response = self.ddb.get_item(
                TableName=REDDIT_ACCOUNTS_TABLE_NAME, Key=self.key()
            )
            item = RedditAccount.deserialize_item(response["Item"])
            self.client_id = item["personal_use_script"]
            self.secret_key = item["secret_key"]
            self.username = item["username"]
            self.password = item["password"]

        except Exception as e:
            print(f"Failed with exception: {e}")

        self.data["username"] = self.username
        self.data["password"] = self.password

    @staticmethod
    def deserialize_item(item):
        new_item = {}
        for key in item:
            new_item[key] = RedditAccount.extract_value(item[key])

        return new_item

    @staticmethod
    def extract_value(dictionary):
        data_type, value = list(dictionary.keys())[0], list(dictionary.values())[0]

        if data_type == "S":
            return value

    def authenticate_with_api(self):
        self.auth = requests.auth.HTTPBasicAuth(self.client_id, self.secret_key)

    def fetch_and_update_access_token(self, REDDIT_AUTH_URL):
        # Authorise and request for access token from Reddit API
        res = requests.post(
            REDDIT_AUTH_URL, auth=self.auth, data=self.data, headers=self.headers
        )
        self.access_token = res.json()["access_token"]
        self.headers["Authorization"] = f"bearer {self.access_token}"

    def fetch_posts_as_json(self, url, params={}):
        res = requests.get(url, headers=self.headers, params=params)
        return res.json()
