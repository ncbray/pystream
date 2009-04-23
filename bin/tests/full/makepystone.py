module('tests.full.pystone')
output('../temp')
config(checkTypes=True)

entryPoint('pystones', inst(int))
