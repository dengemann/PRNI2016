# Authors: Danilo Bzdok <danilbzdok@gmail.com>
#
# License: BSD (3-clause)

"""
--------------------------------------------------------------------------------
nets_prec/NEOFAC_A/mean-R2: -0.1478
nets_prec/NEOFAC_O/mean-R2: -0.1461
nets_prec/NEOFAC_C/mean-R2: -0.1680
nets_prec/NEOFAC_N/mean-R2: -0.1546
nets_prec/NEOFAC_E/mean-R2: -0.1475
--------------------------------------------------------------------------------
nets_cov/NEOFAC_A/mean-R2: -0.1763
nets_cov/NEOFAC_O/mean-R2: -0.1573
nets_cov/NEOFAC_C/mean-R2: -0.1611
nets_cov/NEOFAC_N/mean-R2: -0.1774
nets_cov/NEOFAC_E/mean-R2: -0.1396
--------------------------------------------------------------------------------
regs_prec/NEOFAC_A/mean-R2: -0.1803
regs_prec/NEOFAC_O/mean-R2: -0.1852
regs_prec/NEOFAC_C/mean-R2: -0.1822
regs_prec/NEOFAC_N/mean-R2: -0.1981
regs_prec/NEOFAC_E/mean-R2: -0.1956
--------------------------------------------------------------------------------
regs_cov/NEOFAC_A/mean-R2: -0.1762
regs_cov/NEOFAC_O/mean-R2: -0.1852
regs_cov/NEOFAC_C/mean-R2: -0.1897
regs_cov/NEOFAC_N/mean-R2: -0.1854
regs_cov/NEOFAC_E/mean-R2: -0.2075

"""

import glob
import numpy as np
import nibabel as nib
import pandas
from sklearn.preprocessing import StandardScaler
from sklearn.cross_validation import ShuffleSplit
from sklearn.linear_model import Lasso, LassoCV
# gather the data
mask_file = nib.load('data/grey10_icbm_3mm_bin.nii.gz')

from sklearn.ensemble import RandomForestRegressor
for cur_ana in ['nets_prec', 'nets_cov', 'regs_prec', 'regs_cov']:
    print('-' * 80)
    cur_paths = glob.glob('data/fmri-rest-features/'
                          'runs-1_pcoding-LR/*/*_%s.npy' % cur_ana)
    sub_ids = np.array([int(p.split('/')[-2]) for p in cur_paths])

    beh = pandas.read_csv('data/unrestricted_dengemann_2_21_2016_4_40_21.csv')
    # neo_inds = np.array(['Compl' in col for col in beh.columns.values])
    # neo_inds = np.array(['WM_' in col for col in beh.columns.values])
    neo_inds = np.array(['NEOFAC_' in col for col in beh.columns.values])
    # thing

    print('Predicting %i columns...' % neo_inds.sum())
    contrast_names = list(beh.columns.values[neo_inds])

    # map HCP big 5 to subject dump list
    hcp_to_dump_inds = []
    for cur_id in sub_ids:
        ind = np.where(beh.values[:, 0] == cur_id)[0]
        assert len(ind) == 1
        hcp_to_dump_inds.append(ind[0])
    hcp_to_dump_inds = np.array(hcp_to_dump_inds)

    beh_scores = np.array(
        beh.values[hcp_to_dump_inds][:, neo_inds], dtype=np.float64)
    beh_titles = np.array(beh.columns[neo_inds])

    # predict
    FS_brain = []
    idx = np.triu_indices(20, 1)
    for item in cur_paths:
        item_data = np.load(item)
        FS_brain.append(item_data[idx])
    FS_brain = np.array(FS_brain)
    # FS_brain = StandardScaler().fit_transform(FS_brain)

    for i_beh in range(5):
        scores = np.nan_to_num(beh_scores[:, i_beh])[:, None]
        title = beh_titles[i_beh]

        clf = LassoCV(alpha=1.0)
        # clf = RandomForestRegressor(n_estimators=1000, max_depth=3)

        coefs = []
        r2_list = []
        folder = ShuffleSplit(n=len(scores), n_iter=100, test_size=0.1)
        y = StandardScaler().fit_transform(scores)
        for ii, (train, test) in enumerate(folder):
            scaler = StandardScaler().fit(FS_brain[train])
            X_train = scaler.transform(FS_brain[train])
            clf.fit(X=X_train, y=y[train])
            X_test = scaler.transform(FS_brain[test])
            r2 = clf.score(X_test, y[test])
            r2_insample = clf.score(X_train, y[train])
            print 'fold %i of 100 -- r2=%0.3f -- r2_ins=%0.3f' % (
                ii, r2, r2_insample)
            r2_list.append(r2)
        mean_r2 = np.mean(r2_list)
        print('%s/%s/mean-R2: %.4f' % (cur_ana, title, mean_r2))
