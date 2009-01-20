// pybind.cpp : Defines the entry point for the DLL application.
//

#include "stdafx.h"
#include "pybind.h"

#include "vec3.h"

/*
PyObject * dot(PyObject * self, PyObject * args)
{
	PyObject * __restrict obj1;
	PyObject * __restrict obj11;
	PyObject * __restrict obj8, * __restrict obj2, * __restrict obj3, * __restrict obj9, * __restrict obj10;
	PyObject * __restrict obj0, * __restrict obj5, * __restrict obj12, * __restrict obj6, * __restrict obj7, * __restrict obj4;

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
	Py_INCREF(obj12);

	Py_DECREF(obj11);
	Py_DECREF(obj8);
	Py_DECREF(obj2);
	Py_DECREF(obj3);
	Py_DECREF(obj9);
	Py_DECREF(obj10);
	Py_DECREF(obj5);
	Py_DECREF(obj12);
	Py_DECREF(obj6);
	Py_DECREF(obj7);
	Py_DECREF(obj4);
	return obj12;
}
*/

/*
PyObject * dot(PyObject * self, PyObject * args)
{
	PyObject * __restrict obj0;
	PyObject * __restrict obj1;
	PyObject * __restrict obj2;
	PyObject * __restrict obj3;
	PyObject * __restrict obj4;
	PyObject * __restrict obj5;
	PyObject * __restrict obj6;
	PyObject * __restrict obj7;


	if (!PyArg_ParseTuple(args, "OO:dot", &obj0, &obj1)) return NULL;
	obj2 = PyObject_GetAttrString(obj0, "x");
	obj3 = PyObject_GetAttrString(obj1, "x");
	obj4 = PyObject_GetAttrString(obj0, "y");
	obj5 = PyObject_GetAttrString(obj1, "y");
	obj6 = PyObject_GetAttrString(obj0, "z");
	obj7 = PyObject_GetAttrString(obj1, "z");

	const double a = PyFloat_AsDouble(obj2);
	const double b = PyFloat_AsDouble(obj3);
	const double c = PyFloat_AsDouble(obj4);
	const double d = PyFloat_AsDouble(obj5);
	const double e = PyFloat_AsDouble(obj6);
	const double f = PyFloat_AsDouble(obj7);

	Py_DECREF(obj2);
	Py_DECREF(obj3);
	Py_DECREF(obj4);
	Py_DECREF(obj5);
	Py_DECREF(obj6);
	Py_DECREF(obj7);

	return PyFloat_FromDouble(a*b+c*d+e*f);
}
*/

PyObject * dot(PyObject * self, PyObject * args)
{
	PyObject * __restrict obj0;
	PyObject * __restrict obj1;

	if (!PyArg_ParseTuple(args, "OO:dot", &obj0, &obj1)) return NULL;

	vec3 * __restrict a = ((vec3_wrapper *)obj0)->obj;
	vec3 * __restrict b = ((vec3_wrapper *)obj1)->obj;

	return PyFloat_FromDouble(a->dot(*b));
}


static PyObject * spam_system(PyObject *self, PyObject *args)
{
	const char *command;
	int sts;

	if (!PyArg_ParseTuple(args, "s", &command))
		return NULL;
	sts = system(command);
	return Py_BuildValue("i", sts);
}

static PyMethodDef BindMethods[] = {
	{"dot",  dot, METH_VARARGS, "Dot product."},
	{"system",  spam_system, METH_VARARGS, "Execute a shell command."},
	{NULL, NULL, 0, NULL}        /* Sentinel */
};



extern void vec3_attach(PyObject * m);

PyMODINIT_FUNC initpybind()
{
	PyObject * m = Py_InitModule3("pybind", BindMethods, "Binding test module.");
	vec3_attach(m);
}

