import glob
import numpy as np
import nibabel as nib
from nilearn.image import concat_imgs

# grab the LR and RL phase encoding rest images from one subject
sub_id = 100307
rs_files = glob.glob('/Volumes/TRESOR/neurospin/Volumes/DANILO2/neurospin/population/HCP/S500-1/%i/MNINonLinear/Results/rfMRI_REST1_??/rfMRI_REST1_??.nii.gz' % sub_id)


mask_file = nib.load('grey10_icbm_3mm_bin.nii.gz')

# may take a while ! -> unpacks 2 1TB gz archives
# timeit on MBP: 1 loops, best of 1: 2min 13s 
all_sub_rs_maps = concat_imgs(rs_files)
cur_shape = all_sub_rs_maps.get_data().shape
size_in_GB = all_sub_rs_maps.get_data().nbytes / 1e9

print('% rs images: %.2f GB' % (cur_shape[-1], size_in_GB))

###############################################################################
# dump network projections
###############################################################################

# retrieve network projections
from nilearn import datasets as ds
smith_pkg = ds.fetch_atlas_smith_2009()
icas_path = smith_pkg['rsn20']

from nilearn.input_data import NiftiMapsMasker
nmm = NiftiMapsMasker(
    mask_img=mask_file, maps_img=icas_path, resampling_target='mask',
    standardize=True, detrend=True)
nmm.fit()
nmm.maps_img_.to_filename('dbg_ica_maps.nii.gz')

FS_netproj = nmm.transform(all_sub_rs_maps)
np.save('%i_nets_timeseries' % sub_id, FS_netproj)

# compute network sparse inverse covariance
from sklearn.covariance import GraphLassoCV
from nilearn.image import index_img
from nilearn import plotting

try:
    gsc_nets = GraphLassoCV(verbose=2, alphas=20)
    gsc_nets.fit(FS_netproj)

    np.save('%i_nets_cov' % sub_id, gsc_nets.covariance_)
    np.save('%i_nets_prec' % sub_id, gsc_nets.precision_)
except:
    pass

###############################################################################
# dump region poolings
###############################################################################
from nilearn.image import resample_img

crad = ds.fetch_atlas_craddock_2012()
# atlas_nii = index_img(crad['scorr_mean'], 19)  # Craddock 200 region atlas
atlas_nii = index_img(crad['scorr_mean'], 9)  # Craddock 100 region atlas

r_atlas_nii = resample_img(
    img=atlas_nii,
    target_affine=mask_file.get_affine(),
    target_shape=mask_file.shape,
    interpolation='nearest'
)
r_atlas_nii.to_filename('debug_ratlas.nii.gz')

from nilearn.input_data import NiftiLabelsMasker
nlm = NiftiLabelsMasker(
    labels_img=r_atlas_nii, mask_img=mask_file,
    standardize=True, detrend=True)

nlm.fit()
FS_regpool = nlm.transform(all_sub_rs_maps)
np.save('%i_regs_timeseries' % sub_id, FS_regpool)

# compute network sparse inverse covariance
from sklearn.covariance import GraphLassoCV
from nilearn.image import index_img
from nilearn import plotting

try:
    gsc_nets = GraphLassoCV(verbose=2, alphas=20)
    gsc_nets.fit(FS_regpool)

    np.save('%i_regs_cov' % sub_id, gsc_nets.covariance_)
    np.save('%i_regs_prec' % sub_id, gsc_nets.precision_)
except:
    pass