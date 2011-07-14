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

module('linear')
output('../temp')
config(checkTypes=True)

entryPoint('doDot')
entryPoint('doDotHalf', inst('float'), inst('float'), inst('float'))
entryPoint('doDotFull', inst('float'), inst('float'), inst('float'), inst('float'), inst('float'), inst('float'))

entryPoint('doOr', inst('bool'), const(7), const(11))
entryPoint('testAttrMerge', inst('bool'))


entryPoint('doStaticSwitch')
entryPoint('doDynamicSwitch', const(1))
entryPoint('doDynamicSwitch', const(0))
entryPoint('doDynamicSwitch', inst('int'))

entryPoint('doSwitchReturn', const(1))
entryPoint('doSwitchReturn', const(0))
entryPoint('doSwitchReturn', inst('int'))


entryPoint('twisted', inst('int'))
entryPoint('testBinTree')
entryPoint('vecAttrSwitch', inst('bool'))

entryPoint('doMultiSwitch', inst('bool'), inst('bool'))

entryPoint('testCall', inst('bool'))

entryPoint('selfCorrelation', inst('bool'))
entryPoint('groupCorrelation', inst('bool'))

entryPoint('methodMerge', inst('bool'))

entryPoint('assignMerge', inst('bool'))
