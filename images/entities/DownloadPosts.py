from multiprocessing import Process, Pipe
from moviepy.editor import *

# from subprocess import Popen, PIPE
import logging, pprint, os, youtube_dl
from time import time
from datetime import datetime

pp = pprint.PrettyPrinter(indent=2, compact=True, width=80)

from helpers import s3 as s3_helpers
from pathlib import Path


class DownloadPosts:
    def __init__(
        self,
        s3,
        posts,
        bucket_name,
        logger,
        download_path="/tmp",
        encode_path="/tmp/encoded",
    ):
        self.posts = posts
        self.download_path = download_path
        self.encode_path = encode_path
        self.logger = logger
        self.s3 = s3
        self.bucket_name = bucket_name
        Path(self.encode_path).mkdir(exist_ok=True, parents=True)
        Path(self.download_path).mkdir(exist_ok=True, parents=True)

        self.__create_s3_bucket()

    # NOTE: If you comment below fn and the above call, comment out s3 upload in
    # the method: __download_video_from_post
    def __create_s3_bucket(self):
        try:
            self.s3.create_bucket(
                ACL="private",
                Bucket=self.bucket_name,
                CreateBucketConfiguration={"LocationConstraint": "ap-south-1"},
            )
        except:
            self.logger.info(
                "Bucket already created. Maybe a mistake made when manually trying things out ?"
            )
            pass

    def __download_video_from_post(self, post, logger):
        import subprocess

        self.logger.info(
            f"Process: {os.getpid()} is downloading video from post with title: {post['title']}"
        )

        file_name_mp4 = post["name"] + ".mp4"
        # file_name_mkv = post["name"] + ".mkv"

        download_file_path_mp4 = os.path.join(self.download_path, file_name_mp4)
        encode_file_path_mp4 = os.path.join(self.encode_path, file_name_mp4)
        # encode_file_path_mkv = os.path.join(self.encode_path, file_name_mkv)

        ydl_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "logger": logging.getLogger(),
            "outtmpl": download_file_path_mp4,
        }

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([post["url"]])

        print(f"Finished downloading the file to {download_file_path_mp4}")
        # ffmpeg_resize_command = [
        #     "ffmpeg",
        #     "-hide_banner",
        #     "-loglevel",
        #     "error",
        #     "-i",
        #     download_file_path_mp4,
        #     "-vf",
        #     "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:-1:-1:color=black",
        #     encode_file_path_mp4,
        #     "-movflags",
        #     "+faststart",
        #     "-y",
        # ]

        ffmpeg_resize_command = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            # "-movflags",
            # "+faststart",
            "-i",
            download_file_path_mp4,
            "-vcodec",
            "libx264",
            "-acodec",
            "ac3",
            "-vf",
            "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:x=(1920-iw)/2:y=(1080-ih)/2:color=black",
            encode_file_path_mp4,
        ]
        print(f"ffmpegging the file {download_file_path_mp4}")

        subprocess.run(
            ffmpeg_resize_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        try:
            clip = VideoFileClip(encode_file_path_mp4)
            print(f"Able to read the file {encode_file_path_mp4} in moviepy")
        except Exception as e:
            print(f"There is an exception with file {encode_file_path_mp4}")
            print(e)

        # subprocess.run(
        #     ["qtfaststart", encode_file_path_mp4, "p_" + encode_file_path_mp4],
        #     stdout=None,
        #     stderr=subprocess.PIPE,
        # )

        # try:
        #     from moviepy.editor import VideoFileClip

        #     bla = VideoFileClip(encode_file_path_mp4)
        #     print(f"Finished file {encode_file_path_mp4}")
        #     # bla = bla.resize(width=1920, height=1080)
        #     # bla.write_videofile(encode_file_path_mp4, logger=None, verbose=False)
        #     # print(f"Finished resizing the file to {encode_file_path_mp4}")

        # except Exception as e:
        #     print(e)

        # ffmpeg_convert_command = [
        #     "ffmpeg",
        #     "-hide_banner",
        #     "-loglevel",
        #     "error",
        #     "-i",
        #     encode_file_path_mkv,
        #     encode_file_path_mp4,
        # ]

        # subprocess.run(ffmpeg_convert_command, stdout=None, stderr=subprocess.PIPE)

        # print(
        #     f"Finished ffmpegging, encoding and converting the file is at {encode_file_path_mp4}"
        # )

        # try:
        #     from moviepy.editor import VideoFileClip

        #     bla = VideoFileClip(download_file_path_mp4)
        #     bla = bla.resize(width=1920, height=1080)
        #     bla.write_videofile(encode_file_path_mp4, logger=None, verbose=False)
        #     print(f"Finished resizing the file to {encode_file_path_mp4}")

        # except Exception as e:
        #     print(e)

    def download_videos(self):
        self.logger.info("Downloading videos from posts")
        processes = []

        start = time()

        for idx, post in enumerate(self.posts):
            # if idx > len(self.posts) / 3:
            #     break
            process = Process(
                target=self.__download_video_from_post,
                args=(post, self.logger),
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
