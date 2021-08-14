from datetime import datetime

# import pandas as pd

import ddb_helpers


class DailyUpload:
    post_keys_to_keep = [
        "title",
        "url",
        "upvote_ratio",
        "ups",
        "author",
        "name",
        "total_awards_received",
    ]

    def __init__(self, subreddit) -> None:
        self.subreddit = subreddit
        self.date = str(datetime.today().date())  ## Of the format yyyy-mm-dd
        self.total_duration = 0
        self.urls = []
        # self.df_top = pd.DataFrame()
        self.latest_post = None
        self.eligible_posts = []

    # Renamed from date_subreddit_key()
    def key(self) -> dict:
        """Returns a dictionary with date as PK, subreddit as SK.

        Returns:
            Dict: Containing serialized subreddit and date
        """

        return {
            "PK": DailyUpload.__serialize_date(self.date),
            "SK": DailyUpload.__serialize_subreddit(self.subreddit),
        }

    # def subreddit_date_key(self) -> dict:
    #     """Returns a dictionary with subreddit as PK date as SK.

    #     Returns:
    #         Dict: Containing serialized subreddit and date.
    #     """
    # return {"PK": self.__serialize_subreddit(), "SK": self.__serialize_date()}

    # Renamed from serialize_date_subreddit()
    def serialize_to_item(self):
        """Serializes member variable data of this object for the access pattern:
        date-Partition Key
        subreddit- Sort Key

        Returns:
            Dict: Ready to be used by boto3 to insert item into DynamoDB.
        """
        item = self.key()
        item["posts"] = DailyUpload.__serialize_posts(self.eligible_posts)
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
        if post["is_video"] and not post["over_18"] and not post["stickied"]:
            if post["total_awards_received"] > 0:
                return True

            if post["ups"] > 0 and post["num_comments"] > 0:
                return True

        return False

    def parse_posts(self, posts):
        """Parse posts and insert into a dataframe.
        The last parsed post will updated in a member variable.

        Args:
            posts (list): List of posts from reddit API
        """
        posts = posts["data"]["children"]
        for post in posts:
            post = post["data"]
            self.latest_post = post

            if DailyUpload.__is_eligible(post) and DailyUpload.__removed_post_is_worthy(
                post
            ):

                temp = {key: post[key] for key in DailyUpload.post_keys_to_keep}
                self.eligible_posts.append(temp)
                self.total_duration += int(post["media"]["reddit_video"]["duration"])

    @staticmethod
    def __serialize_posts(posts):
        serialized_posts = {"L": [DailyUpload.__serialize_post(post) for post in posts]}

        return serialized_posts

    @staticmethod
    def __serialize_post(post):
        serialized_post = {"M": {}}

        for key in DailyUpload.post_keys_to_keep:
            serialized_post["M"][key] = {
                ddb_helpers.get_datatype(post[key]): str(post[key])
            }

        return serialized_post

    @staticmethod
    def __serialize_subreddit(subreddit):
        return {"S": subreddit}

    @staticmethod
    def __serialize_date(date):
        return {"S": date}

    def deserialize_date_subreddit(item):
        pass

    @staticmethod
    def deserialize_PK_SK_count(item):
        deserialized_item = {}
        for key, value in item.items():
            for _key, _value in value.items():
                deserialized_item[key] = _value
        return deserialized_item

    def deserialize_subreddit_postID(item):
        pass


# self.df_top = self.df_top.append(
#     {
#         "title": post["title"],
#         "upvote_ratio": post["upvote_ratio"],
#         "ups": post["ups"],
#         "downs": post["downs"],
#         "score": post["score"],
#         "url": post["url"],
#     },
#     ignore_index=True,
# )

# def sort_and_update_urls(self):
#     self.df_top = self.df_top.sort_values(
#         ["score", "total_awards_received", "ups", "upvote_ratio"],
#         ascending=False,
#         axis=0,
#     )

# self.urls = self.urls + self.df_top["url"].tolist()

# def serialize_subreddit_date(self):
#     item = self.subreddit_date_key()
#     item["total_duration"] = self.__serialize_total_duration()
#     return item

# def __serialize_urls(self):
#     serialized_urls = {"L": [{"S": url} for url in self.urls]}
#     return serialized_urls

#  post["title"],
#                     post["upvote_ratio"],
#                     post["ups"],
#                     post["score"],
#                     post["url"],
#                     post["author"],
