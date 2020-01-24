DataSpace
=========


Specification
--------------
The DataSpace is a composable container for any objects.

- elements (sub-spaces) can be accessed via composable indices: `ds['path1/path2']['obj1.var'], ds['path1/path2.obj1.var'], ds['path1.path2.obj1.var']` are equivalent
- function calls on a DataSpace or sub-space are redirected to the underlying objects and return a generator
- objects under the same DataSpace need to be of the same type, i.e. have the same API
- an object is contained  in a DataSpace if the object identifier can be found in the DataSpace index or the indices of sub-spaces

Usage
-----

