"""
Specification
--------------
The DataSpace is a composable container for any objects.

- elements (sub-spaces) can be accessed via composable indices: `ds['path1/path2']['obj1.var'], ds['path1/path2.obj1.var'], ds['path1.path2.obj1.var']` are equivalent
- function calls on a DataSpace or sub-space are redirected to the underlying objects and return a generator
- objects under the same DataSpace need to be of the same type, i.e. have the same API
- an object is contained  in a DataSpace if the object identifier can be found in the DataSpace index or the indices of sub-spaces
"""
import inspect


def check_all_elements_of_same_type(elements):
    if not elements:
        return False
    if not isinstance(elements, dict):
        raise ValueError('elements need to be of type "dict"')
    t = type(next(iter(elements.values())))
    return all(isinstance(e, t) for e in elements.values())


def group(group_name, elements):
    """
        Create group from the given elements and give it a name
    """
    if not isinstance(elements, dict):
        raise ValueError('elements need to be of type "dict"')

    newGroup = DataSpace(name=group_name)
    groups = {}
    for name, item in elements.items():
        if isinstance(item, dict):
            tmpGroup = group(name, item)
            groups[name] = tmpGroup
        else:
            newGroup._add(name, item)
    newGroup._update(groups)
    return newGroup


def _normalize_internal_path(path):
    return path.replace('/', '.')

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


class DataSpace(object):

    # __slots__ = ['_index', '_elements', '_methods']

    def __init__(self, name, elements=None):
        if elements is not None and not check_all_elements_of_same_type(elements):
            raise ValueError('Not all elements are of same type')

        self._root = _normalize_internal_path(name)
        self._index = {self._root: self}
        self._elements = elements if elements is not None else {}

        self.__reload_index()

    def __load_element_functions(self):
        ds_methods = [m for m, _ in inspect.getmembers(self, predicate=inspect.ismethod)]
        e_methods = [m for m, in inspect.getmembers(elements[0], predicate=inspect.ismethod)]
        e_methods = [m for m in e_methods if m not in ds_methods and not m.startswith('__')]

        for m in e_methods:
            setattr(self, m, lambda e: getattr(e, m))

    def _add(self, name, value):
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
        return self._index[name]

    def __len__(self):
        first_e = next(iter(self._elements.values()))
        if hasattr(first_e, '__len__'):
            return max([len(e) for e in self._elements])
        return len(self._elements)

    def __add_to_index(self, name, value):
        name = _normalize_internal_path(name)
        full_path = '.'.join([self._root, name])
        if name not in self._index and full_path not in self._index:
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

    def notify(self, *args, **kwargs):
        actions = kwargs.pop('actions', [])
        results = {}
        for action in actions:
            results[action] = {}
            for name, element in self._elements.items():
                print(action, name, element, args, kwargs)
                results[action][name] = getattr(element, action)(*args, **kwargs)
        self.__reload_index()
        return results
