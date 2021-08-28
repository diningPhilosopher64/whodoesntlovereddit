from daily_uploads import process_subreddits_group
import logging

# Initialize logger and its config.
logger = logging.getLogger()
logger.setLevel(logging.INFO)


logger.info("Starting processing")

process_subreddits_group.run(
    {"Records": [{"body": "whooesntlovereddit-2021-08-25-funny"}]}, {}
)
