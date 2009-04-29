module('tests.full.recursive')
output('../temp')
config(checkTypes=True)

import tests.full.recursive as recursive

entryPoint(recursive.fact, inst(int))
