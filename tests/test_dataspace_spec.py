from collections import namedtuple
from hypothesis import given
from hypothesis_fspaths import fspaths
import hypothesis.strategies as st
import inspect
import pytest
import types

from numpy.testing import assert_array_equal
import pandas as pd
import uproot

import fast_carpenter.dataspace as ds
from fast_carpenter.masked_tree import MaskedUprootTree
from fast_carpenter.backends.alphatwirl import EventRanger


class DummyTree:

    def __init__(self):
        self.a = [42]
        self.b = [117]
        self._vars = {'a': self.a, 'b': self.b}

    def array(self, item):
        return self.__dict__[item]

    def add_var(self, name, value):
        self._vars[name] = value
        self.__dict__[name] = value

    def get(self, name):
        return self._vars[name]

    def __len__(self):
        return len(self._vars)

    def __contains__(self, name):
        return name in self._vars or hasattr(self, name)

    def __getitem__(self, key):
        return self._vars[key]

    def keys(self):
        return self._vars.keys()


@pytest.fixture
def dataspace_from_dict():
    dt1 = DummyTree()
    dt2 = DummyTree()
    dt2.a = 2323
    dt2.b = 111
    dt2.add_var('c', 'yes')
    trees = {'dt1': dt1, 'dt2': dt2}

    data = ds.group('input_trees', trees)
    return data, trees


@pytest.fixture
def complex_dataspace():
    dt1 = DummyTree()
    dt2 = DummyTree()
    dt2.a = 2323
    dt2.b = 111
    dt2.add_var('c', 'yes')
    dt2.add_var('emu.electron.pt', 420.2)
    trees = {'path1/dt1': dt1, 'path2/dt2': dt2}
    return ds.group('input_trees', trees), trees


@pytest.fixture
def dataspace_from_single_tree(infile):
    trees = {infile.name.decode('utf-8'): infile}
    return ds.group('input_trees', trees), trees


@pytest.fixture
def owner():
    Owner = namedtuple(
        'Owner',
        ['start_block', 'iblock', 'nevents_per_block', 'nblocks', 'nevents_in_tree']
    )
    return Owner(
        0, 1, 10000, 1, 10000,
    )


@pytest.fixture
def dataspace_from_multiple_trees(owner):
    filename = "http://fast-hep-data.web.cern.ch/fast-hep-data/cms/L1T/CMS_L1T_study.root"
    trees = ['l1CaloTowerEmuTree/L1CaloTowerTree', 'l1CaloTowerTree/L1CaloTowerTree']

    f = uproot.open(filename)
    trees = {tree: f[tree] for tree in trees}
    data = ds.from_paths([filename], trees)
    ranges = EventRanger()
    ranges.set_owner(owner)
    return data, trees


@pytest.fixture
def element():
    class Element:

        def __init__(self):
            self._content = [1, 2, 3]

        def array(self):
            return self._content

    return Element()


@pytest.fixture
def dataspace(element):
    elements = {'%d'.format(i): element for i in range(3)}
    return ds.DataSpace('test', elements)

# TODO: implement multiple types


@given(st.dictionaries(
    fspaths(allow_pathlike=False),
    st.integers(),
    min_size=2,
    # max_size=10
)
)
def test_elements_of_same_type(elements):
    assert ds.check_all_elements_of_same_type(elements)


@given(st.builds(zip,
                 st.lists(st.text(min_size=1, max_size=10),
                          min_size=2,
                          unique=True),
                 st.lists(st.from_type(type)
                          .flatmap(st.from_type)
                          .filter(lambda x: not isinstance(x, (type(None)))),
                          min_size=2,
                          unique_by=lambda x: type(x),
                          ))
       .map(dict))
def test_elements_of_different_type(elements):
    assert not ds.check_all_elements_of_same_type(elements)


def test_invalid_elements():
    with pytest.raises(ValueError):
        ds.DataSpace('test', [])

    with pytest.raises(ValueError):
        ds.DataSpace('test', [int(2), float(4)])


# TODO: in next version?
# def test_methods(dataspace, element):
#     ds_methods = [m for m, _ in inspect.getmembers(dataspace, predicate=inspect.ismethod)]
#     e_methods = [m for m, _ in inspect.getmembers(element, predicate=inspect.ismethod)]
#     # ds_methods = dir(dataspace)
#     # e_methods = dir(element)
#     assert ds_methods == e_methods


def test_index(dataspace_from_dict):
    ds, trees = dataspace_from_dict
    assert 'input_trees' in ds


def test_contains(complex_dataspace):
    ds, _ = complex_dataspace
    assert 'input_trees.path1.dt1.a' in ds
    assert 'input_trees.path1/dt1.a' in ds
    assert 'path1.dt1.a' in ds
    assert 'path2.dt2.emu.electron.pt' in ds
    assert 'DoesNotExist' not in ds


def test_contains_with_single_tree_from_file(dataspace_from_single_tree):
    ds, _ = dataspace_from_single_tree
    assert 'input_trees.events.Muon_Py' in ds
    assert 'events.Muon_Py' in ds
    assert 'DoesNotExist' not in ds


def test_contains_with_multiple_trees_from_file(dataspace_from_multiple_trees):
    ds, trees = dataspace_from_multiple_trees
    assert 'L1CaloTower' in trees['l1CaloTowerTree/L1CaloTowerTree']

    assert 'l1CaloTowerTree/L1CaloTowerTree' in ds
    assert 'l1CaloTowerTree.L1CaloTowerTree' in ds

    assert 'l1CaloTowerTree/L1CaloTowerTree.L1CaloTower' in ds
    assert 'l1CaloTowerTree.L1CaloTowerTree.L1CaloTower' in ds

    assert 'l1CaloTowerTree/L1CaloTowerTree.L1CaloTower.et' in ds
    assert 'l1CaloTowerTree.L1CaloTowerTree.L1CaloTower.et' in ds
    assert 'l1CaloTowerEmuTree.L1CaloTowerTree.L1CaloTower.et' in ds

    assert 'DoesNotExist' not in ds


def test_array(complex_dataspace):
    data, trees = complex_dataspace
    result = data['path2.dt2.emu.electron.pt']
    assert result == trees['path2/dt2'].array('emu.electron.pt')


def test_complex_access(complex_dataspace):
    data, trees = complex_dataspace
    for name in trees:
        assert data[name]['a'] == trees[name]['a']
        assert data[name + '.a'] == trees[name]['a']


def test_complex_access_with_wrapper(complex_dataspace):
    data, trees = complex_dataspace
    result = data['path2.dt2.emu.electron.pt']

    assert result == trees['path2/dt2'].array('emu.electron.pt')


def test_element_method(complex_dataspace):
    ds, _ = complex_dataspace
    assert 'path1.dt1.a' in ds
    assert 'path1.dt1.notyethere' not in ds
    ds.notify(actions=['add_var'], name='notyethere', value=42.2)
    assert 'path1.dt1.notyethere' in ds
    assert ds['path1.dt1.notyethere'] == 42.2

def test_access_with_multiple_trees_from_file(dataspace_from_multiple_trees):
    ds, trees = dataspace_from_multiple_trees
    tree_names = ['l1CaloTowerEmuTree/L1CaloTowerTree', 'l1CaloTowerTree/L1CaloTowerTree']
    vars = ['et', 'iet']
    for t in tree_names:
        for v in vars:
            ds_array = ds[t + '.L1CaloTower.' + v].array()
            tree_array = trees[t]['L1CaloTower'][v].array()
            assert list(ds_array.content) == list(tree_array.content)

def test_pandas(dataspace_from_multiple_trees):
    ds, trees = dataspace_from_multiple_trees
    df = ds.pandas.df(ds, ['l1CaloTowerEmuTree.L1CaloTowerTree.L1CaloTower.iet'], flatten=True)
    assert df is not None
    assert len(df) == 1319442

    tree_array = trees['l1CaloTowerEmuTree/L1CaloTowerTree']['L1CaloTower']['iet'].array()
    tree_df = pd.DataFrame(data=tree_array.flatten(), columns=['L1CaloTower.iet'])

    assert len(tree_df) == len(df)
    assert_array_equal(df['l1CaloTowerEmuTree.L1CaloTowerTree.L1CaloTower.iet'], tree_df['L1CaloTower.iet'])


def test_len_from_multiple_trees(dataspace_from_multiple_trees):
    ds, trees = dataspace_from_multiple_trees
    for tree in trees.values():
        assert len(tree) == len(ds)
