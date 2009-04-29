module('tests.full.physics')
output('../temp')
config(checkTypes=True)


import tests.full.physics as physics
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

attr(inst(vec.mat4), 'm00', inst(float))
attr(inst(vec.mat4), 'm01', inst(float))
attr(inst(vec.mat4), 'm02', inst(float))
attr(inst(vec.mat4), 'm03', inst(float))
attr(inst(vec.mat4), 'm10', inst(float))
attr(inst(vec.mat4), 'm11', inst(float))
attr(inst(vec.mat4), 'm12', inst(float))
attr(inst(vec.mat4), 'm13', inst(float))
attr(inst(vec.mat4), 'm20', inst(float))
attr(inst(vec.mat4), 'm21', inst(float))
attr(inst(vec.mat4), 'm22', inst(float))
attr(inst(vec.mat4), 'm23', inst(float))
attr(inst(vec.mat4), 'm30', inst(float))
attr(inst(vec.mat4), 'm31', inst(float))
attr(inst(vec.mat4), 'm32', inst(float))
attr(inst(vec.mat4), 'm33', inst(float))

#entryPoint(physics.simpleUpdate, inst(float), inst(int))
entryPoint(physics.harness, inst(vec.vec4), inst(vec.vec3))
