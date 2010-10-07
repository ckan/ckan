class Enum(set):
    '''Simple enumeration
    e.g. Animal = Enum("dog", "cat", "horse")
    joey = Animal.DOG
    '''
    def __init__(self, *names):
        super(Enum, self).__init__(names)
        
    def __getattr__(self, name):
        if name in self:
            return name
        raise AttributeError
