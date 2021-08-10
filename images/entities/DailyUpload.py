from datetime import datetime


class DailyUpload:
    def __init__(self, subreddit) -> None:
        self.subreddit = subreddit
        self.date = str(datetime.today().date())  ## Of the format yyyy-mm-dd
        self.total_duration = 0
        self.urls = []

    def date_subreddit_key(self) -> dict:
        return {"PK": self.__serialize_date(), "SK": self.__serialize_subreddit()}

    def subreddit_date_key(self) -> dict:
        return {"PK": self.__serialize_subreddit(), "SK": self.__serialize_date()}

    def serialize_date_subreddit(self):
        item = self.date_subreddit_key()
        item["urls"] = self.__serialize_urls()
        return item

    def serialize_subreddit_date(self):
        item = self.subreddit_date_key()
        item["total_duration"] = self.__serialize_total_duration()
        return item

    def __serialize_urls(self):
        serialized_urls = {"L": [{"S": url} for url in self.urls]}
        return serialized_urls

    def __serialize_subreddit(self):
        return {"S": self.subreddit}

    def __serialize_total_duration(self):
        return {"N": str(self.total_duration)}

    def __serialize_date(self):
        return {"S": self.date}

    def deserialize_date_subreddit(item):
        pass

    def deserialize_subreddit_date(item):
        pass

    def deserialize_subreddit_postID(item):
        pass
