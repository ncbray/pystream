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

from . import fold
from . import dce
from dataflow.base import InternalError

from cStringIO import StringIO
from language.python.simplecodegen import SimpleCodeGen

from language.python import ast

#
# Leverages type inference to eliminate indirect calls,
# fold and propigate constants, etc.
# In effect, this pass attempts to "de-dynamicize" Python
#


def evaluateCode(compiler, prgm, node, outputAnchors=None):
	assert node.isCode(), type(node)

	try:
		fold.evaluateCode(compiler, prgm, node)

		# Can't process arbitrary abstract code nodes.
		if node.isStandardCode():
			dce.evaluateCode(compiler, node, outputAnchors)

	except InternalError:
		print
		print "#######################################"
		print "Function generated an internal error..."
		print "#######################################"
		sio = StringIO()
		scg = SimpleCodeGen(sio)
		scg.process(node)
		print sio.getvalue()
		raise


def evaluate(compiler, prgm):
	with compiler.console.scope('simplify'):
		for code in prgm.liveCode:
			if not code.annotation.descriptive:
				evaluateCode(compiler, prgm, code)
