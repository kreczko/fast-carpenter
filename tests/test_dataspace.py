from collections import namedtuple
import pytest
import uproot

from fast_carpenter import dataspace as ds
from fast_carpenter.masked_tree import MaskedUprootTree
# from fast_carpenter.event_builder import EventRanger


class DummyTree:
    def __init__(self):
        self.a = [42]
        self.b = [117]

    def array(self, item):
        return self.__dict__[item]

    def add_var(self, name, value):
        self.__dict__[name] = value

    def get(self, name):
        return self.__dict__[name]

    def __len__(self):
        return len(self.__dict__)

    def __contains__(self, name):
        return name in self.__dict__ or hasattr(self, name)


@pytest.fixture
def dataspace_from_dict():
    dt1 = DummyTree()
    dt2 = DummyTree()
    dt2.a = 2323; dt2.b = 111
    dt2.add_var('c', 'yes')
    trees = {'dt1':dt1, 'dt2':dt2}

    data = ds.group(trees, name='input_trees')
    return data, trees

@pytest.fixture
def complex_dataspace():
    dt1 = DummyTree()
    dt2 = DummyTree()
    dt2.a = 2323; dt2.b = 111
    dt2.add_var('c', 'yes')
    dt2.add_var('emu.electron.pt', 420.2)
    trees = {'path1/dt1':dt1, 'path2/dt2':dt2}
    return ds.group(trees, name='input_trees'), trees


@pytest.fixture
def dataspace_from_single_tree(infile):
    trees = {infile.name.decode('utf-8'): infile}
    return ds.group(trees, name='input_trees'), trees

@pytest.fixture
def owner():
    Owner = namedtuple(
        'Owner',
        ['start_block', 'iblock', 'nevents_per_block', 'nblocks', 'nevents_in_tree']
    )
    return  Owner(
        0, 1, 10000, 1, 10000,
    )


@pytest.fixture
def dataspace_from_multiple_trees(owner):
    filename = "tests/data/CMS_L1T_study.root"
    trees = ['l1CaloTowerEmuTree/L1CaloTowerTree', 'l1CaloTowerTree/L1CaloTowerTree']
    f = uproot.open(filename)
    # ranges = EventRanger()
    # trees = {tree: MaskedUprootTree(f[tree], ranges) for tree in trees}
    trees = {tree: f[tree] for tree in trees}
    data = ds.group(trees, name='input_trees')
    # ranges.set_owner(owner)
    return data, trees

def test_group_with_list():
    dt = DummyTree()
    data = ds.group([dt], name='input_trees')
    assert data.notify(action=['array'], item='a')['array'] == dt.array('a')
    assert data.notify('input_trees', action=['array'], item='b')['array'] == dt.array('b')

    with pytest.raises(KeyError):
        assert data.notify('unkown_group', action=['array'], item='a')['array'] == dt.array('a')

def test_group_with_dict(dataspace_from_dict):
    data, trees = dataspace_from_dict
    func = 'array'
    results = data.notify(group=None, action=[func], item='a')
    results_named = data.notify('input_trees', action=['array'], item='b')
    results_onesided = data.notify(action=['array'], item='c')

    for name in trees:
        assert results[name][func] == trees[name].array('a')
        assert results_named[name][func] == trees[name].array('b')
        if hasattr(trees[name], 'c'):
            assert results_onesided[name][func] == trees[name].array('c')

    with pytest.raises(KeyError):
        assert data.notify('unkown_group', action=['array'], item='a')

def test_find_group_and_item(complex_dataspace):
    data, _ = complex_dataspace
    group, item = data.find_group_and_item('path2.dt2.emu.electron.pt')
    assert group._name == 'path2/dt2'
    assert item == 'emu.electron.pt'

def test_array(complex_dataspace):
    data, trees = complex_dataspace
    result = data.array('path2.dt2.emu.electron.pt')
    assert result == trees['path2/dt2'].array('emu.electron.pt')

def test_complex_access(complex_dataspace):
    data, trees = complex_dataspace
    func = 'get'
    results = data.notify(action=[func], name='a')
    for name in trees:
        assert results[name][func] == trees[name].get('a')

def test_complex_access_with_wrapper(complex_dataspace):
    data, trees = complex_dataspace
    func = 'array'
    result = data.notify('input_trees', action=[func], item='path2.dt2.emu.electron.pt')
    assert result['path2/dt2'][func] == trees['path2/dt2'].array('emu.electron.pt')


def test_contains(complex_dataspace, dataspace_from_single_tree, dataspace_from_multiple_trees):
    ds, _ = complex_dataspace
    assert 'path1.dt1.a' in ds
    assert 'path2.dt2.emu.electron.pt' in ds
    assert 'DoesNotExist' not in ds
    ds, _ = dataspace_from_single_tree
    assert 'events.Muon_Py' in ds
    assert 'DoesNotExist' not in ds

    ds, trees = dataspace_from_multiple_trees
    assert 'L1CaloTower' in trees['l1CaloTowerTree/L1CaloTowerTree']
    print(trees['l1CaloTowerTree/L1CaloTowerTree']['L1CaloTower']['iet'].array())
    print(trees['l1CaloTowerTree/L1CaloTowerTree'].array('L1CaloTower.iet'))
    # print(trees['l1CaloTowerTree/L1CaloTowerTree'].array('L1CaloTower', ['et']))
    assert 'l1CaloTowerTree.L1CaloTowerTree.L1CaloTower.et' in ds
    assert 'l1CaloTowerEmuTree.L1CaloTowerTree.L1CaloTower.et' in ds
    assert 'DoesNotExist' not in ds
