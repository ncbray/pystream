from simple import *
from decl import *


# Shader decl
s = shader(SimpleShader)
s.vertex(vec3, vec3)

s.method('__init__', mat4)
s.slot('project', mat4)


