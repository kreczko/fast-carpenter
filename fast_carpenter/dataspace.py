

def group(elements, name=None):
    """
        Create group from the given elements and give it a name
    """
    newGroup = DataSpace(name=name)
    if isinstance(elements, dict):
        groups = []
        for name, item in elements.items():
            tmpGroup = group(item, name=name)
            groups.append(tmpGroup)
        newGroup.extend(groups)
        return newGroup

    if isinstance(elements, (list, tuple)):
        newGroup.extend(elements)
    else:
        newGroup.extend([elements])

    return newGroup


class DataSpace(object):
    """
        Dataspace to collect objects from memory, group them and notfify them of changes
    """

    def __init__(self, name=None):
        self._elements = []
        self._namedElements = {}
        self._name = name if name is not None else 'final space season 1'

    def add(self, element, *args, **kwargs):
        pass

    def extend(self, elements):
        self._elements.extend(elements)

    def update(self, namedElements):
        self._namedElements.update(namedElements)

    def notify(self, group=None, *args, **kwargs):
        elements = self._elements
        if group is not None and group != self._name:
            self.find_group(group).notify(*args, **kwargs)

        for element in elements:
            if hasattr(element, 'notify'):
                element.notify(*args, **kwargs)
            else:
                action = []
                results = {}
                if 'action' in kwargs:
                    action = kwargs.pop('action')
                    if not isinstance(action, list):
                        action = [action]
                    for a in action:
                        if hasattr(element, a):
                            results[a] = getattr(element, a)(*args, **kwargs)
        return results

    def __len__(self):
        for element in self._elements:
            if hasattr(element, '__len__'):
                return len(element)

    def find_group(self, group):
        for element in self._elements:
            if hasattr(element, 'name'):
                if element.name == group:
                    return element

        raise KeyError('Cannot find group {group} in data space {name}'.format(
            group=group, name=self._name))

    def array(self, item):
        tokens = item.split('.')
        if not tokens:
            return self.notify(None, item, action='array')

        result = None
        for i in range(len(tokens)):
            try:
                folder = '/'.join(tokens[:i])
                name = '.'.join(tokens[i:])
                print('Trying to find {}:'.format(folder + item))
                result = self.notify(group=folder + name, action='array')
            except KeyError as e:
                print('Cannot find {}:'.format(folder + item), e)
        print('result', result)
        return result

    @property
    def et(self):
        return 42


class DataSpaceGroup(object):
    pass
