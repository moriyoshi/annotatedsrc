Rendering the posted source code with callouts
----------------------------------------------

::

    POST http://localhost:8000/g/code.c.svg

Request body::

    #include <stdio.h>

    int main() --- (1)
    {
        return 0;
    }


Rendering the source code in the specified Git repository with callouts
-----------------------------------------------------------------------

::

    GET http://localhost:8000/f/https://github.com/moriyoshi/embedsrc/master/+/setup.py?range=1-5&[A]=1&[B]=2


