# Authors: Denis A. Engemann <denis.engemann@gmail.com>
#
# License: BSD (3-clause)

import os
import os.path as op
import boto
import base64
import boto.s3.connection
from boto.s3.key import Key
from boto.ec2 import EC2Connection
from boto.ec2.blockdevicemapping import BlockDeviceMapping, BlockDeviceType
from mne.utils import _TempDir

mapping = BlockDeviceMapping()
mapping["/dev/sdb"] = BlockDeviceType(ephemeral_name='ephemeral0')

_base_template = """#!/bin/bash
echo "updating code ..."
source /home/ubuntu/.bashrc
source /home/ubuntu/miniconda2/bin/activate swish
/home/ubuntu/miniconda2/bin/pip install boto
(cd /home/ubuntu/github/PRNI2016
  && git pull origin master
  && echo "updating code ... done"
  && {cmd})
"""


def download_from_s3(aws_access_key_id, aws_secret_access_key, bucket, fname,
                     key, dry_run=False,
                     host='s3.amazonaws.com'):
    """Download file from bucket
    """
    switch_validation = False
    if host is not None and not isinstance(
            host, boto.s3.connection.NoHostProvided):
        if 'eu-central' in host:
            switch_validation = True
            os.environ['S3_USE_SIGV4'] = 'True'

    com = boto.connect_s3(aws_access_key_id, aws_secret_access_key, host=host)
    bucket = com.get_bucket(bucket, validate=False)
    my_key = Key(bucket)
    my_key.key = key
    out = False
    if my_key.exists():
        if not dry_run:
            s3fid = bucket.get_key(key)
            s3fid.get_contents_to_filename(fname)
            out = True
        else:
            return True
    else:
        print('could not get %s : it does not exist' % key)
        out = False
    if switch_validation:
        del os.environ['S3_USE_SIGV4']
    return out


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
    switch_validation = False
    if host is not None:
        if 'eu-central' in host:
            switch_validation = True
            os.environ['S3_USE_SIGV4'] = 'True'
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

    if switch_validation:
        del os.environ['S3_USE_SIGV4']

    if sent == size:
        return True
    return False


def get_test_script(subjects, poweroff=True):
    script = 'python compute_test_s3 --subject {subjects}'.format(
        subjects=' '.join(subjects))
    cmd = _base_template.format(cmd=script)
    if poweroff:
        cmd += '\nsudo poweroff'
    return cmd


def get_run_parallel_script(subjects, script, poweroff=True, n_par=1):
    parallel_cmd = ('python run_parallel.py --script {script} '
                    '--par_target subject --par_args {subjects} '
                    '--n_par {n_par}').format(
                        subjects=' '.join(subjects),
                        script=script,
                        n_par=n_par)

    cmd = _base_template.format(cmd=parallel_cmd)
    if poweroff:
        cmd += '\nsudo poweroff'
    return cmd


def instance_run_jobs(code,
                      aws_access_key_id=None, aws_secret_access_key=None,
                      instance_type='t2.micro', dry_run=False):

    ec2con = EC2Connection(aws_access_key_id=aws_access_key_id,
                           aws_secret_access_key=aws_secret_access_key)
    import pdb; pdb.set_trace()
    out = ec2con.run_instances(
        image_id='ami-62474008', min_count=1, instance_type=instance_type,
        key_name='test-node-virginia', user_data=code,
        dry_run=dry_run, instance_initiated_shutdown_behavior='terminate',
        instance_profile_name='push-to-swish', block_device_map=mapping,
        security_groups=['launch-wizard-1'])
    return out
