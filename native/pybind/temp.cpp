#include "stdafx.h"

static PyObject *module = 0;

PyObject * beConfused(PyObject *self, PyObject *args)
{
	PyObject *obj0, *obj1, *obj2;
	
	if (!PyArg_ParseTuple(args, "O:beConfused", &obj0)) return NULL;
	obj1 = PyObject_GetAttrString(module, "confuse");
	obj2 = PyObject_CallFunctionObjArgs(obj1, obj0, NULL);
	Py_DECREF(obj1);
	return obj2;
}

PyObject * confusedSite(PyObject *self, PyObject *args)
{
	PyObject *obj1, *obj4, *obj2, *obj5, *obj0, *obj3, *obj6;
	
	if (!PyArg_ParseTuple(args, "O:confusedSite", &obj0)) return NULL;
	if(PyObject_IsTrue(obj0))
	{
		obj1 = PyObject_GetAttrString(module, "vec3");
		obj2 = PyFloat_FromDouble(7.0);
		obj3 = PyObject_CallFunctionObjArgs(obj1, obj2, obj2, obj2, NULL);
		Py_DECREF(obj1);
		Py_DECREF(obj2);
		return obj3;
	}
	else
	{
		obj4 = PyObject_GetAttrString(module, "vec3");
		obj5 = PyFloat_FromDouble(11.0);
		obj6 = PyObject_CallFunctionObjArgs(obj4, obj5, obj5, obj5, NULL);
		Py_DECREF(obj4);
		Py_DECREF(obj5);
		return obj6;
	}
}

PyObject * beConfusedConst(PyObject *self, PyObject *args)
{
	PyObject *obj0, *obj1, *obj2;
	
	if (!PyArg_ParseTuple(args, "O:beConfusedConst", &obj0)) return NULL;
	obj1 = PyObject_GetAttrString(module, "confuseConst");
	obj2 = PyObject_CallFunctionObjArgs(obj1, obj0, NULL);
	Py_DECREF(obj1);
	return obj2;
}

PyObject * confuseConst(PyObject *self, PyObject *args)
{
	PyObject *obj0, *obj1;
	
	if (!PyArg_ParseTuple(args, "O:confuseConst", &obj0)) return NULL;
	if(PyObject_IsTrue(obj0))
	{
		Py_INCREF(obj0);
		return obj0;
	}
	else
	{
		obj1 = PyInt_FromLong(1);
		return obj1;
	}
}

PyObject * dot(PyObject *self, PyObject *args)
{
	PyObject *obj1, *obj6, *obj5, *obj7, *obj4, *obj10, *obj2, *obj0, *obj3, *obj12, *obj9, *obj8, *obj11;
	
	if (!PyArg_ParseTuple(args, "OO:dot", &obj0, &obj1)) return NULL;
	obj2 = PyObject_GetAttrString(obj0, "x");
	obj3 = PyObject_GetAttrString(obj1, "x");
	obj4 = PyNumber_Multiply(obj2, obj3);
	obj5 = PyObject_GetAttrString(obj0, "y");
	obj6 = PyObject_GetAttrString(obj1, "y");
	obj7 = PyNumber_Multiply(obj5, obj6);
	obj8 = PyObject_GetAttrString(obj0, "z");
	obj9 = PyObject_GetAttrString(obj1, "z");
	obj10 = PyNumber_Multiply(obj8, obj9);
	obj11 = PyNumber_Add(obj4, obj7);
	obj12 = PyNumber_Add(obj11, obj10);
	Py_DECREF(obj3);
	Py_DECREF(obj7);
	Py_DECREF(obj5);
	Py_DECREF(obj6);
	Py_DECREF(obj4);
	Py_DECREF(obj10);
	Py_DECREF(obj2);
	Py_DECREF(obj11);
	Py_DECREF(obj9);
	Py_DECREF(obj8);
	return obj12;
}

PyObject * extractValue(PyObject *self, PyObject *args)
{
	PyObject *obj0, *obj1, *obj2;
	
	if (!PyArg_ParseTuple(args, "O:extractValue", &obj0)) return NULL;
	obj1 = PyObject_GetAttrString(obj0, "dot");
	obj2 = PyObject_CallFunctionObjArgs(obj1, obj0, NULL);
	Py_DECREF(obj1);
	return obj2;
}

PyObject * confuseMethods(PyObject *self, PyObject *args)
{
	PyObject *obj8, *obj1, *obj9, *obj10, *obj13, *obj11, *obj12, *obj3, *obj0, *obj5, *obj14, *obj15, *obj4, *obj2, *obj6, *obj7, *obj16, *obj17;
	
	if (!PyArg_ParseTuple(args, "OOOOOO:confuseMethods", &obj0, &obj1, &obj2, &obj3, &obj4, &obj5)) return NULL;
	obj6 = PyObject_GetAttrString(module, "vec3");
	obj7 = PyObject_CallFunctionObjArgs(obj6, obj0, obj1, obj2, NULL);
	obj8 = PyObject_GetAttrString(module, "vec3");
	obj9 = PyObject_CallFunctionObjArgs(obj8, obj3, obj4, obj5, NULL);
	obj10 = PyObject_RichCompare(obj0, obj1, Py_GT);
	if(PyObject_IsTrue(obj10))
	{
		obj11 = PyObject_GetAttrString(obj7, "cross");
		obj12 = PyObject_CallFunctionObjArgs(obj11, obj9, NULL);
		obj13 = obj12;
		Py_DECREF(obj11);
	}
	else
	{
		obj14 = PyObject_GetAttrString(obj9, "cross");
		obj15 = PyObject_CallFunctionObjArgs(obj14, obj7, NULL);
		obj13 = obj15;
		Py_DECREF(obj14);
	}
	obj16 = PyObject_GetAttrString(obj13, "dot");
	obj17 = PyObject_CallFunctionObjArgs(obj16, obj13, NULL);
	Py_DECREF(obj8);
	Py_DECREF(obj7);
	Py_DECREF(obj9);
	Py_DECREF(obj10);
	Py_DECREF(obj13);
	Py_DECREF(obj6);
	Py_DECREF(obj16);
	return obj17;
}

PyObject * passThrough(PyObject *self, PyObject *args)
{
	PyObject *obj0;
	
	if (!PyArg_ParseTuple(args, "O:passThrough", &obj0)) return NULL;
	Py_INCREF(obj0);
	return obj0;
}

PyObject * beConfusedSite(PyObject *self, PyObject *args)
{
	PyObject *obj7, *obj1, *obj8, *obj0, *obj2, *obj3, *obj4, *obj5, *obj6;
	
	if (!PyArg_ParseTuple(args, "O:beConfusedSite", &obj0)) return NULL;
	obj1 = PyObject_GetAttrString(module, "passThrough");
	obj2 = PyObject_GetAttrString(module, "confusedSite");
	obj3 = PyObject_CallFunctionObjArgs(obj2, obj0, NULL);
	obj4 = PyObject_CallFunctionObjArgs(obj1, obj3, NULL);
	obj5 = PyObject_GetAttrString(module, "passThrough");
	obj6 = PyObject_GetAttrString(module, "extractValue");
	obj7 = PyObject_CallFunctionObjArgs(obj6, obj4, NULL);
	obj8 = PyObject_CallFunctionObjArgs(obj5, obj7, NULL);
	Py_DECREF(obj7);
	Py_DECREF(obj2);
	Py_DECREF(obj1);
	Py_DECREF(obj3);
	Py_DECREF(obj4);
	Py_DECREF(obj5);
	Py_DECREF(obj6);
	return obj8;
}

PyObject * cross(PyObject *self, PyObject *args)
{
	PyObject *obj21, *obj5, *obj7, *obj8, *obj6, *obj14, *obj18, *obj19, *obj1, *obj20, *obj22, *obj23, *obj24, *obj3, *obj2, *obj16, *obj9, *obj10, *obj11, *obj12, *obj17, *obj15, *obj0, *obj13, *obj4;
	
	if (!PyArg_ParseTuple(args, "OO:cross", &obj0, &obj1)) return NULL;
	obj2 = PyObject_GetAttrString(obj0, "y");
	obj3 = PyObject_GetAttrString(obj1, "z");
	obj4 = PyNumber_Multiply(obj2, obj3);
	obj5 = PyObject_GetAttrString(obj0, "z");
	obj6 = PyObject_GetAttrString(obj1, "y");
	obj7 = PyNumber_Multiply(obj5, obj6);
	obj8 = PyNumber_Subtract(obj4, obj7);
	obj9 = PyObject_GetAttrString(obj0, "z");
	obj10 = PyObject_GetAttrString(obj1, "x");
	obj11 = PyNumber_Multiply(obj9, obj10);
	obj12 = PyObject_GetAttrString(obj0, "x");
	obj13 = PyObject_GetAttrString(obj1, "z");
	obj14 = PyNumber_Multiply(obj12, obj13);
	obj15 = PyNumber_Subtract(obj11, obj14);
	obj16 = PyObject_GetAttrString(obj0, "x");
	obj17 = PyObject_GetAttrString(obj1, "y");
	obj18 = PyNumber_Multiply(obj16, obj17);
	obj19 = PyObject_GetAttrString(obj0, "y");
	obj20 = PyObject_GetAttrString(obj1, "x");
	obj21 = PyNumber_Multiply(obj19, obj20);
	obj22 = PyNumber_Subtract(obj18, obj21);
	obj23 = PyObject_GetAttrString(module, "vec3");
	obj24 = PyObject_CallFunctionObjArgs(obj23, obj8, obj15, obj22, NULL);
	Py_DECREF(obj21);
	Py_DECREF(obj5);
	Py_DECREF(obj7);
	Py_DECREF(obj8);
	Py_DECREF(obj6);
	Py_DECREF(obj14);
	Py_DECREF(obj16);
	Py_DECREF(obj17);
	Py_DECREF(obj18);
	Py_DECREF(obj19);
	Py_DECREF(obj3);
	Py_DECREF(obj20);
	Py_DECREF(obj23);
	Py_DECREF(obj2);
	Py_DECREF(obj22);
	Py_DECREF(obj9);
	Py_DECREF(obj10);
	Py_DECREF(obj11);
	Py_DECREF(obj12);
	Py_DECREF(obj13);
	Py_DECREF(obj15);
	Py_DECREF(obj4);
	return obj24;
}

PyObject * confuse(PyObject *self, PyObject *args)
{
	PyObject *obj0, *obj1, *obj2;
	
	if (!PyArg_ParseTuple(args, "O:confuse", &obj0)) return NULL;
	if(PyObject_IsTrue(obj0))
	{
		obj1 = PyInt_FromLong(1);
		return obj1;
	}
	else
	{
		obj2 = PyInt_FromLong(0);
		return obj2;
	}
}

PyObject * __init__(PyObject *self, PyObject *args)
{
	PyObject *obj0, *obj1, *obj4, *obj2, *obj3;
	
	if (!PyArg_ParseTuple(args, "OOOO:__init__", &obj0, &obj1, &obj2, &obj3)) return NULL;
	PyObject_SetAttrString(obj0, "x", obj1);
	PyObject_SetAttrString(obj0, "y", obj2);
	PyObject_SetAttrString(obj0, "z", obj3);
	obj4 = Py_None;
	Py_INCREF(obj4);
	return obj4;
}

static PyMethodDef BindMethods[] = {
	{"beConfused", beConfused, METH_VARARGS, ""},
	{"confusedSite", confusedSite, METH_VARARGS, ""},
	{"beConfusedConst", beConfusedConst, METH_VARARGS, ""},
	{"confuseConst", confuseConst, METH_VARARGS, ""},
	{"dot", dot, METH_VARARGS, ""},
	{"extractValue", extractValue, METH_VARARGS, ""},
	{"confuseMethods", confuseMethods, METH_VARARGS, ""},
	{"passThrough", passThrough, METH_VARARGS, ""},
	{"beConfusedSite", beConfusedSite, METH_VARARGS, ""},
	{"cross", cross, METH_VARARGS, ""},
	{"confuse", confuse, METH_VARARGS, ""},
	{"__init__", __init__, METH_VARARGS, ""},
	{NULL, NULL, 0, NULL}
};


PyMODINIT_FUNC initpybind()
{
	module = Py_InitModule3("pybind", BindMethods, "");
}
