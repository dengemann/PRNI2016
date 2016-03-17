# Authors: Denis A. Engemann <denis.engemann@gmail.com>
#
# License: BSD (3-clause)

import numpy as np
import pandas as pd
from sklearn.model_selection import KFold
from boto.ec2.blockdevicemapping import BlockDeviceMapping, BlockDeviceType

from aws_hacks import (
    instance_run_jobs,
    make_start_script,
    get_run_parallel_script)

aws_details = pd.read_csv('aws_details.csv')
aws_access_key_id = aws_details['Access Key Id'].values[0]
aws_secret_access_key = aws_details['Secret Access Key'].values[0]

mapping = BlockDeviceMapping()
mapping["/dev/sdb"] = BlockDeviceType(ephemeral_name='ephemeral0')

df = pd.read_csv('data/unrestricted_dengemann_2_21_2016_4_40_21.csv')

n_instances = 10
abused_kfold = KFold(n_folds=n_instances)  # convenience-hack

subjects = np.array(['test-sub-%0.3d' % i for i in range(100)])

startup_script_tmp = make_start_script(
    cmd='{cmd}',  # leave this open
    repo='PRNI2016',
    anaconda_path='miniconda2',
    env='swish',
    install_pip=['boto'],
    add_swap_file=False
)

parallel_params = dict(
    script='compute_test_s3.py',  # run this script
    par_target='subject',  # for each subject
    n_par=1  # 1 job each
)

for ii, (_, test) in enumerate(abused_kfold.split(subjects)):
    this_subjects = subjects[test]

    parallel_params.update(par_args=this_subjects)
    parallel_cmd = get_run_parallel_script(parallel_params)
    code = startup_script_tmp.format(cmd=parallel_cmd)
    out = instance_run_jobs(
        code=code,
        image_id='ami-62474008',
        key_name='test-node-virginia',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        dry_run=True,
        min_count=1,
        instance_type='t2.micro',
        block_device_map=mapping,
        security_groups=['launch-wizard-1']
    )
