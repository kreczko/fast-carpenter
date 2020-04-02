"""
Specification
--------------
The DataSpace is a composable container for any objects.

- elements (sub-spaces) can be accessed via composable indices:
    `ds['path1/path2']['obj1.var'], ds['path1/path2.obj1.var'], ds['path1.path2.obj1.var']` are equivalent
- function calls on a DataSpace or sub-space are redirected to the underlying objects and return a generator
- objects under the same DataSpace need to be of the same type, i.e. have the same API
- an object is contained  in a DataSpace if the object identifier can be found in the
    DataSpace index or the indices of sub-spaces
"""
import functools
import inspect

import numpy as np
import pandas as pd

import uproot

# TODO: Automatically managed caches with possibility of using memcached (useful for multicore)


def check_all_elements_of_same_type(elements):
    if not elements:
        return False
    if not isinstance(elements, dict):
        raise ValueError('elements need to be of type "dict"')
    t = type(next(iter(elements.values())))
    return all(type(e) is t for e in elements.values())


def group(group_name, elements):
    """
        Create group from the given elements and give it a name
    """
    if not isinstance(elements, dict):
        raise ValueError('elements need to be of type "dict"')

    newGroup = DataSpace(name=group_name)
    groups = {}
    for name, item in elements.items():
        name = name.decode('utf-8') if type(name) is bytes else name
        if isinstance(item, dict):
            tmpGroup = group(name, item)
            groups[name] = tmpGroup
        else:
            newGroup._add(name, item)
    newGroup._update(groups)
    return newGroup


def from_file_paths(file_paths, treeNames):
    if len(file_paths) != 1:
        # TODO - support multiple paths
        raise AttributeError("Multiple file paths not yet supported")

    try:
        rootfile = uproot.open(file_paths[0])
        trees = {treeName: rootfile[treeName] for treeName in treeNames}
    except MemoryError:
        rootfile = uproot.open(
            file_paths[0], localsource=uproot.FileSource.defaults)
        trees = {treeName: rootfile[treeName] for treeName in treeNames}
    ds = group('input_trees', trees)
    return ds


def _normalize_internal_path(path):
    if type(path) is str:
        return path.replace('/', '.')
    if type(path) is bytes:
        return path.replace(b'/', b'.').decode('utf-8')
    return path


def pandas_wrap(func):
    @functools.wraps
    def df(*args, **kwargs):
        ds = args[0]
        for e in ds._elements:
            return e.pandas.df(*args[1:], **kwargs)
    func.df = df
    return df

# TODO: in next version?
# class SubSpace(type):

#     def __new__(cls, name, bases, attrs):
#         print('  SubSpace.__new__(cls=%s, name=%s, bases=%s, attrs=%s)' % (
#             cls, name, bases, attrs
#         ))
#         print()
#         return super().__new__(cls, name, bases, attrs)

#     def __call__(cls, *args, **kwargs):

#         print('  SubSpace.__call__(cls=%s, args=%s, kwargs=%s)' % (
#             cls, args, kwargs
#         ))
#         print()
#         return super().__call__(*args, **kwargs)


# class HyperSpace(SubSpace):

    # def __new__(cls, name, bases, attrs):
    #     print('  HyperSpace.__new__(cls=%s, name=%s, bases=%s, attrs=%s)' % (
    #         cls, name, bases, attrs
    #     ))
    #     print()
    #     attrs['__slots__'] = [a for a in attrs.keys() if not a.startswith('__')]
    #     attrs['__slots__'] += ['_index', '_elements']
    #     return super().__new__(cls, name, bases, attrs)

    # def __call__(cls, *args, **kwargs):
    #     print('  HyperSpace.__call__(cls=%s, args=%s, kwargs=%s)' % (
    #         cls, args, kwargs
    #     ))
    #     print()
    #     name = args[0]
    #     elements = args[1]
    #     if not elements:
    #         raise ValueError('elements cannot be empty')
    #     if not check_all_elements_of_same_type(elements):
    #         raise ValueError('Not all elements are of same type')

    #     tmp_class = super().__call__(*args, **kwargs)
    #     ds_methods = [m for m, _ in inspect.getmembers(tmp_class, predicate=inspect.ismethod)]
    #     e_methods = [m for m, _ in inspect.getmembers(elements[0], predicate=inspect.ismethod)]
    #     e_methods = [m for m in e_methods if m not in ds_methods and not m.startswith('__')]

    #     attrs = {m: f for m, f in inspect.getmembers(cls, predicate=inspect.ismethod)}

    #     new_attr = {m: print for m in e_methods}
    #     attrs.update(new_attr)
    #     # print('new:', attrs)

    #     newclass = cls.__new__(cls, cls.__name__, [object], attrs)
    #     print(dir(newclass), newclass.__slots__)
    #     # newclass = super().__call__(*args, **kwargs)
    #     return newclass

class DataSpaceView(object):

    intercept = ['array']

    def __init__(self, obj, mask=None):
        self._obj = obj
        self._mask = mask

    def __getattr__(self, name):
        if not hasattr(self._obj, name):
            raise AttributeError(
                'Object {} does not have attribute {}'.format(self._obj, name))
        if name not in DataSpaceView.intercept:
            return getattr(self._obj, name)
        return super().__getattr__(name)

    def __getitem__(self, key):
        return DataSpaceView(self._obj[key], self._mask)

    def array(self, *args, **kwargs):
        if self._mask is not None:
            return self._obj.array(*args, **kwargs)[self._mask]
        return self._obj.array(*args, **kwargs)

    def raw(self):
        return self._obj

    def __eq__(self, other):
        return self._obj == other


class DataSpace(object):

    def __init__(self, name, elements=None):
        if elements is not None and not check_all_elements_of_same_type(elements):
            raise ValueError('Not all elements are of same type')

        self._root = _normalize_internal_path(name)
        self._index = {self._root: self}
        self._elements = elements if elements is not None else {}
        self._mask = None

        self.__reload_index()

    def __load_element_functions(self):
        ds_methods = [m for m, _ in inspect.getmembers(
            self, predicate=inspect.ismethod)]
        e_methods = [m for m, in inspect.getmembers(
            self._elements[0], predicate=inspect.ismethod)]
        e_methods = [
            m for m in e_methods if m not in ds_methods and not m.startswith('__')]

        for m in e_methods:
            setattr(self, m, lambda e: getattr(e, m))

    def _add(self, name, value):
        name = name.decode('utf-8') if type(name) is bytes else name
        if name in self._elements:
            raise KeyError('Element {} already exists'.format(name))
        self._elements[name] = value
        self.__reload_index(name, value)

    def _update(self, newElements):
        newElements.update(self._elements)
        self._elements = newElements
        self.__reload_index()

    def __contains__(self, name):
        return _normalize_internal_path(name) in self._index

    def __getitem__(self, name):
        name = _normalize_internal_path(name)
        if name not in self._index:
            print(name, 'not in', list(self._index.keys()))
        return DataSpaceView(self._index[name], self._mask)

    def __setitem__(self, name, value):
        name = _normalize_internal_path(name)
        if name in self._index:
            raise ValueError('Variable {} already ecists!'.format(name))
        # TODO: tree_wraper wraps this in an uproot array
        self._index[name] = value

    def __len__(self):
        first_e = next(iter(self._elements.values()))
        if hasattr(first_e, '__len__'):
            if self._mask is not None:
                return np.count_nonzero(self._mask)
            return max([len(e) for e in self._elements.values()])
        return len(self._elements)

    def __add_to_index(self, name, value):
        name = _normalize_internal_path(name)
        full_path = '.'.join([self._root, name])
        if name not in self._index and full_path not in self._index:
            name = name.decode('utf-8') if type(name) is bytes else name
            self._index[name] = value
            self._index[full_path] = value

    def __reload_index(self, name=None, value=None):
        if name and value:
            self.__add_to_index(name, value)
            return

        for name, value in self._elements.items():
            if isinstance(value, self.__class__):
                for n, v in value._index.items():
                    v.__reload_index()
                    self.__add_to_index('.'.join([name, n]), v)
            elif hasattr(value, 'keys'):
                self.__recursive_index(value, [name])
            self.__add_to_index(name, value)

    def __recursive_index(self, collection, parents):
        self.__add_to_index('.'.join(parents), collection)
        for n in collection.keys():
            v = collection[n]
            n = n.decode('utf-8') if isinstance(n, bytes) else n

            if hasattr(v, 'keys'):
                self.__recursive_index(v, parents + [n])
            else:
                path = _normalize_internal_path('.'.join(parents + [n]))
                self.__add_to_index(path, v)
        # create aliases
        aliases = {}
        for key in self._index.keys():
            alias = self.alias(key)
            if alias != key:
                aliases[alias] = self._index[key]
        self._index.update(aliases)

    def notify(self, *args, **kwargs):
        actions = kwargs.pop('actions', [])
        results = {}
        for action in actions:
            results[action] = {}
            for name, element in self._elements.items():
                results[action][name] = getattr(
                    element, action)(*args, **kwargs)
        self.__reload_index()
        return results

    def keys(self):
        return [k.encode('utf-8') for k in self._index.keys()]

    def _find_tree_and_branch(self, path):
        # tree, branch = None, None
        tokens = path.split('.')
        for i, t in enumerate(tokens):
            tmp = t

            if i > 0:
                tmp = '.'.join(tokens[:i])
            if tmp in self:
                if 'Tree' in str(type(self[tmp])):
                    return self[tmp], '.'.join(tokens[i:])
        return self[path], path

    def df(self, *args, **kwargs):
        inputs = args[0]
        results = {}
        for i in inputs:
            alias = self.alias(i)
            results[alias] = self[alias].array(*args[1:], **kwargs)
        return pd.DataFrame.from_dict(results)

    def alias(self, key):
        if '.' in key:
            return key.replace('.', '__DOT__')
        return key

    def pandas(self):
        # TODO: could simplify with types.SimpleNamespace()
        pass

    pandas.df = df

    def new_variable(self, name, value):
        name = name('utf-8') if type(name) is bytes else name
        self[name] = value

    def apply_mask(self, new_mask):
        if self._mask is None:
            self._mask = _normalise_mask(new_mask, len(self))
        else:
            self._mask = self._mask[new_mask]

    def reset_mask(self):
        self._mask = None


def _normalise_mask(mask, tree_length):
    if isinstance(mask, (tuple, list)):
        mask = np.array(mask)
    elif not isinstance(mask, np.ndarray):
        raise RuntimeError("mask is not a numpy array, a list, or a tuple")
    return mask
