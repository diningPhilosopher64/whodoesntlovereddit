import cv2, os, boto3, imgkit, pprint
import numpy as np
import re
import glob
from moviepy.editor import *
from PIL import Image
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from pathlib import Path
from bs4 import BeautifulSoup
from concurrent.futures import ProcessPoolExecutor, as_completed


pp = pprint.PrettyPrinter(indent=2, compact=True, width=80)


class TTS:
    def __init__(
        self, reddit_account, post, posts_root_path, generic_index_file_path, logger
    ):
        self.post = post
        self.post_path = Path(posts_root_path / f'post_{self.post["id"]}')
        self.comments = []
        self.comments_with_replies = []
        self.reddit_account = reddit_account
        self.generic_index_file_path = generic_index_file_path
        self.logger = logger

        self.post_path.mkdir(parents=True, exist_ok=True)

    def __fetch_comments(self):
        REDDIT_API_COMMENTS_URL = (
            f'https://oauth.reddit.com/r/AskReddit/comments/{self.post["id"]}'
        )

        comments = self.reddit_account.fetch_posts_as_json(
            REDDIT_API_COMMENTS_URL,
            params={"depth": "1", "limit": "100", "sort": "top"},
        )

        comments = comments[1]
        comments = comments["data"]["children"]

        actual_comments = []
        for comment in comments:
            comment = comment["data"]
            if "body" in comment:
                actual_comments.append(comment)

        self.logger.info(f"Fetched {len(actual_comments)} comments")

        return actual_comments

    def __filter_comments(self, comments):
        awarded_comments = [
            comment for comment in comments if comment["total_awards_received"] > 0
        ]

        if not awarded_comments:
            awarded_comments = [comment for comment in comments if comment["ups"] > 500]
            awarded_comments = max(awarded_comments, comments[: len(comments) / 2])

        self.logger.info(f"Filtered {len(awarded_comments)} comments")

        return awarded_comments

    def fetch_and_filter_comments(self):
        comments = self.__fetch_comments()
        filtered_comments = self.__filter_comments(comments)
        self.comments = filtered_comments

    def __fetch_replies(self, comment):
        replies = self.reddit_account.fetch_posts_as_json(
            "https://oauth.reddit.com/api/morechildren/",
            params={
                "link_id": self.post["name"],
                "children": comment["id"],
                "depth": "3",
                "sort": "top",
            },
        )

        replies = replies["jquery"][10][3][0]

        actual_replies = []

        for reply in replies:
            reply = reply["data"]
            if "body" in reply:
                actual_replies.append(reply)

        self.logger.info(
            f"Fetched {len(actual_replies)} replies for comment {comment['id']}"
        )

        return actual_replies[1:]

    def __filter_replies(self, replies):
        awarded_replies = [
            reply for reply in replies if reply["total_awards_received"] > 0
        ]

        # If comment has no awarded replies, pick atmost 2, most upvoted replies
        if not awarded_replies:
            awarded_replies = [reply for reply in replies if reply["ups"] > 500]
            awarded_replies = awarded_replies[:2]

        self.logger.info(f"Filtered {len(awarded_replies)} replies")

        return awarded_replies

    def fetch_and_filter_replies_to_comments(self):
        self.logger.info(f"Finalizing comments and replies")
        final_comments = []
        for comment in self.comments:
            replies = self.__fetch_replies(comment)
            filtered_replies = self.__filter_replies(replies)
            # replies = []
            # filtered_replies = []
            if not comment or not filtered_replies:
                continue

            final_comment = {}
            final_comment["comment"] = comment
            final_comment["replies"] = filtered_replies
            final_comments.append(final_comment)

            final_comments.append(final_comment)
            self.logger.info(
                f"For comment {comment['id']}, finalized {len(filtered_replies)} replies"
            )

        self.comments_with_replies = final_comments

    def __prepare_data(self, is_comment, permalink):
        data_permalink = f"https://www.redditmedia.com{permalink}"
        depth = 1 if is_comment else 2
        context = "" if is_comment else "context=7&amp;"
        query_params = f"depth={depth}&amp;showmore=false&amp;embed=true&amp;showtitle=true&amp;{context}showmedia=false&amp;theme=dark"
        iframe_src = f"{data_permalink}?{query_params}"

        return iframe_src

    def __generate_live_iframe(
        self, is_comment, permalink, iD, generic_index_file_path, live_iframe_path
    ):
        iframe_src = self.__prepare_data(is_comment, permalink)

        with open(generic_index_file_path) as f:
            soup = BeautifulSoup(f, "html.parser")

        iframe = soup.find("iframe")

        iframe["src"] = iframe_src

        with open(live_iframe_path, "w") as f:
            f.write(str(soup.prettify(formatter="html")))

    def __generate_saved_iframe(self, html_file, saved_iframe_path):
        option = webdriver.FirefoxOptions()
        option.add_argument("--headless")
        option.add_argument("--width=3000")
        option.add_argument("--height=800")
        option.add_argument("--start-maximized")
        option.add_argument("--start-fullscreen")

        browser = webdriver.Firefox(options=option)
        html_file = "file://" + str(html_file)

        browser.get(html_file)

        iframe = browser.find_element_by_tag_name("iframe")
        browser.switch_to.frame(iframe)
        html = browser.page_source

        soup = BeautifulSoup(str(html), "html.parser")

        with open(saved_iframe_path, "w") as f:
            f.write(str(soup.prettify(formatter="html")))

        browser.quit()

    def __split_text_into_lines(self, is_comment, iframe_file_path):
        # print("iframe_file_path ", iframe_file_path)
        with open(iframe_file_path, "r") as f:
            soup = BeautifulSoup(f, "html.parser")
            # paragraphs = soup.findAll("p")
        target_item = None
        try:
            divs = soup.select(".md")
            target_item = divs[0] if is_comment else divs[1]

        except Exception as exc:
            print(divs, iframe_file_path)
            print(exc)
            return None, None
        # FIXME:  If reply to a reply, you'll have to pass additional arg which contains the
        # target text. Then you can iterate over paragraphs to get the target text using 'in'

        if not target_item:
            return None, None
        delimiters = ".,\n"
        prefix = ""
        prefix_parsed_split_paras = []
        parsed_split_paras = []

        for child in target_item.children:
            try:
                if not child:
                    continue

                complete_text_in_para = ""
                split_para = re.split(f"([{delimiters}])", child.text.strip())

                split_para = [
                    split_para_item for split_para_item in split_para if split_para_item
                ]

                if not split_para:
                    continue

                parsed_split_para = []
                for split_para_item in split_para:
                    if not split_para_item in delimiters:
                        parsed_split_para.append(split_para_item)
                    else:
                        parsed_split_para[-1] = parsed_split_para[-1] + split_para_item

                parsed_split_paras.extend(parsed_split_para)
                prefix_parsed_para = []
                for parse in parsed_split_para:
                    prefix = prefix + parse
                    prefix_parsed_para.append(prefix)

                prefix += "\n"
                prefix_parsed_split_paras.extend(prefix_parsed_para)
            except Exception as exc:
                print(child, iframe_file_path, divs, target_item)
                print(exc)

        return prefix_parsed_split_paras, parsed_split_paras

    def stitch_comment_clips_together(self):
        import subprocess

        for folder in os.listdir(self.post_path):

            comment_file_path = os.path.join(self.post_path, folder, "comment_0.mp4")

            if not os.path.isfile(comment_file_path):
                continue

            comment_file_paths = glob.glob(
                os.path.join(self.post_path, folder, "comment_*.mp4")
            )

            comment_file_paths.sort()

            reply_file_paths = glob.glob(
                os.path.join(self.post_path, folder, "reply*.mp4")
            )
            reply_file_paths.sort()

            all_clips = comment_file_paths + reply_file_paths

            clips_list_path = os.path.join(self.post_path, folder, "clips_list.txt")

            self.logger.info(
                f"Stitching clips for comment {os.path.join(self.post_path, folder)}"
            )

            with open(clips_list_path, "w") as f:
                for clip in all_clips:
                    f.write(f"file '{clip}'\n")

            final_comment_video_path = os.path.join(self.post_path, folder, "final.mp4")

            cmd = [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                clips_list_path,
                "-c",
                "copy",
                final_comment_video_path,
            ]

            subprocess.run(cmd)

    def stitch_all_clips_together(self):
        import subprocess

        all_clips = []
        for folder in os.listdir(self.post_path):

            final_clip_path = os.path.join(self.post_path, folder, "final.mp4")
            if not os.path.isfile(final_clip_path):
                continue

            all_clips.append(final_clip_path)

        all_clips_list_path = os.path.join(self.post_path, "all_clips_list.txt")

        with open(all_clips_list_path, "w") as f:
            for clip in all_clips:
                f.write(f"file '{clip}'\n")

        final_post_video_path = os.path.join(self.post_path, "final_post_video.mp4")

        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            all_clips_list_path,
            "-c",
            "copy",
            final_post_video_path,
        ]

        subprocess.run(cmd)

    def process_and_render(self):
        multiprocessing_args = []
        for idx, comment_with_reply in enumerate(self.comments_with_replies):
            comment_with_reply_path = (
                self.post_path / f'{idx}_{comment_with_reply["comment"]["id"]}'
            )
            comment_with_reply_path.mkdir(parents=True, exist_ok=True)
            comment = comment_with_reply["comment"]
            replies = comment_with_reply["replies"]

            # For comment, generate live iframe and save it with source downloaded
            live_iframe_path = comment_with_reply_path / "comment_live_iframe.html"
            saved_iframe_path = comment_with_reply_path / "comment_saved_iframe.html"
            is_comment = True
            self.__generate_live_iframe(
                is_comment,
                comment["permalink"],
                comment["id"],
                self.generic_index_file_path,
                live_iframe_path,
            )

            self.__generate_saved_iframe(live_iframe_path, saved_iframe_path)

            # Split the entire comment into lines
            prefix_parsed_split_text, comment_split_text = self.__split_text_into_lines(
                is_comment, saved_iframe_path
            )

            if prefix_parsed_split_text is None or comment_split_text is None:
                continue

            for idx, split_comment in enumerate(comment_split_text):
                comment_arg_dict = {
                    "text_to_show": prefix_parsed_split_text[idx],
                    "text_to_speak": split_comment,
                    "is_comment": True,
                    "saved_iframe_path": saved_iframe_path,
                    "idx": idx,
                }
                multiprocessing_args.append(comment_arg_dict)

            # For each reply, generate live iframe then save it with source downloaded
            replies_args = []
            for index, reply in enumerate(replies):
                live_iframe_path = (
                    comment_with_reply_path / f"reply_{index}_live_iframe.html"
                )
                saved_iframe_path = (
                    comment_with_reply_path / f"reply_{index}_saved_iframe.html"
                )
                is_comment = False
                self.__generate_live_iframe(
                    is_comment,
                    reply["permalink"],
                    reply["id"],
                    self.generic_index_file_path,
                    live_iframe_path,
                )
                self.__generate_saved_iframe(live_iframe_path, saved_iframe_path)

                # For each reply split the entire reply into lines
                (
                    prefix_reply_split_text,
                    reply_split_text,
                ) = self.__split_text_into_lines(is_comment, saved_iframe_path)

                if prefix_reply_split_text is None or reply_split_text is None:
                    continue

                for index1, split_reply in enumerate(reply_split_text):
                    reply_arg_dict = {
                        "text_to_show": prefix_reply_split_text[index1],
                        "text_to_speak": split_reply,
                        "is_comment": False,
                        "saved_iframe_path": saved_iframe_path,
                        "idx": index1,
                    }
                    multiprocessing_args.append(reply_arg_dict)

                # TODO: Remove this line once everything works as expected
                # break

            # TODO: Remove this line once everything works as expected
            # break

        # print("multiprocessing ", multiprocessing_args)
        with ProcessPoolExecutor(max_workers=5) as executor:
            future_processes = {
                executor.submit(TTS.process_and_render_item, args)
                for args in multiprocessing_args
            }

            for future in as_completed(future_processes):
                try:
                    data = future.result()
                except Exception as exc:
                    print(f"Generated an exception: {exc}")
                else:
                    print(f"Generated data for comment process: {future}")

    def process_and_render_item(arg):
        item = arg
        is_comment = item["is_comment"]
        idx = item["idx"]
        text_to_show = item["text_to_show"]
        text_to_speak = item["text_to_speak"]
        saved_iframe_path = item["saved_iframe_path"]

        item_root_path = saved_iframe_path.parent

        generated_paths = generate_required_paths(item_root_path, is_comment, idx)

        generate_item_iframe_path(
            saved_iframe_path,
            is_comment,
            text_to_show,
            generated_paths["item_iframe_path"],
        )
        add_customization(
            generated_paths["item_iframe_path"],
            is_comment,
            generated_paths["customized_item_iframe_path"],
        )
        generate_image_from_iframe(
            generated_paths["customized_item_iframe_path"],
            generated_paths["image_path"],
        )
        generate_and_download_audio(text_to_speak, generated_paths["audio_path"])
        generate_and_render_video(
            generated_paths["image_path"],
            generated_paths["audio_path"],
            generated_paths["video_path"],
        )


def generate_item_iframe_path(
    saved_iframe_path, is_comment, text_to_show, generated_item_iframe_path
):
    with open(saved_iframe_path, "r") as f:
        soup = BeautifulSoup(f, "html.parser")

    divs = soup.select(".md")

    padding = "\n          "
    div = divs[0] if is_comment else divs[1]

    paragraphs = div.findAll("p")

    for paragraph in paragraphs:
        paragraph.decompose()

    p_tag = soup.new_tag("p")
    p_tag.string = padding + text_to_show + padding

    div.append(p_tag)

    with open(generated_item_iframe_path, "w") as f:
        f.write(str(soup.prettify(formatter="html")))


def generate_required_paths(item_root_path, is_comment, idx):
    prefix = f"comment_{idx}" if is_comment else f"reply_{idx}"

    paths = {
        "item_iframe_path": item_root_path / f"{prefix}.html",
        "customized_item_iframe_path": item_root_path / f"{prefix}_customized.html",
        "image_path": item_root_path / f"{prefix}.png",
        "audio_path": item_root_path / f"{prefix}.mp3",
        "video_path": item_root_path / f"{prefix}.mp4",
    }

    return paths


def generate_image_from_iframe(saved_iframe_path, generated_image_path):

    options = {"width": 1920, "height": 1080, "quiet": ""}
    imgkit.from_file(str(saved_iframe_path), str(generated_image_path), options=options)

    return generated_image_path


def generate_and_render_video(image_file_path, audio_file_path, final_video_path):
    import subprocess

    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-framerate",
        "1",
        "-i",
        str(image_file_path),
        "-i",
        str(audio_file_path),
        "-vcodec",
        "libx264",
        "-c:a",
        "copy",
        "-r",
        "30",
        "-pix_fmt",
        "yuv420p",
        final_video_path,
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # audio_clip = AudioFileClip(str(audio_file_path))
    # duration = audio_clip.duration
    # video_clip = ImageClip(str(image_file_path), duration=duration)
    # video_clip.audio = audio_clip

    # video_clip.write_videofile(str(final_video_path), fps=1, logger=None)


def generate_and_download_audio(text, audio_file_path):
    params = {
        "Engine": "neural",
        "OutputFormat": "mp3",
        "Text": text,
        "TextType": "text",
        "VoiceId": "Matthew",
    }

    polly = boto3.client("polly", region_name="ap-southeast-1")

    response = polly.synthesize_speech(**params)

    with open(audio_file_path, "wb") as f:
        f.write(response["AudioStream"].read())


def add_customization(saved_iframe_path, is_comment, customized_item_iframe_path):
    with open(saved_iframe_path, "r") as f:
        soup = BeautifulSoup(f, "html.parser")

    html = soup.find("html")

    style_content = """
        body {
            margin-top: 3%;
            margin-left: 10%;
            margin-right: 10%;
            /* text-align: center; */
            /* margin: 0;
            position: absolute;
            top: 50%;
            left: 50%;
            -ms-transform: translate(-50%, -50%);
            transform: translate(-50%, -50%); */
        }
        .md {
            max-width: 1000em;
        }
        """
    script_comment_content = """
        let authorTextSize = '1.2', subredditTextSize = '1.5', titleTextSize = '2.5', commentTextSize = '2.5';
        let upvoteTextSize = '1.1';
        let sub = Array.from(
        document.getElementsByClassName('embed-subreddit-title')
        )[0];
        sub.setAttribute(
        'style',
        sub.getAttribute('style') + `;font-size: ${subredditTextSize}rem`
        );

        //   embed-subreddit-post-author
        let postedBy = Array.from(
        document.getElementsByClassName('embed-subreddit-post-author')
        )[0];
        postedBy.setAttribute(
        'style',
        postedBy.getAttribute('style') + `;font-size: ${authorTextSize}rem`
        );

        //   embed-subreddit-post-title
        let postTitle = Array.from(
        document.getElementsByClassName('reddit-embed-post-link-wrap')
        )[0];
        postTitle.setAttribute(
        'style',
        postTitle.getAttribute('style') + `;font-size: ${titleTextSize}rem`
        );

        //   reddit-embed-author
        let commentAuthor = Array.from(
        document.getElementsByClassName('reddit-embed-author')
        )[0];
        commentAuthor.setAttribute(
        'style',
        commentAuthor.getAttribute('style') + `;font-size: ${authorTextSize}rem`
        );

        let comment = Array.from(document.getElementsByTagName('p'))[0];
        comment.setAttribute(
        'style',
        comment.getAttribute('style') + `;font-size: ${commentTextSize}rem`
        );

        // reddit-embed-score
        let commentUpvotes = Array.from(
        document.getElementsByClassName('reddit-embed-score')
        )[0];
        commentUpvotes.setAttribute(
        'style',
        commentUpvotes.getAttribute('style') + `;font-size: ${upvoteTextSize}rem`
        );

        let commentRepliesCount = Array.from(
        document.getElementsByClassName('reddit-embed-replies')
        )[0];

        commentRepliesCount.remove();

        // embed-subreddit-post-date
        let postDate = Array.from(
        document.getElementsByClassName('embed-subreddit-post-date')
        )[0];

        postDate.remove();

        //  reddit-embed-comment-meta-item reddit-embed-permalink
        let commentDate = Array.from(
        document.getElementsByClassName(
            'reddit-embed-comment-meta-item reddit-embed-permalink'
        )
        )[0];

        commentDate.remove();
        """

    script_reply_content = """
            // This section is for the comment reply only.
        //   reddit-embed-author
        let replyAuthor = Array.from(
        document.getElementsByClassName('reddit-embed-author')
        )[1];
        replyAuthor.setAttribute(
        'style',
        replyAuthor.getAttribute('style') + `;font-size: ${authorTextSize}rem`
        );

        //  reddit-embed-comment-meta-item reddit-embed-permalink
        // Here we choose the zeroeth element from the array because the comment's
        // date is already removed from dom.
        let replyDate = Array.from(
        document.getElementsByClassName(
            'reddit-embed-comment-meta-item reddit-embed-permalink'
        )
        )[0];

        replyDate.remove();

        let replyRepliesCount = Array.from(
        document.getElementsByClassName('reddit-embed-replies')
        )[0];

        replyRepliesCount.remove();

        // Here we choose the first element from the array because the comment is
        // the first 'p' tag and the reply is the second 'p' tag

        let reply = Array.from(document.getElementsByTagName('p'))[1];
        reply.setAttribute(
        'style',
        reply.getAttribute('style') + `;font-size: ${commentTextSize}rem`
        );

        // reddit-embed-score
        // Similar explanation as above
        let replyUpvotes = Array.from(
        document.getElementsByClassName('reddit-embed-score')
        )[1];
        replyUpvotes.setAttribute(
        'style',
        replyUpvotes.getAttribute('style') + `;font-size: ${upvoteTextSize}rem`
        );
        """

    script_content = (
        script_comment_content
        if is_comment
        else script_comment_content + script_reply_content
    )

    style = soup.new_tag("style", type="text/css")
    style.append(style_content)

    script = soup.new_tag("script", type="text/javascript")
    script.append(script_content)
    html.append(script)
    html.append(style)

    # div_md = soup.find("")

    with open(customized_item_iframe_path, "w") as f:
        f.write(str(soup.prettify(formatter="html")))

    return saved_iframe_path
