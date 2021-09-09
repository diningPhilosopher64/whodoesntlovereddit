from concurrent.futures.process import ProcessPoolExecutor
import boto3, os, logging, pprint, json
from pathlib import Path

from time import time, time_ns
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import Process
from datetime import datetime, timedelta
from process_posts_in_subreddits_group import parse_subreddits_group

pp = pprint.PrettyPrinter(indent=2, compact=True, width=80)

# Initialize logger and its config.
logger = logging.getLogger()
logger.setLevel(logging.INFO)

from entities.FilterPosts import FilterPosts
from entities.DownloadPosts import DownloadPosts
from entities.VideoProcessing import VideoProcessing
from helpers import s3 as s3_helpers


POSTS_DOWNLOAD_LOCATION = os.getenv("POSTS_DOWNLOAD_LOCATION", "posts")
UNPARSED_SUBREDDITS_GROUP = os.getenv("UNPARSED_SUBREDDITS_GROUP")


def run():

    start = time()
    video_paths_to_upload = get_paths_of_videos()

    videos_data = []
    for video_path in video_paths_to_upload:
        videos_data.append(prepare_video_metadata_to_upload(video_path))

    s3 = boto3.client("s3")
    bucket_name = "whodoesntlovereddit" + "-" + str(datetime.today().date())
    if not s3_helpers.bucket_exists(
        s3,
        logger,
        {
            "Bucket": bucket_name,
        },
    ):
        s3_helpers.create_bucket(
            s3,
            logger,
            {
                "ACL": "private",
                "Bucket": bucket_name,
                "CreateBucketConfiguration": {"LocationConstraint": "ap-south-1"},
            },
        )

    with ProcessPoolExecutor(max_workers=len(videos_data)) as executor:
        future_upload_process = {
            executor.submit(upload_to_s3, bucket_name, video_data[0], video_data[1])
            for video_data in videos_data
        }

        for future in as_completed(future_upload_process):
            try:
                data = future.result()
            except Exception as exc:
                logger.error(f"Failed to upload video. {future}")
                print(exc)
            else:
                logger.info(f"Successfully uploaded video. {future}")

    end = time()

    logger.info(
        f"Time taken to upload {len(video_paths_to_upload)} vidoes is {round(end-start,2)}s"
    )


def upload_to_s3(bucket_name, metadata_file_path, video_file_path):
    s3 = boto3.client("s3")

    s3_helpers.upload_file(
        s3, logger, bucket_name=bucket_name, file_path=str(video_file_path)
    )

    s3_helpers.upload_file(
        s3, logger, bucket_name=bucket_name, file_path=str(metadata_file_path)
    )


def get_paths_of_videos():
    posts_paths = os.listdir(POSTS_DOWNLOAD_LOCATION)

    videos_to_upload = []
    for posts in posts_paths:
        video_folder_path = (
            Path(POSTS_DOWNLOAD_LOCATION) / posts / "encoded" / "processed"
        )

        for video in os.listdir(video_folder_path):
            if video.startswith("whodoesntlovereddit"):
                videos_to_upload.append(video_folder_path / video)
                break

    return videos_to_upload


def prepare_video_metadata_to_upload(video_path):
    video_folder = video_path.parent

    posts_json_folder_path = video_folder.parent.parent

    for item in os.listdir(posts_json_folder_path):
        if item.endswith(".json"):
            posts_json_file = posts_json_folder_path / item
            break

    with open(posts_json_file, "r") as f:
        posts = json.load(f)

    considered_posts = []
    for item in os.listdir(video_folder):
        if not item.startswith("whodoesntlovereddit"):
            post = get_post_from_name(posts, item.split(".")[0])
            considered_posts.append(post)

    video_credits = [f'u/{post["author"]} - {post["url"]}' for post in considered_posts]
    # video_credits = [f'u/{post["author"]}' for post in posts]

    video_credits = "\n".join(video_credits)

    keywords = ", ".join(parse_subreddits_group(UNPARSED_SUBREDDITS_GROUP))
    keywords = f'"{keywords}"'
    description = f"""
    Enjoy watching these funny meme clips/videos.

    Try not to laugh as you watch these funny/awesome/wholesome/creative/amazing  videos.

    Like the video and Subscribe for more.

    ➟ Credits (Please check out the creators of these clips, without them these kinds of videos won't exist):\n
    🎥 CONTENT CREATORS FEATURED (Show them some love):
    {video_credits}

    E-mail me on my business e-mail if you want your video removed or if i missed your credit (if i missed it, you will be credited with special thanks in the comments.)
    I browse hundreds of repost pages for one video and without a watermark, it's impossible for me to find the source of every clip.

    For promotions/removals, contact my email:📩  vidsfromaroundtheinternet@gmail.com

    ⚠️ Copyright Disclaimer, Under Section 107 of the Copyright Act 1976, allowance is made for 'fair use' for purposes
    such as criticism, comment, news reporting, teaching, scholarship, and research.
    Fair use is a use permitted by copyright statute that might otherwise be infringing.
    Non-profit, educational or personal use tips the balance in favor of fair use.

    ⚠️ Community Guidelines Disclaimer
    This video is for entertainment purposes only. My videos are not intented to bully / harass or offend anyone. The clips shown are funny, silly, they relieve stress and anxiety, create good vibes and make viewers laugh.  Many of them leaving feedback about these videos helping with depression, anxiety and all type of bad moods.
    This video should not be taken seriously.
    Do not perform any actions shown in this video!
    
    #Memes #DailyFunnyVideos #Funny #FunnyClips #WholesomeClips #Wholesome 
    #Daily #dank_memes #PetVideos #PetClips #Clips 
    """

    description = f'"{description}"'
    category_id = '"23"'
    title = f'"{str(video_path).split("/")[-1]}"'
    file_path = f'"{str(video_path)}"'

    file_name = str(video_path).split("/")[-1]
    video_name = file_name.split(".")[0]

    meta_data_file = video_path.parent / f"{video_name}_meta_data.txt"

    with open(meta_data_file, "w") as f:
        f.write(f"{title}\n{description}\n{keywords}\n{description}\n{category_id}\n")

    video_data = (meta_data_file, file_path)

    return video_data


def get_post_from_name(posts, post_name):

    post_name = (
        post_name if post_name.startswith("t3_") else post_name.partition("_")[2]
    )

    for post in posts:
        if post["name"] == post_name:
            return post


def upload_video(upload_command):
    os.system(" ".join(upload_command))
