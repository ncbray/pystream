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

from language.python import ast

def buildTempLocal(analysis, objs):
	if objs is None:
		return None
	else:
		lcl = analysis.root.local(ast.Local('entry_point_arg'))
		objs = frozenset([analysis.objectName(xtype) for xtype in objs])
		lcl.updateValues(objs)
		return lcl

def buildEntryPoint(analysis, ep, epargs):
	selfarg = buildTempLocal(analysis, epargs.selfarg)

	args = []
	for arg in epargs.args:
		args.append(buildTempLocal(analysis, arg))

	varg = buildTempLocal(analysis, epargs.vargs)
	karg = buildTempLocal(analysis, epargs.kargs)

	analysis.root.dcall(ep, ep.code, selfarg, args, [], varg, karg, None)
