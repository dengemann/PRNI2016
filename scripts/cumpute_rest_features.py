# Authors: Danilo Bzdok <danilbzdok@gmail.com>
#          Denis A. Engemann <denis.engemann@gmail.com>
#
# License: BSD (3-clause)

import os
import os.path as op
from argparse import ArgumentParser

import numpy as np
import nibabel as nib
from nilearn.image import concat_imgs
from nilearn import datasets as ds
from nilearn.input_data import NiftiMapsMasker
from nilearn.input_data import NiftiLabelsMasker
from sklearn.covariance import GraphLassoCV
from nilearn.image import index_img
from nilearn.image import resample_img
from aws_lib import download_from_s3, upload_to_s3
import pandas as pd

aws_details = pd.read_csv('aws_details.csv')
aws_access_key_id = aws_details['Access Key Id'].values[0]
aws_secret_access_key = aws_details['Secret Access Key'].values[0]

aws_details = pd.read_csv('aws_hcp_details.csv')
hcp_aws_access_key_id = aws_details['Access Key Id'].values[0]
hcp_aws_secret_access_key = aws_details['Secret Access Key'].values[0]


def put_s3fun(fname, delete_if_good=True):
    good = upload_to_s3(
        aws_access_key_id, aws_secret_access_key, fname=fname,
        bucket='swish-data', key=fname)
    if good:
        print('all is good, uploaded and removing %s' % fname)
        os.remove(fname)
    else:
        print('something went wrong with %s' % fname)


def get_s3_fun(key, fname):
    return download_from_s3(hcp_aws_access_key_id, hcp_aws_secret_access_key,
                            bucket='hcp-openaccess', fname=fname, key=key)


def extract_features(subject, s3fun=put_s3fun):
    results_dir = op.join(op.curdir, 'data', subject)
    if not op.exists(results_dir):
        os.makedirs(results_dir)

    rs_files = list()
    for run_index in [1, 2]:
        fname = ('HCP_900/{0}/MNINonLinear/Results/rfMRI_REST{1}_LR/'
                 'rfMRI_REST{1}_LR.nii.gz').format(subject, run_index)
        out_fname = fname.split('/')[-1]
        if not op.exists(out_fname):
            print('Trying to get %s' % fname)
            if get_s3_fun(key=fname, fname=out_fname):
                rs_files.append(out_fname)
            print('Done')
        else:
            rs_files.append(out_fname)

    print('starting feature extraction')
    # grab the LR and RL phase encoding rest images from one subject

    mask_file = nib.load('anat_data/grey10_icbm_3mm_bin.nii.gz')

    #  may take a while ! -> unpacks 2 1TB gz archives
    #  timeit on MBP: 1 loops, best of 1: 2min 13s
    print('concatenating niftis')
    all_sub_rs_maps = concat_imgs(rs_files, verbose=2)

    cur_shape = all_sub_rs_maps.get_data().shape
    size_in_GB = all_sub_rs_maps.get_data().nbytes / 1e9
    print('% rs images: %.2f GB' % (cur_shape[-1], size_in_GB))
    print('done')
    #########################################################################
    # dump network projections
    #########################################################################

    # retrieve network projections
    smith_pkg = ds.fetch_atlas_smith_2009()
    icas_path = smith_pkg['rsn20']

    print('extracting ica maps')
    nmm = NiftiMapsMasker(
        mask_img=mask_file, maps_img=icas_path, resampling_target='mask',
        standardize=True, detrend=True)
    nmm.fit()

    fname = op.join(results_dir, 'dbg_ica_maps.nii.gz')
    nmm.maps_img_.to_filename(fname)
    s3fun(fname)
    print('done')

    print('extracting network projections')
    FS_netproj = nmm.transform(all_sub_rs_maps)
    fname = op.join(results_dir, '%i_nets_timeseries' % subject)
    np.save(fname, FS_netproj)
    s3fun(fname)
    print('done')

    # compute network sparse inverse covariance
    try:
        print('extracting network sparse inverse cov')
        gsc_nets = GraphLassoCV(verbose=2, alphas=20)
        gsc_nets.fit(FS_netproj)
        for fname in ('%i_nets_cov' % subject, '%i_nets_prec' % subject):
            fname = op.join(results_dir, fname)
            np.save(
                fname,
                gsc_nets.covariance_ if 'cov' in fname else
                gsc_nets.precision_)
            s3fun(fname, gsc_nets.precision_)
        print('done')
    except:
        pass

    ###########################################################################
    # dump region poolings
    ###########################################################################

    crad = ds.fetch_atlas_craddock_2012()
    # Craddock 200 region atlas
    # atlas_nii = index_img(crad['scorr_mean'], 19)
    # Craddock 100 region atlas
    atlas_nii = index_img(crad['scorr_mean'], 9)

    r_atlas_nii = resample_img(
        img=atlas_nii,
        target_affine=mask_file.get_affine(),
        target_shape=mask_file.shape,
        interpolation='nearest'
    )
    print('extracting atlas')
    fname = 'debug_ratlas.nii.gz'
    fname = op.join(results_dir, fname)
    r_atlas_nii.to_filename(fname)
    s3fun(fname)
    print('done')

    print('extracting sub region maps')
    nlm = NiftiLabelsMasker(
        labels_img=r_atlas_nii, mask_img=mask_file,
        standardize=True, detrend=True)

    nlm.fit()
    FS_regpool = nlm.transform(all_sub_rs_maps)
    fname = '%i_regs_timeseries' % subject
    fname = op.join(results_dir, fname)
    np.save(fname, FS_regpool)
    s3fun(fname)
    print('done')
    # compute network sparse inverse covariance

    try:
        print('extracting regpool sparse inverse cov')
        gsc_nets = GraphLassoCV(verbose=2, alphas=20)
        gsc_nets.fit(FS_regpool)
        for fname in ('%i_regs_cov' % subject, '%i_regs_prec' % subject):
            fname = op.join(results_dir, fname)
            np.save(
                fname,
                gsc_nets.covariance_ if 'cov' in fname else
                gsc_nets.precision_)
            s3fun(fname)
        print('done')
    except:
        pass
    print('cleaning up')
    for fname in rs_files:
        os.remove(fname)
    print('done')

if __name__ == '__main__':

    parser = ArgumentParser(description='tell subject')
    parser.add_argument('--subject', metavar='subject', type=str, nargs='?',
                        default=None,
                        help='the subject to extract')

    args = parser.parse_args()
    subject = args.subject
    extract_features(subject)
