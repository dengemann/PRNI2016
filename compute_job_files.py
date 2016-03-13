from sklearn.model_selection import KFold
import pandas
df = pandas.read_csv('data/unrestricted_dengemann_2_21_2016_4_40_21.csv')

kfold = KFold(n_folds=10)
for ii, (_, test) in enumerate(kfold.split(df.Subject)):
    with open('subjects-%i.txt' % ii, 'w') as fid:
        fid.write('\n'.join(df.Subject.values[test].astype(str).tolist()))
