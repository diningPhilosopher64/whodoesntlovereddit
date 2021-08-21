import logging, pprint
import pandas as pd

from helpers import ddb as ddb_helpers
from entities.GatherPosts import GatherPosts

pp = pprint.PrettyPrinter(indent=2, compact=True, width=80)


class FilterPosts:
    def __init__(self, ddb, subreddit_group, logger) -> None:
        self.df_top = pd.DataFrame()
        self.df_filtered = pd.DataFrame()
        self.subreddit_group = subreddit_group
        self.logger = logger
        self.ddb = ddb
        self.posts_arr = []
        self.gather_post = None

    def get_posts_of_subreddits_from_db(self, TableName):
        transact_items = []

        for subreddit in self.subreddit_group:
            self.gather_posts = GatherPosts(subreddit, self.logger)
            transact_item = {
                "Get": {
                    "TableName": TableName,
                    "Key": self.gather_posts.key(),
                }
            }

            transact_items.append(transact_item)

        kwargs = {"TransactItems": transact_items}

        subreddit_items = ddb_helpers.transact_get_items(
            ddb=self.ddb, logger=self.logger, **kwargs
        )

        self.posts_arr = [
            GatherPosts.deserialize_from_item(item)["posts"] for item in subreddit_items
        ]

    def marshall_and_sort_posts(self):
        for posts in self.posts_arr:
            for post in posts:
                self.df_top = self.df_top.append(
                    {
                        "title": post["title"],
                        "upvote_ratio": post["upvote_ratio"],
                        "ups": post["ups"],
                        "total_awards_received": post["total_awards_received"],
                        "url": post["url"],
                        "name": post["name"],
                        "author": post["author"],
                        "duration": post["duration"],
                    },
                    ignore_index=True,
                )

        self.df_top = self.df_top.sort_values(
            ["ups", "total_awards_received", "upvote_ratio"], ascending=False, axis=0
        )

    def filter_best_posts(self):
        total_duration = 0
        for index, row in self.df_top.iterrows():
            duration = row["duration"]
            has_awards = True if row["total_awards_received"] > 0 else False

            if total_duration < 600 or has_awards:
                total_duration += row["duration"]
                self.df_filtered = self.df_filtered.append(row)

    def get_filtered_posts(self):
        return self.df_filtered.to_dict("records")
