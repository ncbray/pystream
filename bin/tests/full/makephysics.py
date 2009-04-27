module('tests.full.physics')
output('../temp')
config(checkTypes=True)

import tests.full.vec as vec

attr(inst(vec.vec2), 'x', inst(float))
attr(inst(vec.vec2), 'y', inst(float))

attr(inst(vec.vec3), 'x', inst(float))
attr(inst(vec.vec3), 'y', inst(float))
attr(inst(vec.vec3), 'z', inst(float))

attr(inst(vec.vec4), 'x', inst(float))
attr(inst(vec.vec4), 'y', inst(float))
attr(inst(vec.vec4), 'z', inst(float))
attr(inst(vec.vec4), 'w', inst(float))

#entryPoint('simpleUpdate', inst(float), inst(int))
entryPoint('harness', inst(vec.vec4), inst(vec.vec3))
