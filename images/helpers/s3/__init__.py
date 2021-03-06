import os, sys, traceback, json, pprint
import re

pp = pprint.PrettyPrinter(indent=2, compact=True, width=80)


# Making the current directory in which this file is in discoverable to python
sys.path.append(os.path.join(os.path.dirname(__file__)))


from helpers.Exceptions import RequestedItemNotFoundException
from helpers import Exceptions


def bucket_exists(s3, logger, kwargs) -> bool:
    try:
        s3.head_bucket(**kwargs)
        logger.info(f'Bucket {kwargs["Bucket"]} exists.')
        return True

    except s3.exceptions.ClientError as err:
        if err.response["Error"]["Code"] == "404":
            logger.info(f'Bucket {kwargs["Bucket"]} does not exist.')

    except Exception:
        Exceptions.log_generic_exception(kwargs, logger)

    return False


def upload_file(s3, logger, bucket_name, file_path, prefix=""):
    file_name = file_path.split("/")[-1]

    file_name = file_name if not prefix else prefix + "/" + file_name

    try:

        with open(file_path, "rb") as f:
            s3.upload_fileobj(f, bucket_name, file_name)

        logger.info(
            f"Successfully uploaded the file: {file_name} to the bucket: {bucket_name}"
        )
    except:
        kwargs = {
            "BucketName": bucket_name,
            "FileName": file_path,
            "prefix": prefix,
        }
        Exceptions.log_generic_exception(kwargs, logger)


def create_bucket(s3, logger, kwargs) -> bool:
    try:
        s3.create_bucket(**kwargs)
        logger.info(f'Created bucket: {kwargs["Bucket"]}')
    except:
        Exceptions.log_generic_exception(kwargs, logger)


# def upload_file(s3, logger, file_path):
#     try:
#         with open(file_path, "rb") as f:
#             s3.upload_fileobj(f, )


def list_objects_v2(s3, logger, **kwargs):
    try:
        resp = s3.list_objects_v2(**kwargs)
        contents = resp["Contents"]
        objects = [content["Key"] for content in contents]

        logger.info("Got the following items:")
        logger.info(pp.pformat(objects))
        return objects

    except Exception:
        Exceptions.log_generic_exception(kwargs, logger)


def download_file(s3, logger, **kwargs):
    try:
        res = s3.download_file(**kwargs)

    except Exception:
        Exceptions.log_generic_exception(kwargs, logger)


# def upload_fileobj(s3, bucket_name, file_path, logger):
#     file_name = file_path.split("/")[-1]

#     try:
#         with open(file_path, "rb") as f:
#             s3.upload_fileobj(f, bucket_name, file_name)
#     except:
#         Exceptions.log_generic_exception(logger)
