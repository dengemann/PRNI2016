import os
import boto
from boto.s3.key import Key
os.environ['S3_USE_SIGV4'] = 'True'


def upload_to_s3(aws_access_key_id, aws_secret_access_key, fname, bucket, key,
                 callback=None, md5=None, reduced_redundancy=False,
                 content_type=None, host='s3.eu-central-1.amazonaws.com'):
    """
    Uploads the given file to the AWS S3
    bucket and key specified.

    callback is a function of the form:

    def callback(complete, total)

    The callback should accept two integer parameters,
    the first representing the number of bytes that
    have been successfully transmitted to S3 and the
    second representing the size of the to be transmitted
    object.

    Returns boolean indicating success/failure of upload.
    """
    com = boto.connect_s3(aws_access_key_id, aws_secret_access_key, host=host)
    bucket = com.get_bucket(bucket, validate=True)
    s3_key = Key(bucket)
    s3_key.key = key
    if content_type:
        s3_key.set_metadata('Content-Type', content_type)

    with open(fname) as fid:
        try:
            size = os.fstat(fname.fileno()).st_size
        except:
            # Not all file objects implement fileno(),
            # so we fall back on this
            fid.seek(0, os.SEEK_END)
            size = fid.tell()
        sent = s3_key.set_contents_from_file(
            fid, cb=callback, md5=md5, reduced_redundancy=reduced_redundancy,
            rewind=True)
        # Rewind for later use
        fid.seek(0)
    if sent == size:
        return True
    return False
