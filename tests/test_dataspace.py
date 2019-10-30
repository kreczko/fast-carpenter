import pytest

from fast_carpenter import dataspace as ds


class DummyTree:
    def __init__(self):
        self.a = [42]
        self.b = [117]

    def array(self, name):
        return self.__dict__[name]


def test_group():
    dt = DummyTree()
    data = ds.group([dt], name='input_trees')
    assert data.notify(action=['array'], name='a')['array'] == dt.array('a')
    assert data.notify('input_trees', action=['array'], name='b')['array'] == dt.array('b')

    with pytest.raises(KeyError):
        assert data.notify('unkown_group', action=['array'], name='a')['array'] == dt.array('a')
