# from daily_uploads import process_subreddits_group
# import logging

# # Initialize logger and its config.
# logger = logging.getLogger()
# logger.setLevel(logging.INFO)


# logger.info("Starting processing")

# process_subreddits_group.run(
#     {"Records": [{"body": "whodoesntlovereddit-2021-09-08-funny"}]}, {}
# )

from daily_uploads import (
    process_posts_in_subreddits_group,
    download_and_resize,
    process_individual_clips,
    stitch_clips_and_render,
    upload_video_files,
)


process_posts_in_subreddits_group.process_posts()

# download_and_resize.run()

# process_individual_clips.run()

# stitch_clips_and_render.run()

# upload_video_files.run()
