// _pystream.cpp : Defines the entry point for the DLL application.
//

#include "stdafx.h"

// HACK as this is private...
typedef struct {
	PyObject_HEAD
		PyWrapperDescrObject *descr;
	PyObject *self;
} wrapperobject;


PyObject *
PyCFunction_cfuncptr(PyObject *self, PyObject *args)
{
	PyObject *func;
	void *ptr = 0;

	if (!PyArg_ParseTuple(args, "O:cfuncptr", &func)) return NULL;

	if (PyCFunction_Check(func)) 
	{
		ptr = PyCFunction_GetFunction(func);
	}
	else if (PyObject_TypeCheck(func, &PyWrapperDescr_Type))
	{
		ptr = ((PyWrapperDescrObject *)func)->d_wrapped;
	}
	// 2.5+?
	else if (strcmp(func->ob_type->tp_name, "method_descriptor") == 0) // Horrible hack, but there seems to be no alternative.
	{
		ptr = ((PyMethodDescrObject *)func)->d_method->ml_meth;
	}
	// 2.6
	else if (strcmp(func->ob_type->tp_name, "method-wrapper") == 0) // Horrible hack, but there seems to be no alternative.
	{
		ptr = ((wrapperobject *)func)->descr->d_base->wrapper;
	}
	else
	{
		PyErr_SetString(PyExc_TypeError, "Argument must wrap a c function pointer.");
		return NULL;
	}

	return PyInt_FromSsize_t(Py_ssize_t(ptr)); 
}

static PyMethodDef BindMethods[] = {
	{"cfuncptr", PyCFunction_cfuncptr, METH_VARARGS, ""},
	{NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC init_pystream()
{
	Py_InitModule3("_pystream", BindMethods, "");
}


