PyStream 0.1
Copyright (c) 2007-2011 Nick Bray
See LICENSE.txt for licensing information.


2011/07/13

This is the initial release of PyStream, a static compiler that can map Python onto the GPU.  I have put off releasing the code for almost a year now, having always intended to "clean it up" first.  To get the ball rolling, I am releasing it as-is, in all its scramble-to-finish-my-dissertation glory.

Direct questions and comments to: ncbray@gmail.com.



To get PyStream running, you must do the following:


=== Dependencies ===

* Install Python 2.6.  (Newer versions may also work, but they have not been tested.)

* Install Graphviz, and make sure it works.
(I've encountered a case where a .rpm install did not work correctly out of the box.)


=== Native Code ===

* If you're not using windows, run ./native/_pystream/setup.py and then copy the resulting _pystream.pyd into ./bin directory.  This library is needed to scrape data held in built-in data structures that is not accessible from Python.


=== Running ===

Run python bin\runtests.py.  Output will show up in the "summaries" directory.

The entry points for the shaders are specified in bin\tests\full\makephysics.py.


=== Acknowledgments ===

Python
Copyright (c) 2001-2008 Python Software Foundation
All Rights Reserved.

ANTLR
Copyright (c) 2003-2008 Terence Parr
All Rights Reserved.

PADS
Public Domain