# Authors: Denis A. Engemann <denis.engemann@gmail.com>
#
# License: BSD (3-clause)
import sys
import time
import os
import os.path as op


from aws_lib import download_from_s3
import pandas as pd

bucket = 'swish-data'
prefix = 'fmri-rest-features/runs-1_pcoding-LR'

aws_details = pd.read_csv('aws_details.csv')
aws_access_key_id = aws_details['Access Key Id'].values[0]
aws_secret_access_key = aws_details['Secret Access Key'].values[0]

aws_details = pd.read_csv('aws_hcp_details.csv')
hcp_aws_access_key_id = aws_details['Access Key Id'].values[0]
hcp_aws_secret_access_key = aws_details['Secret Access Key'].values[0]

df = pd.read_csv('data/unrestricted_dengemann_2_21_2016_4_40_21.csv')

out_dir = 'data'


def get_bucket_paths(prefix, subject):

    fnames = [
        '{}_nets_cov.npy',
        '{}_nets_prec.npy',
        '{}_nets_timeseries.npy',
        '{}_regs_cov.npy',
        '{}_regs_prec.npy',
        '{}_regs_timeseries.npy',
        'dbg_ica_maps.nii.gz',
        'debug_ratlas.nii.gz'
    ]
    out = list()
    for fname in fnames:
        if '{}' in fname:
            fname = fname.format(subject)
        fname = op.join(prefix, subject, fname)
        out.append(fname)
    return out


def check_done(prefix, subject):
    key = op.join(prefix, subject, 'done')
    return download_from_s3(aws_access_key_id, aws_secret_access_key,
                            bucket='swish-data', fname='test', key=key,
                            dry_run=True, host='s3.eu-central-1.amazonaws.com')


def get_s3_fun(key, fname):
    return download_from_s3(aws_access_key_id, aws_secret_access_key,
                            bucket='swish-data', fname=fname, key=key,
                            dry_run=False,
                            host='s3.eu-central-1.amazonaws.com')


def get_s3_results():
    failed = list()
    for subject in df.Subject.astype(str):
        this_out_dir = op.join(out_dir, prefix, subject)
        if not op.exists(this_out_dir):
            os.makedirs(this_out_dir)
        if check_done(prefix=prefix, subject=subject):
            for fname in get_bucket_paths(prefix=prefix, subject=subject):
                out_fname = op.join('data', fname)
                if not op.exists(out_fname):
                    if not get_s3_fun(  # XXX paths not generalized
                            key=fname, fname=out_fname):
                        failed.append({'subject': subject, 'key': fname})
    failed = df.DataFrame(failed)
    return failed


if __name__ == '__main__':

    start_time = time.time()
    res = get_s3_results()
    elapsed_time = time.time() - start_time
    print('Elapsed time {}'.format(
        time.strftime('%H:%M:%S', time.gmtime(elapsed_time))))
    if len(res) > 0:
        res.to_csv('fmri_rest_failed_subjects.csv')
        sys.exit('could not find requested files for %s subjects' % len(res))
