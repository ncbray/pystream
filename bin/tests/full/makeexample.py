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

#@PydevCodeAnalysisIgnore

module('example')
output('../temp')
config(checkTypes=True)

entryPoint('f')
entryPoint('add', const(1.0), const(2.0))
entryPoint('add', inst('int'), inst('int'))
entryPoint('call', inst('float'), inst('float'), inst('float'), inst('float'))
entryPoint('either', inst('int'), inst('int'))
entryPoint('inrange', inst('float'))

entryPoint('negate', inst('int'))
entryPoint('negateConst')

entryPoint('defaultArgs')
entryPoint('defaultArgs', inst('int'))
entryPoint('defaultArgs', inst('int'), inst('int'))

entryPoint('switch1', inst('float'))
entryPoint('switch2', inst('float'))

#entryPoint('factorial', inst('int'))
# TODO, prevent infinite recursion.
#entryPoint('factorial', const(10))
