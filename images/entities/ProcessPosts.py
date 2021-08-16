from multiprocessing import Pool
from subprocess import Popen, PIPE
from time import time

import logging, pprint

pp = pprint.PrettyPrinter(indent=2, compact=True, width=80)


class ProcessPosts:
    def __init__(self, subreddit, posts, logger):
        self.subreddit = subreddit
        self.posts = posts
        self.download_cmd = [
            "youtube-dl",
            "-f",
            "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "placeholder_url",
            "-o",
            "placeholder_title",
        ]
        self.download_processes = []
        self.logger = logger
        self.download_processes_logs = []
        self.tasks = {}
        self.logger.info("Initialized object")

    def download_videos_from_posts(self):
        start = time()
        with Pool(len(self.posts)) as p:
            p.map(download_video_from_post, self.posts)
        end = time()

        self.logger.info(
            f"Time taken to download {len(self.posts)} videos from {self.subreddit} is {round(end-start, 2)}s"
        )


def download_video_from_post(post):
    logger = logging.getLogger()
    download_cmd = [
        "youtube-dl",
        "-f",
        "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "placeholder_url",
        "-o",
        "placeholder_title",
    ]

    download_cmd[3] = post["url"]
    download_cmd[5] = post["title"]
    process = Popen(download_cmd, stderr=PIPE)
    _, stderr = process.communicate()

    if stderr:
        logger.error("Failed to download the post:\n")
        logger.error(pp.pformat(post))
        logger.error("Failed with error")
        logger.error(pp.pformat(stderr.decode("utf-8")))
    else:
        logger.info("Successfully downloaded the post:\n")
        logger.info(pp.pformat(post))
