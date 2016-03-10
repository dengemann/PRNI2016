import os
import glob
import numpy as np
import nibabel as nib
from nilearn.image import concat_imgs
from nilearn import datasets as ds
from nilearn.input_data import NiftiMapsMasker
from nilearn.input_data import NiftiLabelsMasker
from sklearn.covariance import GraphLassoCV
from nilearn.image import index_img
from nilearn.image import resample_img
from aws_lib import upload_to_s3
import pandas as pd

aws_details = pd.read_csv('aws_details.csv')
aws_access_key_id = aws_details['Access Key Id']
aws_secret_access_key = aws_details['Secret Access Key']


def s3fun(fname, delete_if_good=True):
    good = upload_to_s3(
        aws_access_key_id, aws_secret_access_key, fname=fname,
        bucket='swish-data', key=fname)
    if good:
        print('all is good, uploaded and removing %s' % fname)
        os.remove(fname)
    else:
        print('something went wrong with %s' % fname)


def extract_features(subject, results_dir, s3fun=s3fun):
    os.mkdir(results_dir)
    rs_files = glob.glob(
        '%s/MNINonLinear/Results/rfMRI_REST1_??/rfMRI_REST1_??.nii.gz' %
        subject)
    # grab the LR and RL phase encoding rest images from one subject
    mask_file = nib.load('data/grey10_icbm_3mm_bin.nii.gz')

    #  may take a while ! -> unpacks 2 1TB gz archives
    #  timeit on MBP: 1 loops, best of 1: 2min 13s
    all_sub_rs_maps = concat_imgs(rs_files)

    cur_shape = all_sub_rs_maps.get_data().shape
    size_in_GB = all_sub_rs_maps.get_data().nbytes / 1e9
    print('% rs images: %.2f GB' % (cur_shape[-1], size_in_GB))

    #########################################################################
    # dump network projections
    #########################################################################

    # retrieve network projections
    smith_pkg = ds.fetch_atlas_smith_2009()
    icas_path = smith_pkg['rsn20']

    nmm = NiftiMapsMasker(
        mask_img=mask_file, maps_img=icas_path, resampling_target='mask',
        standardize=True, detrend=True)
    nmm.fit()

    fname = 'dbg_ica_maps.nii.gz'
    nmm.maps_img_.to_filename(fname)
    s3fun(fname)

    FS_netproj = nmm.transform(all_sub_rs_maps)
    fname = '%i_nets_timeseries' % subject
    np.save(fname, FS_netproj)
    s3fun(fname)

    # compute network sparse inverse covariance
    try:
        gsc_nets = GraphLassoCV(verbose=2, alphas=20)
        gsc_nets.fit(FS_netproj)

        for fname in ('%i_nets_cov' % subject, '%i_nets_prec' % subject):
            np.save(fname, gsc_nets.covariance_)
            s3fun(fname, gsc_nets.precision_)

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
    fname = 'debug_ratlas.nii.gz'
    r_atlas_nii.to_filename(fname)
    s3fun(fname)
    nlm = NiftiLabelsMasker(
        labels_img=r_atlas_nii, mask_img=mask_file,
        standardize=True, detrend=True)

    nlm.fit()
    FS_regpool = nlm.transform(all_sub_rs_maps)
    fname = '%i_regs_timeseries' % subject
    np.save(fname, FS_regpool)

    # compute network sparse inverse covariance

    try:
        gsc_nets = GraphLassoCV(verbose=2, alphas=20)
        gsc_nets.fit(FS_regpool)
        for fname in ('%i_regs_cov' % subject, '%i_regs_prec' % subject):
            np.save(fname, gsc_nets.covariance_)
            s3fun(fname, gsc_nets.precision_)
    except:
        pass
