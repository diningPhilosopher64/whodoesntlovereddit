import requests, logging, pprint
from helpers.Exceptions import InvalidCredentialsProvidedException
from helpers import ddb as ddb_helpers

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
        params = {"TableName": REDDIT_ACCOUNTS_TABLE_NAME, "Key": self.key()}
        item = ddb_helpers.get_item(ddb=self.ddb, logger=self.logger, **params)
        deserialized_item = RedditAccount.deserialize_item(item)

        self.client_id = deserialized_item["personal_use_script"]
        self.secret_key = deserialized_item["secret_key"]
        self.username = deserialized_item["username"]
        self.password = deserialized_item["password"]
        self.data["username"] = self.username
        self.data["password"] = self.password
        self.logger.info("Fetched and updated account details")
        self.logger.debug("Fetched and updated the following account details:\n")
        self.logger.debug(pp.pformat(deserialized_item))

    @staticmethod
    def deserialize_item(item):
        deserialized_item = {}
        for key, value in item.items():
            for _key, _value in value.items():
                deserialized_item[key] = ddb_helpers.deserialize_piece_of_item(
                    _key, _value
                )

        return deserialized_item

    def authenticate_with_api(self):
        self.auth = requests.auth.HTTPBasicAuth(self.client_id, self.secret_key)
        self.logger.info("Configured authentication for reddit account")

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

        self.logger.info("Successfully fetched access_token and updated headers")
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
            self.logger.error(f"URL to fetch posts from: {url}\n")
            self.logger.error("params passed were:\n")
            self.logger.error(pp.pformat(params))
