from collections import namedtuple
from hypothesis import given
from hypothesis_fspaths import fspaths
import hypothesis.strategies as st
import inspect
import pytest
import types

import uproot

import fast_carpenter.dataspace as ds
from fast_carpenter.masked_tree import MaskedUprootTree
from fast_carpenter.event_builder import EventRanger


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

    # def __item__(self, key):
    #     return self._vars[key]

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
    filename = "tests/data/CMS_L1T_study.root"
    trees = ['l1CaloTowerEmuTree/L1CaloTowerTree', 'l1CaloTowerTree/L1CaloTowerTree']
    f = uproot.open(filename)
    ranges = EventRanger()
    # trees = {tree: MaskedUprootTree(f[tree], ranges) for tree in trees}
    trees = {tree: f[tree] for tree in trees}
    data = ds.group('input_trees', trees)
    ranges.set_owner(owner)
    return data, trees


@pytest.fixture
def element():
    class Element:

        def __init__(self):
            self._content = [1, 2, 3]

        def array(self):
            return self.content

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


@given(
    st.dictionaries(
        fspaths(allow_pathlike=False),
        st.one_of(st.from_type(type).flatmap(st.from_type)
                  .filter(lambda x: not isinstance(x, (type(None), bool)))),
        min_size=2,
        max_size=10,
    )
)
def test_elements_of_different_type(elements):
    assert not ds.check_all_elements_of_same_type(elements)


def test_invalid_elements():
    with pytest.raises(ValueError):
        ds.DataSpace('test', [])

    with pytest.raises(ValueError):
        ds.DataSpace('test', [int(2), float(4)])


def test_methods(dataspace, element):
    ds_methods = [m for m, _ in inspect.getmembers(dataspace, predicate=inspect.ismethod)]
    e_methods = [m for m, _ in inspect.getmembers(element, predicate=inspect.ismethod)]
    # ds_methods = dir(dataspace)
    # e_methods = dir(element)
    assert ds_methods == e_methods


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
