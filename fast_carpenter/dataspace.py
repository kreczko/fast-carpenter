

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
    WRAPPED_FUNCS = ['array']

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
        # should group be groups where we pop one item of for each level?
        if group and group != self._name:
            self.find_group(group).notify(*args, **kwargs)
        

        results = {}
        # group, item = self.find_group_and_item(item)
        # if group is not None:
            
        for element in elements:
            if isinstance(element, DataSpace):
                results[element._name] = element.notify(*args, **kwargs)
            else:
                action = []
                if 'action' in kwargs:
                    action = kwargs.pop('action')
                    if not isinstance(action, list):
                        action = [action]
                    for a in action:
                        if a in self.WRAPPED_FUNCS:
                            results[a] = getattr(self, a)(*args, **kwargs)
                            continue
                        if hasattr(element, a):
                            # should we catch errors here?
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
        
    def find_group_and_item(self, group_or_item):
        tokens = group_or_item.split('.')
        if not tokens:
            return None, group_or_item
        
        for i in range(len(tokens)):
            group = '/'.join(tokens[:i])
            item = '.'.join(tokens[i:])
            if group == self._name:
                return self, item
            for element in self._elements:
                if not isinstance(element, DataSpace):
                    continue
                if group == element._name:
                    return element, item
                
        return self, group_or_item
                    

    def array(self, item):
        group, item = self.find_group_and_item(item)
        if group is None:
            # call notify on elements
            return self.notify(group=None, item=item, action='array')
    
        try:
            result = group._elements[0].array(item)
            return result
        except Exception as e:
            print('failed', self._elements, e)
        
        return None

    @property
    def et(self):
        return [42]
    
    def __repr__(self):
        element_names = [e._name for e in self._elements if hasattr(e, '_name')]
        n_elements = len(self._elements)
        n_unnamed = n_elements - len(element_names)
        if n_unnamed > 0:
            return 'DataSpace "{name}" with {N} elements: {element_names} ({M} unnamed)'.format(
                name=self._name,
                N=n_elements,
                element_names=element_names,
                M=n_unnamed,
            )
        return 'DataSpace "{name}" with {N} elements: {element_names}'.format(
                name=self._name,
                N=n_elements,
                element_names=element_names,
            )


class DataSpaceGroup(object):
    pass
