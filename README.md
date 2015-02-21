Primarily a wrapper for handling and processing `sys.stdin` but unlike pythonpy multiline processing is possible like in `python -c`, also shell calls from python are abbreviated via bash syntax and piped to subprocess, which should skip the overhead of starting a new pycmd process if there are several pipes. 
Syntactical example: 
```
py -XU -silent "`ls -l | grep .png`; [i for i in r.w if int(i[4]) > 5000]"
```
