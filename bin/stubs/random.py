from __future__ import absolute_import

from . stubcollector import llast, attachAttrPtr, highLevelStub
from . llutil import simpleDescriptor, allocate, getType

### Random module ###


import _random
attachAttrPtr(_random.Random, 'random')(llast(simpleDescriptor('random', ('self',), float)))
