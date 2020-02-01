import uproot

f = uproot.open('http://fast-hep-data.web.cern.ch/fast-hep-data/cms/L1T/CMS_L1T_study.root')
t1 = f['l1CaloTowerEmuTree/L1CaloTowerTree']

t1.show()

arrays = t1.arrays(namedecode="utf-8")
print('array keys', arrays.keys())
n_array_vars = len(arrays.keys())

n_branches = len(t1.keys())
n_vars = sum([len(t1[k].keys()) for k in t1.keys()])
print(f'{n_vars} variables across {n_branches} branches but {n_array_vars} variables in array dict')

array = t1['L1CaloTower']['iet'].array()
print(array)

# import pandas as pd
# df = pd.DataFrame(data=array.flatten(), columns=['L1CaloTower.iet'])

# # df = t1.pandas.df('L1CaloTower*')

# print(df)

# print(dir(t1['L1CaloTower']['iet']))

# df = t1.pandas.df('L1CaloTower.iet')

# print(df)