import uproot
import pandas as pd

f = uproot.open('tests/data/CMS_L1T_study.root')
t1 = f['l1CaloTowerTree/L1CaloTowerTree']

print(len(t1))

print('keys', t1.keys())

array = t1['L1CaloTower']['iet'].array()
print(array)

df = pd.DataFrame(data=array.flatten(), columns=['L1CaloTower.iet'])

# print(dir(t1['L1CaloTower']['iet']))

# df = t1.pandas.df('L1CaloTower.iet')

# print(df)