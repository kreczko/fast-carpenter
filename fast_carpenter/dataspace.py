

def group(elements, name=None):
    """
        Create group from the given elements and give it a name
    """
    newGroup = DataSpace(name=name)
    newGroup.extend(elements)
    return newGroup
    

class DataSpace(object):
    """
        Dataspace to collect objects from memory, group them and notfify them of changes
    """
    
    def __init__(self, name=None):
        self._elements = []
        self._name = []
    
    def add(self, element, *args, **kwargs):
        pass
    
    def extend(self, elements):
        self._elements.extend(elements)
    
    def notify(self, target=None, *args, **kwargs):
        if target is not None:
            self.find_target(target).notify(*args, **kwargs)
            return 0
        
        
        for element in self._elements:
            if hasattr(element, 'notify'):
                element.notify(*args, **kwargs)
            else:
                action = []
                if 'action' in kwargs:
                    action = kwargs.pop('action')
                    if not isinstance(action, list):
                        action = [action]
                    for a in action:
                        if hasattr(element, a):
                            getattr(element, a)()
    
    def __len__(self):
        for element in self._elements:
            if hasattr(element, '__len__'):
                return len(element)
    
    def find_target(self, *args, **kwargs):
        pass
    
    @property
    def et(self):
        return 42
        

    

class DataSpaceGroup(object):
    pass