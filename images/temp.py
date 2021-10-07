from daily_uploads import (
    process_posts_in_subreddits_group,
    download_and_resize,
    process_individual_clips,
    stitch_clips_and_render,
    upload_video_files,
)


process_posts_in_subreddits_group.process_posts()

download_and_resize.run()

process_individual_clips.run()

stitch_clips_and_render.run()

upload_video_files.run()
