import config as cfg

import numpy as np
import pandas as pd

from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.cross_validation import StratifiedShuffleSplit, cross_val_score
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.dummy import DummyClassifier

df_ur = pd.read_csv('data/unrestricted_dengemann_2_21_2016_4_40_21.csv')
df_re = pd.read_csv('data/RESTRICTED_dengemann_2_21_2016_5_7_50.csv')

df = pd.concat([df_ur, df_re], axis=1)

""" step 1 -- create a subsample of twins

- twin/non-twin indexer
- mother id indexer
- check if a sibling is in sample
"""

df['has_sibling'] = False
df['sibgling_index'] = 0
for key, index in df.groupby(['Mother_ID', 'Twin_Stat']).groups.items():
    has_sibling = (len(index) == 2)
    for ii, ind in enumerate(index):
        df.loc[ind, 'has_sibling'] = has_sibling
        if has_sibling:
            df.loc[ind, 'sibgling_index'] = ii + 1

print pd.crosstab(df.Twin_Stat, df.has_sibling)
"""
has_sibling  False  True
Twin_Stat
NotTwin        320    174
Twin            80    396
"""

dff = df[df.sibgling_index.isin([1])]
dff = dff[~dff.MEG_AnyData]
dff = dff[dff[cfg.completion].min(1)]
dff = dff[dff.Gender != 'U']
dff = dff[dff[cfg.variables].notnull().min(1)]

print pd.crosstab(dff.Twin_Stat, dff.Gender)
"""
has_sibling  False  True
Twin_Stat
NotTwin        318     87
Twin            77    152
"""

# Y = StandardScaler().fit_transform(dff[cfg.variables])
Y = dff[cfg.variables].values
X = [LabelEncoder().fit_transform(dff['Gender']),
     StandardScaler().fit_transform(dff['Age_in_Yrs'])]
X = np.array(X).T
lm = LinearRegression().fit(X, Y)
X_res = Y - lm.predict(X)

# X_pca = KernelPCA(kernel='poly', n_components=5, degree=3).fit_transform(X_res)
# X_pca = SparsePCA(alpha=2., n_components=5).fit_transform(X_res)
"""
X_pca = PCA(n_components=15).fit_transform(X_res)
X_df_pca = pd.DataFrame()
for ii, ax in enumerate(X_pca.T, 1):
    X_df_pca['PC%i' % ii] = ax
X_df_pca['twin_status'] = dff['Twin_Stat']

import seaborn as sns
sns.set()
sns.pairplot(X_df_pca[['PC1', 'PC12', 'PC3', 'twin_status']], hue="twin_status")
"""
y = LabelEncoder().fit_transform(dff['Twin_Stat'])

classif = dict(
    rf=RandomForestClassifier(
        n_estimators=5000, criterion="entropy", max_depth=6, max_features=1),
    et=ExtraTreesClassifier(
        n_estimators=5000, criterion="entropy", max_depth=6, max_features=1),
    lda=LinearDiscriminantAnalysis(),
    lr=LogisticRegression(class_weight='auto'),
    dummy_stratified=DummyClassifier(strategy='stratified'),
    dummy_most_frequent=DummyClassifier(strategy='most_frequent'),
    dummy_prior=DummyClassifier(strategy='prior'),
    dummy_uniform=DummyClassifier(strategy='uniform'),
)

cv = StratifiedShuffleSplit(y, n_iter=100, random_state=42)
psy_scores = dict()
for key, est in classif.items():
    psy_scores[key] = cross_val_score(
        estimator=est, X=X_res, y=y, cv=cv, scoring='roc_auc', n_jobs=8)
    print key, ': ', psy_scores[key].mean()


dff2 = df[df.sibgling_index.isin([0, 1])]
dff2 = dff2[~dff2.MEG_AnyData]
dff2 = dff2[dff2.Gender != 'U']
dff2 = dff2[dff2[cfg.completion[0]]]
# dff
Y_fs = dff2[cfg.brain_vars].values
X = [LabelEncoder().fit_transform(dff2['Gender']),
     StandardScaler().fit_transform(dff2['Age_in_Yrs'])]
X = np.array(X).T
lm = LinearRegression().fit(X, Y_fs)
X_fs_res = Y_fs - lm.predict(X)
y = LabelEncoder().fit_transform(dff2['Twin_Stat'])

fs_scores = dict()
for key, est in classif.items():
    fs_scores[key] = cross_val_score(
        estimator=make_pipeline(StandardScaler(), est),
        X=X_fs_res, y=y, cv=cv, scoring='roc_auc', n_jobs=8)
    print key, ': ', fs_scores[key].mean()

for key, val in psy_scores.items():
    print key, ': ', val.mean()

for key, val in fs_scores.items():
    print key, ': ', val.mean()
