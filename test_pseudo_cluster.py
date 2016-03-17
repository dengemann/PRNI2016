import pandas as pd
from sklearn.model_selection import KFold
from aws_lib import (
    instance_run_jobs, get_run_parallel_script, 
    get_test_script)

aws_details = pd.read_csv('aws_details.csv')
aws_access_key_id = aws_details['Access Key Id'].values[0]
aws_secret_access_key = aws_details['Secret Access Key'].values[0]

aws_details = pd.read_csv('aws_hcp_details.csv')
hcp_aws_access_key_id = aws_details['Access Key Id'].values[0]
hcp_aws_secret_access_key = aws_details['Secret Access Key'].values[0]

df = pd.read_csv('data/unrestricted_dengemann_2_21_2016_4_40_21.csv')

n_instances = 10
kfold = KFold(n_folds=n_instances)
meg_subjects = df[df.MEG_AnyData].Subject.values

for ii, (_, test) in enumerate(kfold.split(meg_subjects)):
    subjects = meg_subjects[test].astype(str).tolist()
    script_str = get_run_parallel_script(subjects, 'compute_test_s3.py')
    out = instance_run_jobs(
        script_str,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key, dry_run=False)
