import requests, logging, pprint
import ddb_helpers
from ddb_helpers.Exceptions import InvalidCredentialsProvidedException

pp = pprint.PrettyPrinter(indent=2, compact=True, width=80)


class RedditAccount:
    def __init__(self, subreddit, ddb, logger):
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
        self.logger = logger

    def key(self):
        return {"PK": {"S": self.subreddit}}

    def fetch_and_update_account_details(self, REDDIT_ACCOUNTS_TABLE_NAME):

        item = ddb_helpers.get_item(
            ddb=self.ddb,
            TableName=REDDIT_ACCOUNTS_TABLE_NAME,
            Key=self.key(),
            logger=self.logger,
        )

        item = RedditAccount.deserialize_item(item)

        self.client_id = item["personal_use_script"]
        self.secret_key = item["secret_key"]
        self.username = item["username"]
        self.password = item["password"]
        self.data["username"] = self.username
        self.data["password"] = self.password
        self.logger.info("Fetched and updated the following account details:\n")
        self.logger.info(pp.pformat(item))

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
        try:
            # Authorise and request for access token from Reddit API
            res = requests.post(
                REDDIT_AUTH_URL, auth=self.auth, data=self.data, headers=self.headers
            )

            res = res.json()
            if "error" in res and res["error"] == 401:
                raise InvalidCredentialsProvidedException()

        except (InvalidCredentialsProvidedException, Exception):
            self.logger.error(f"Response object contains:\n")
            self.logger.error(pp.pformat(res))
            self.logger.error(
                "Invalid Credentials. The following details were provided:\n"
            )
            self.logger.error(
                f"Requests auth object:\nusername: {self.auth.username}\npassword: {self.auth.password}\n"
            )
            self.logger.error(f"Data provided in the POST request:\n")
            self.logger.error(pp.pformat(self.headers))
            self.logger.error(f"Headers present in the POST request:\n")
            self.logger.error(pp.pformat(self.headers))

        self.access_token = res["access_token"]
        self.headers["Authorization"] = f"bearer {self.access_token}"

    def fetch_posts_as_json(self, url, params={}):
        try:
            res = requests.get(url, headers=self.headers, params=params)
            return res.json()

        except Exception as err:
            self.logger.error(f"Unable to fetch posts from Reddit")
            self.logger.error("Headers used:\n")
            self.logger.error(pp.pformat(self.headers))
            self.logger.error(f"URL to fetch posts from: {url}\n"))
            self.logger.error("params passed were:\n")
            self.logger.error(pp.pformat(params))
