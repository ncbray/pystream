# Copyright 2011 Nicholas Bray
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from types import *

# Extended "types"
# Includes some important types not available elsewhere.

# A descriptor that produces builtin methods.
MethodDescriptorType = type(str.__dict__['count'])

# Wraps a slot in a type opbject.
WrapperDescriptorType = type(str.__dict__['__add__'])


TupleIteratorType 	= type(iter(()))
ListIteratorType 	= type(iter([]))
XRangeIteratorType 	= type(iter(xrange(1)))


TypeNeedsStub = (MethodDescriptorType, WrapperDescriptorType, BuiltinFunctionType)
TypeNeedsHiddenStub = (MethodDescriptorType, WrapperDescriptorType)


ConstantTypes = set((str, int, float, long, NoneType, bool, CodeType))
