from datetime import datetime
import pprint
from helpers import ddb as ddb_helpers

pp = pprint.PrettyPrinter(indent=2, compact=True, width=80)


class GatherPosts:
    post_keys_to_keep = [
        "title",
        "url",
        "upvote_ratio",
        "ups",
        "author",
        "name",
        "total_awards_received",
    ]

    def __init__(self, subreddit, logger) -> None:
        self.subreddit = subreddit
        self.date = str(datetime.today().date())  ## Of the format yyyy-mm-dd
        self.total_duration = 0
        self.urls = []
        self.latest_post = None
        self.eligible_posts = []
        self.logger = logger

    def key(self) -> dict:
        """Returns a dictionary with date as PK, subreddit as SK.

        Returns:
            Dict: Containing serialized subreddit and date
        """

        return {
            "PK": GatherPosts.__serialize_date(self.date),
            "SK": GatherPosts.__serialize_subreddit(self.subreddit),
        }

    def serialize_to_item(self):
        """Serializes member variable data of this object for the access pattern:
        date-Partition Key
        subreddit- Sort Key

        Returns:
            Dict: Ready to be used by boto3 to insert item into DynamoDB.
        """
        item = self.key()
        item["posts"] = GatherPosts.__serialize_posts(self.eligible_posts)
        # self.logger.info("Serialized item successfully")
        # self.logger.info(pp.pformat(item))
        return item

    @staticmethod
    def __removed_post_is_worthy(post):
        if post["removed_by"] or post["removal_reason"]:
            if post["num_comments"] > 5 and post["score"] > 10:
                return True
            else:
                return False

        return True

    @staticmethod
    def __is_eligible(post):

        if post["over_18"] or post["stickied"]:
            return False

        if (
            post["is_video"]
            or "preview" in post
            and "reddit_video_preview" in post["preview"]
            and post["preview"]["reddit_video_preview"]["is_gif"]
        ):
            if post["total_awards_received"] > 0:
                return True

            if post["ups"] > 0 and post["num_comments"] > 0:
                return True

        # elif (
        #     "preview" in post
        #     and "reddit_video_preview" in post["preview"]
        #     and post["preview"]["reddit_video_preview"]["is_gif"]
        # ):
        #     return True

        return False

    def parse_posts(self, posts):
        """Parse posts and insert into a dataframe.
        The last parsed post will updated in a member variable.

        Args:
            posts (list): List of posts from reddit API
        """
        posts = posts["data"]["children"]
        self.logger.info(f"For {self.subreddit} on date: {self.date}")
        duration = 0
        for post in posts:
            post = post["data"]
            self.latest_post = post
            print(f'Latest post has the title: {post["title"]}')
            if GatherPosts.__is_eligible(post) and GatherPosts.__removed_post_is_worthy(
                post
            ):

                temp = {key: post[key] for key in GatherPosts.post_keys_to_keep}

                # Have to handle duration seperately here and
                # in __serialize_post() because its deeply nested.
                # Duration key is stored in different places depending on whether the post is a video or a gif.
                duration = (
                    int(post["media"]["reddit_video"]["duration"])
                    if post["is_video"]
                    else int(post["preview"]["reddit_video_preview"]["duration"])
                )

                temp["duration"] = duration
                self.eligible_posts.append(temp)

                # self.total_duration += duration
                # self.logger.info(
                #     f"Post:\nTitle: {post['title']}\nDuration: {duration}s\nwas added to eligible posts\n"
                # )

        # self.logger.info("Eligible posts are ")
        # self.logger.info(pp.pformat(self.eligible_posts))
        self.logger.info(
            f"Total duration for {self.subreddit} subreddit on {self.date} is {self.total_duration}\n"
        )

    @staticmethod
    def __serialize_posts(posts):
        serialized_posts = {"L": [GatherPosts.__serialize_post(post) for post in posts]}
        return serialized_posts

    @staticmethod
    def deserialize_from_item(serialized_item):
        deserialized_item = {}

        for key, value in serialized_item.items():
            for _key, _value in value.items():
                deserialized_item[key] = ddb_helpers.deserialize_piece_of_item(
                    _key, _value
                )

        return deserialized_item

    @staticmethod
    def __serialize_post(post):
        serialized_post = {"M": {}}

        for key in GatherPosts.post_keys_to_keep:
            serialized_post["M"][key] = {
                ddb_helpers.get_datatype(post[key]): str(post[key])
            }

        serialized_post["M"]["duration"] = {
            ddb_helpers.get_datatype(post["duration"]): str(post["duration"])
        }

        return serialized_post

    @staticmethod
    def __serialize_subreddit(subreddit):
        return {"S": subreddit}

    @staticmethod
    def __serialize_date(date):
        return {"S": date}

    @staticmethod
    def deserialize_PK_SK_count(item):
        deserialized_item = {}
        for key, value in item.items():
            for _key, _value in value.items():
                deserialized_item[key] = _value
        return deserialized_item
