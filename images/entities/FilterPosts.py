import logging, pprint
import pandas as pd

from helpers import ddb as ddb_helpers
from entities.GatherPosts import GatherPosts

pp = pprint.PrettyPrinter(indent=2, compact=True, width=80)


class FilterPosts:
    def __init__(self, ddb, subreddits_group, date, logger) -> None:
        self.df_top = pd.DataFrame()
        self.df_filtered = pd.DataFrame()
        self.subreddits_group = subreddits_group
        self.logger = logger
        self.ddb = ddb
        self.date = date
        self.posts_arr = []
        self.gather_posts = None

    def get_posts_of_subreddits_from_db(self, TableName):
        transact_items = []

        for subreddit in self.subreddits_group:
            self.gather_posts = GatherPosts(subreddit, self.logger)

            # If we want posts of a different date, in the constructor
            # we would pass that specific date and below will fetch all posts of that date
            # This would handle the use case for daily uploads for the past.
            self.gather_posts.date = self.date

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

        # pp.pprint(GatherPosts.deserialize_from_item(subreddit_items[0]))

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

    def filter_best_posts(self, VIDEO_URLS_TABLE_NAME):
        total_duration = 0
        for index, row in self.df_top.iterrows():
            duration = row["duration"]
            post_has_awards = True if row["total_awards_received"] > 0 else False

            # TODO: Change this in production
            if total_duration < 600 or post_has_awards:
                # if post_has_awards:
                # if not self.__is_old_post(row["url"], VIDEO_URLS_TABLE_NAME):
                total_duration += row["duration"]
                self.df_filtered = self.df_filtered.append(row)

    def is_old_post(self, post, TABLE_NAME):
        pk = "-".join(self.subreddits_group) + "-" + self.date
        sk = post["url"]
        kwargs = {"TableName": TABLE_NAME, "Key": {"PK": {"S": pk}, "SK": {"S": sk}}}
        return (
            True
            if ddb_helpers.item_exists(ddb=self.ddb, logger=self.logger, **kwargs)
            else False
        )

    def get_filtered_posts(self):
        return self.df_filtered.to_dict("records")
