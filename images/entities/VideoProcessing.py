# from multiprocessing import Process, Pipe, Pool
import pprint, random, boto3
from time import time
from pathlib import Path

from botocore.retries import bucket
from helpers import s3 as s3_helpers
import moviepy
from moviepy.editor import *
from concurrent.futures import ProcessPoolExecutor, as_completed

pp = pprint.PrettyPrinter(indent=2, compact=True, width=80)


class VideoProcessing:
    def __init__(
        self,
        encode_path,
        posts,
        s3,
        bucket_name,
        final_video_name,
        logger,
    ):
        self.encode_path = encode_path
        self.processed_path = os.path.join(self.encode_path, "processed")
        self.processed_file_names = []
        self.bucket_name = bucket_name
        Path(self.processed_path).mkdir(exist_ok=True, parents=True)
        Path(self.encode_path).mkdir(exist_ok=True, parents=True)
        self.final_video_path = (
            os.path.join(self.processed_path, final_video_name) + ".mp4"
        )
        self.posts = posts
        self.s3 = s3
        self.logger = logger

        self.logger.info(f"Encode path set to: {self.encode_path}")
        self.logger.info(f"Processed path set to: {self.processed_path}")
        self.logger.info(f"Final video path set to: {self.final_video_path}")

    def __download_transition_clips(self, TRANSITION_CLIPS_BUCKET):
        transition_clips_file_paths = {}
        transition_clips_set = set()

        params = {"Bucket": TRANSITION_CLIPS_BUCKET}
        objects = s3_helpers.list_objects_v2(self.s3, self.logger, **params)

        # convert it to a set to avoid duplication
        for post in self.posts:
            rand_index = random.randint(0, len(objects) - 1)
            clip = objects[rand_index]
            transition_clips_file_paths[post["name"]] = os.path.join(
                self.encode_path, clip
            )
            transition_clips_set.add(clip)

        # fetch transitions put it in download_path folder
        for clip in transition_clips_set:
            # transition_clip_file_path = transition_clips_file_paths[clip]
            params = {
                "Bucket": TRANSITION_CLIPS_BUCKET,
                "Key": clip,
                # "Filename": f"{self.download_path}{clip}",
                "Filename": os.path.join(self.encode_path, clip),
            }
            s3_helpers.download_file(self.s3, self.logger, **params)

        return transition_clips_file_paths

    def process_video_clips(
        self,
        TRANSITION_CLIPS_BUCKET,
        INTRO_CLIPS_BUCKET,
        OUTTRO_CLIPS_BUCKET,
        AUDIO_CLIPS_BUCKET,
    ):

        # list items in transitions bucket
        # self.logger.info("Processing each video in parallel")
        print("Processing the following video clips in parallel:")
        print([post["title"] for post in self.posts])
        processes = []

        transition_clips_paths = self.__download_transition_clips(
            TRANSITION_CLIPS_BUCKET
        )
        intro_clip_path = VideoProcessing.download_a_random_clip(
            INTRO_CLIPS_BUCKET, self.encode_path, self.logger, self.s3
        )
        outtro_clip_path = VideoProcessing.download_a_random_clip(
            OUTTRO_CLIPS_BUCKET, self.encode_path, self.logger, self.s3
        )

        # self.logger.info("Transition clips received are:")

        # pass intro, transition, outtro to each call of __process_individual_video() method
        # In params arg, send is_first, is_last, transition_clip, intro_clip,
        # outtro_clip and watermark_clip.
        start = time()
        params_arr = []
        for idx, post in enumerate(self.posts):
            is_first = True if idx == 0 else False
            is_last = True if idx == len(self.posts) - 1 else False

            if is_first:
                file_name = f'intro_{post["name"]}.mp4'
            elif is_last:
                file_name = f'outtro_{post["name"]}.mp4'
            else:
                file_name = f'{post["name"]}.mp4'

            params = {
                "is_first": is_first,
                "is_last": is_last,
                "transition_clip_path": transition_clips_paths[post["name"]],
                "intro_clip_path": intro_clip_path,
                "outtro_clip_path": outtro_clip_path,
                "file_name": file_name,
            }

            params_arr.append(params)
            self.processed_file_names.append(file_name)

        with ProcessPoolExecutor(max_workers=10) as executor:
            future_video_clip_processes = {
                executor.submit(
                    VideoProcessing.process_individual_video,
                    post,
                    self.bucket_name,
                    self.logger,
                    self.encode_path,
                    self.processed_path,
                    AUDIO_CLIPS_BUCKET,
                    params_arr[idx],
                )
                for idx, post in enumerate(self.posts)
            }

            for future in as_completed(future_video_clip_processes):
                try:
                    data = future.result()
                except Exception as exc:
                    print(f"Generated an exception: {exc}")
                else:
                    print(f"Generated data: {future}")

        end = time()

        # self.logger.info(
        #     f"Finished processing {len(self.posts)} video clips in {round(end - start, 2)} seconds"
        # )
        print(
            f"Finished processing {len(self.posts)} video clips in {round(end - start, 2)} seconds"
        )

        # self.logger.info(f"Concatenating processed clips")
        print(f"Concatenating processed clips")

    def concatenate_videos_and_render(self):
        print("Trying to concatenate videos of final video\n", self.final_video_path)
        self.logger.info("Concatenating clips to render video")

        intro_clip = None
        outtro_clip = None
        inbetween_clips = []
        for processed_file_name in self.processed_file_names:
            if processed_file_name.startswith("intro"):
                print(f"Intro clip is {processed_file_name}")
                intro_clip = VideoFileClip(
                    os.path.join(self.processed_path, processed_file_name)
                )

            elif processed_file_name.startswith("outtro"):
                print(f"Outtro clip is {processed_file_name}")
                outtro_clip = VideoFileClip(
                    os.path.join(self.processed_path, processed_file_name)
                )

            else:
                print(f"Inbetween clip is {processed_file_name}")
                inbetween_clips.append(
                    VideoFileClip(
                        os.path.join(self.processed_path, processed_file_name)
                    )
                )

        final_video = concatenate_videoclips(
            [intro_clip, *inbetween_clips, outtro_clip]
        )
        print("Final video path is ", self.final_video_path)
        final_video.write_videofile(self.final_video_path, logger=None)

    def upload_subreddits_group_videos_to_s3(self):
        with open(self.final_video_path, "rb") as f:
            self.s3.upload_fileobj(f, self.bucket_name, self.final_video_path)

        self.logger.info(f"Uploaded {self.final_video_path} to {self.bucket_name}")

    def download_a_random_clip(bucket_name, download_path, logger, s3=None, prefix=""):
        """Method to download a random clip from a bucket.
        Used for downloading intro/outtro clips.

        Args:
            bucket_name (String): Name of the bucket to download from.

        Returns:
            String: Path to the downloaded clip.
        """
        if not s3:
            s3 = boto3.client("s3")

        params = {"Bucket": bucket_name}

        params = (
            params
            if not prefix
            else {**params, "Prefix": prefix + "/", "StartAfter": prefix + "/"}
        )

        objects = s3_helpers.list_objects_v2(s3, logger, **params)

        random_clip = objects[random.randint(0, len(objects) - 1)]

        file_path = os.path.join(
            download_path,
            random_clip if not prefix else random_clip.partition(prefix + "/")[2],
        )

        params = {
            "Bucket": bucket_name,
            "Key": random_clip,
            "Filename": file_path,
        }

        s3_helpers.download_file(s3, logger, **params)

        print(f"Downloaded {random_clip} from {bucket_name}")

        return file_path

    def process_individual_video(
        post,
        bucket_name,
        logger,
        encode_path,
        processed_path,
        AUDIO_CLIPS_BUCKET,
        params,
    ):
        file_name = post["name"] + ".mp4"
        file_path = os.path.join(encode_path, file_name)

        # logger.info(
        #     f"Process: {os.getpid()} is processing the video from the post with name: {post['name']}"
        # )
        print(
            f"Process: {os.getpid()} is processing the video from the post with title: {post['title']}"
        )

        # Get video details:
        video_clip = VideoFileClip(file_path)
        fps = video_clip.fps
        duration = video_clip.reader.duration
        size = video_clip.size
        w, h = video_clip.size

        # If the video has no audio, then add a random track based on subreddit group/ bucket_name
        if video_clip.audio is None:
            print(
                f"The video clip with file name {file_name} has no audio. Fetching a random clip"
            )
            if "funny" in bucket_name:
                random_audio_file = VideoProcessing.download_a_random_clip(
                    bucket_name=AUDIO_CLIPS_BUCKET,
                    download_path=encode_path,
                    logger=logger,
                    prefix="funny",
                )

                random_audio_clip = AudioFileClip(random_audio_file).subclip(
                    0, duration
                )
                random_audio_clip = random_audio_clip.audio_fadeout(0.5)
                video_clip.audio = random_audio_clip

        # Generate Watermark clip
        watermark_clip = TextClip(
            "@VidsFromAroundTheInternet",
            fontsize=24,
            color="white",
            size=[w, 30],
            align="East",
        )
        watermark_clip = watermark_clip.set_duration(duration).set_fps(fps)
        watermark_clip = watermark_clip.set_pos(("bottom"))
        # logger.info(f"Generated watermark_clip for the post with name : {post['name']}")
        print(f"Generated watermark_clip for the post with title : {post['title']}")

        # Generate Title for the video
        title_clip = TextClip(
            post["title"],
            fontsize=18,
            color="white",
            size=[w, 24],
            align="West",
            stroke_width=1.5,
        )

        # words per sec
        wps = 3
        title_clip_duration = min(len(post["title"]) / wps, duration / 2, 4)
        title_clip = title_clip.set_pos(("top"))
        title_clip = title_clip.set_duration(title_clip_duration).set_fps(fps)
        # logger.info(f"Generated title_clip for the post with name : {post['name']}")
        print(f"Generated title_clip for the post with name : {post['title']}")

        processed_clip = CompositeVideoClip(
            [video_clip, title_clip, watermark_clip], size=size
        )
        logger.info(
            f"Composited video_clip, title_clip and watermark_clip for the post with name : {post['name']}"
        )
        print(
            f"Composited video_clip, title_clip and watermark_clip for the post with name : {post['title']}"
        )

        transition_clip = VideoFileClip(params["transition_clip_path"])

        if params["is_first"]:
            # If first video, concatenate: Intro | processed_clip | transition
            intro_clip = VideoFileClip(params["intro_clip_path"])
            final_clip = concatenate_videoclips(
                [intro_clip, processed_clip, transition_clip]
            )
            # logger.info(
            #     f"Post with name : {post['name']} is the first video of the subreddit group to be concatenated."
            # )
            print(
                f"Post with name : {post['title']} is the first video of the subreddit group to be concatenated."
            )

        elif params["is_last"]:
            # If last video, concatenate: processed_clip | outtro
            outtro_clip = VideoFileClip(params["outtro_clip_path"])
            final_clip = concatenate_videoclips([processed_clip, outtro_clip])
            # logger.info(
            #     f"Post with name : {post['name']} is the last video of the subreddit group to be concatenated."
            # )
            print(
                f"Post with name : {post['title']} is the last video of the subreddit group to be concatenated."
            )

        else:
            # Some video in the middle, concatenate: processed_clip | transition
            final_clip = concatenate_videoclips([processed_clip, transition_clip])
            # logger.info(f"Post with name : {post['name']} is being concatenated.")
            print(f"Post with name : {post['title']} is being concatenated.")

        final_clip_path = os.path.join(processed_path, params["file_name"])

        final_clip.write_videofile(final_clip_path, logger=None)
