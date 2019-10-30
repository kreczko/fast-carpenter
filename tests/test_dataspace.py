import pytest

from fast_carpenter import dataspace as ds


class DummyTree:
    def __init__(self):
        self.a = [42]
        self.b = [117]

    def array(self, name):
        return self.__dict__[name]


def test_group_with_list():
    dt = DummyTree()
    data = ds.group([dt], name='input_trees')
    assert data.notify(action=['array'], name='a')['array'] == dt.array('a')
    assert data.notify('input_trees', action=['array'], name='b')['array'] == dt.array('b')

    with pytest.raises(KeyError):
        assert data.notify('unkown_group', action=['array'], name='a')['array'] == dt.array('a')

def test_group_with_dict():
    dt1 = DummyTree()
    dt2 = DummyTree()
    dt2.a = 2323; dt2.b = 111; dt2.c = 'yes'
    trees = {'dt1':dt1, 'dt2':dt2}
    
    data = ds.group(trees, name='input_trees')
    func = 'array'
    results = data.notify(action=[func], name='a')
    results_named = data.notify('input_trees', action=['array'], name='b')
    results_onesided = data.notify(action=['array'], name='c')
    
    for name in trees:
        assert results[name][func] == trees[name].array('a')
        assert results_named[name][func] == trees[name].array('b')
        if hasattr(trees[name], 'c'):
            assert results_onesided[name][func] == trees[name].array('c')

    with pytest.raises(KeyError):
        assert data.notify('unkown_group', action=['array'], name='a')