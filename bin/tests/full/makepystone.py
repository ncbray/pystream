#@PydevCodeAnalysisIgnore

module('tests.full.pystone')
output('../temp')
config(checkTypes=True)

import tests.full.pystone as pystone

entryPoint(pystone.pystones, inst(int))
