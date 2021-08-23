from multiprocessing import Process, Pipe

# from subprocess import Popen, PIPE
import logging, pprint, os, youtube_dl
from time import time
from datetime import datetime

pp = pprint.PrettyPrinter(indent=2, compact=True, width=80)

from helpers import s3 as s3_helpers


class DownloadPosts:
    def __init__(self, s3, posts, bucket_name, logger, download_path="/tmp/"):
        self.posts = posts
        self.download_cmd = [
            "youtube-dl",
            "-f",
            "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "placeholder_url",
            "-o",
            "placeholder_title",
        ]
        self.download_path = download_path
        self.logger = logger
        self.s3 = s3
        self.bucket_name = bucket_name

        # self.__create_s3_bucket()

    # def __create_s3_bucket(self):
    #     try:
    #         self.s3.create_bucket(
    #             ACL="private",
    #             Bucket=self.bucket_name,
    #             CreateBucketConfiguration={"LocationConstraint": "ap-south-1"},
    #         )
    #     except:
    #         self.logger.info(
    #             "Bucket already created. Maybe a mistake made when manually trying things out ?"
    #         )
    #         pass

    def __download_video_from_post(self, post, download_path, logger):
        logger.info(
            f"Process: {os.getpid()} is downloading video from post with title: {post['title']}"
        )

        file_name = post["name"] + ".mp4"
        file_path = download_path + file_name

        ydl_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "logger": logging.getLogger(),
            "outtmpl": file_path,
        }

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([post["url"]])

        # FIXME: Not sure how this will playout with helpers.s3
        # as this is run as a subprocess.
        # Try to use helpers.s3.upload_fileobj() sometime later to check if things
        # outside this method are available to the created subprocess.

        # with open(file_path, "rb") as f:
        #     self.s3.upload_fileobj(f, self.bucket_name, file_name)

        logger.info(
            f"Process: {os.getpid()} finished downloading and successfully pushed to s3"
        )

    def download_videos(self):
        self.logger.info("Downloading videos from posts")
        processes = []
        posts_completed = []
        start = time()
        for post in self.posts:
            process = Process(
                target=self.__download_video_from_post,
                args=(post, self.download_path, self.logger),
            )
            processes.append(process)

        for process in processes:
            process.start()

        for process in processes:
            process.join()

        end = time()

        self.logger.info(
            f"Finished processing {len(self.posts)} in {round(end - start, 2)} seconds"
        )


#  import asyncio, concurrent.futures, functools
# import concurrent.futures

# from multiprocessing import Process, Pipe

# # from subprocess import Popen, PIPE
# import logging, pprint, os, youtube_dl
# from time import time

# pp = pprint.PrettyPrinter(indent=2, compact=True, width=80)


# class DownloadPosts:
#     def __init__(self, subreddit, posts, logger):
#         self.subreddit = subreddit
#         self.posts = posts
#         self.download_cmd = [
#             "youtube-dl",
#             "-f",
#             "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
#             "placeholder_url",
#             "-o",
#             "placeholder_title",
#         ]
#         self.download_processes = []
#         self.logger = logger
#         self.download_processes_logs = []
#         self.tasks = {}

#     def __download_video_from_post(self, post, conn, logger):
#         self.logger.info(
#             f"Process: {os.getpid()} is downloading video from post with title: {post['title']}"
#         )
#         ydl_opts = {
#             "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
#             "logger": logging.getLogger(),
#             "outtmpl": post["title"],
#         }

#         with youtube_dl.YoutubeDL(ydl_opts) as ydl:
#             ydl.download([post["url"]])

#         conn.send("done")
#         conn.close()
#         self.logger(
#             f"Process: {os.getpid()} finished downloading and is shutting down."
#         )

#     def download_videos_from_posts(self):
#         self.logger.info("Downloading videos from posts")
#         parent_connections = []
#         processes = []
#         posts_completed = 0
#         start = time()
#         for post in self.posts:
#             parent_conn, child_conn = Pipe()
#             parent_connections.append(parent_conn)

#             process = Process(
#                 target=self.__download_video_from_post,
#                 args=(post, child_conn, self.logger),
#             )
#             processes.append(process)

#         for process in processes:
#             process.start()

#         for process in processes:
#             process.join()

#         for parent_conn in parent_connections:
#             posts_completed += parent_conn.recv()[0]

#         end = time()

#         self.logger("Received the following messages from child processes")
#         self.logger(pp.pformat(posts_completed))
#         self.logger.info(
#             f"Finished processing {posts_completed} in {round(end - start, 2)} seconds"
#         )

# def download_videos_from_posts(self):
#     start = time()
#     results = []
#     with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
#         futures = [
#             executor.submit(download_video_from_post, post) for post in self.posts
#         ]

#     for future in concurrent.futures.as_completed(futures):
#         results.append(future.result())
#     end = time()

#     self.logger.info("Results are:")
#     self.logger.info(pp.pformat(results))

#     self.logger.info(
#         f"Time taken to download {len(self.posts)} videos from {self.subreddit} is {round(end-start, 2)}s"
#     )


# def download_video_from_post(post):
#     logger = logging.getLogger()
#     download_cmd = [
#         "youtube-dl",
#         "-f",
#         "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
#         "placeholder_url",
#         "-o",
#         "placeholder_title",
#     ]
#     title = post["title"]
#     logger.info(f"Post received with title: {title}")

#     download_path = post["title"]
#     download_cmd[3] = post["url"]
#     download_cmd[5] = download_path

#     process = Popen(download_cmd, stderr=PIPE)
#     stdout, stderr = process.communicate()

#     if stderr:
#         logger.error("Failed to download the post:\n")
#         logger.error(pp.pformat(post))
#         logger.error("Failed with error")
#         logger.error(pp.pformat(stderr.decode("utf-8")))
#     else:
#         logger.info("Successfully downloaded the post:\n")
#         logger.info(pp.pformat(post))
