# Authors: Danilo Bzdok <danilbzdok@gmail.com>
#          Denis A. Engemann <denis.engemann@gmail.com>
#
# License: BSD (3-clause)
import sys
import time
import os
import os.path as op
from argparse import ArgumentParser

from aws_hacks import upload_to_s3
import pandas as pd

aws_details = pd.read_csv('aws_details.csv')
aws_access_key_id = aws_details['Access Key Id'].values[0]
aws_secret_access_key = aws_details['Secret Access Key'].values[0]

aws_details = pd.read_csv('aws_hcp_details.csv')
hcp_aws_access_key_id = aws_details['Access Key Id'].values[0]
hcp_aws_secret_access_key = aws_details['Secret Access Key'].values[0]


storage_dir = '/mnt'


def put_s3fun(fname, delete_if_good=True):
    key = fname.split(storage_dir)[-1].lstrip('./')
    good = upload_to_s3(
        aws_access_key_id, aws_secret_access_key, fname=fname,
        bucket='swish-data', key=key)
    if good:
        print('all is good, uploaded and removing %s' % fname)
        os.remove(fname)
    else:
        print('something went wrong with %s' % fname)


def test_s3(subject, storage_dir='/mnt', s3fun=put_s3fun):
    start_time = time.time()
    print('launching test')
    results_dir = op.join(storage_dir, 's3-test', subject)
    if not op.exists(results_dir):
        os.makedirs(results_dir)

    done_file = op.join(results_dir, 'done')
    elapsed_time = time.time() - start_time
    with open(done_file, 'w') as fid:
        fid.write(
            'Elapsed time {}'.format(
                time.strftime('%H:%M:%S', time.gmtime(elapsed_time))))
    s3fun(done_file)
    print('done')
    return True

if __name__ == '__main__':

    parser = ArgumentParser(description='tell subject')
    parser.add_argument('--subject', metavar='subject', type=str, nargs='?',
                        default=None,
                        help='the subject to extract')
    parser.add_argument('--storage-dir', metavar='storage_dir', type=str,
                        nargs='?', default=storage_dir,
                        help='the storage dir')

    args = parser.parse_args()
    storage_dir = args.storage_dir
    subject = args.subject
    start_time = time.time()
    res = test_s3(subject, storage_dir=storage_dir)
    elapsed_time = time.time() - start_time
    print('Elapsed time {}'.format(
        time.strftime('%H:%M:%S', time.gmtime(elapsed_time))))
    if not res:
        sys.exit('could not find requested files for %s' % subject)
    elif res == 'exists':
        sys.exit('requested files already for %s' % subject)
