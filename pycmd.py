#!/usr/bin/env python3
#strictly p3 for now
"""puss (From puss in boots) my take on pythonpy"""
import argparse
import sys
import json
import re
import select 
import os
import io
from collections import Iterable
from ast import literal_eval
import subprocess as sp

__version_info__ = '''pythonpuss %s 
python %s''' % ("0.0.1", sys.version.split(' ')[0])

""" 
Access last result as r 
r.l, r.x, r.w (r.list(), r.str(), r.words())
corresponding iterators as : il, iw, ir
Access stored results as x<num> 
i.e. x1.l 
Expand variable into bash with % 
i.e. "x='hello world'; `echo %x`" 
Pipe python variable into bash stdin
i.e. 
"""
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('expression', nargs='?', default='None')
#default true for now
parser.add_argument("-U", dest="unsafe_shell_call",action='store_const', const=False, default=True, help="use shell=True for subprocess calls")
parser.add_argument('-debug', dest='debug',const=True, action="store_const", default=False, help='debug logging')
parser.add_argument('-V', '--version', action='version', version=__version_info__, help='version info')
parser.add_argument('--i', '--ignore_exceptions', dest='ignore_exceptions', action='store_const', const=True, default=False, help='Wrap try-except-pass around each row')
parser.add_argument('-silent', dest='silent', action='store_const', const=True, default=False, help="Don't print expression output")
parser.add_argument('-S', '--store_all', dest="store_all", action="store_const", const=True, default=False, help="Store output of all expressions")
parser.add_argument('-F', '--store_format', dest='store_format_string', nargs='?', default="x{}", help="Default variable names for expression output storage")
#reversed for now
parser.add_argument('-X', '--use-exec', dest='use_exec', action="store_const", const=False, default=True, help="allows the use of exec type expressions")
parser.add_argument('-b', '--binary-subprocess-open', dest='universal_newlines', action="store_const", const=False, default=True, help="Subprocess will open files as binary rather than text")

class ioWrap(object):
    def __init__(self, io, *args, **kwargs): 
        self.io = io
        self._lines = None
        self._words = None
        self._buff = None
    #Because stdin blocks on read if it's empty 
    def not_empty(self): 
        return True if select.select([self.io], [], [], .000001)[0] else False
    def decode(self, line):
        if 'b' in self.io.mode: 
            try: 
                return line.decode('utf-8')
            except: pass
        return line
    def iwords(self): 
        if self.not_empty:
            return (re.sub('\s+', ' ', line).split(' ') for line in self.ilist())
    def words(self):
        return list(self.iwords())
    def ilist(self): 
        if self.not_empty():
            return (line.rstrip().strip('\n')  for line in self.io.readlines())
    def list(self): 
        return list(self.ilist())
    def str(self): 
        if self.not_empty(): 
            return self.io.read().rstrip()
    @property
    def s(self): return self.str()
    @property
    def l(self): return self.list()
    @property
    def w(self): return self.words()
    @property
    def il(self): return self.ilist()
    @property
    def iw(self): return self.iwords() 

def func_for_py_expr(py_expr): 
    try:
        func = getattr(__builtints__, py_expr)
    except: 
        func = globals().get(py_expr)
    return func
    
def _parse_shell_expr(expr): 
    print(expr)
    re_res = re.search('\|{0,1} {0,1}\%[a-zA-Z0-9_ ()\.]*? \|{0,1}', expr)
    py_expr_res= None
    if re_res: 
        py_expr = expr[re_res.start():re_res.end()].strip('|').strip('%').strip(' ')
        print(py_expr)
        if expr[re_res.start()] == '|':
            start_expr = expr[:re_res.start()].replace('\%', '%').replace('\|', '|')
            proc = eval_shell_expr(start_expr)
            #this needs some fixing
            py_expr_res = func(ioWrap(proc))
        if expr[re_res.end() - 1] == '|': 
            expr = expr[re_res.end()+1:].replace('\%', '%').replace('\|', '|')
            if not py_expr_res: 
                py_expr_res = eval(py_expr)
        #else expr=None
        return eval_shell_expr(expr, py_expr_res) if expr else py_expr_res
    return eval_shell_expr(expr, py_expr_res)
    
def parse_shell_expr(expr): 
    return _parse_shell_expr(expr)
    
def eval_shell_expr(expr, load_in = None):
    re_res = re.search(' {0,1}\%[a-zA-Z0-9_]*', expr)
    if re_res:
        try: 
            sub = eval(expr[re_res.start(): re_res.end()].strip(' ').replace('\%', '%').strip('%'))
            expr = expr[:re_res.start()] +' '+ str(sub) +' ' + expr[re_res.end():] 
        except: pass
    return _eval_shell_expr(expr, load_in)
        
def _eval_shell_expr(expr, load_in= None):
    proc = sp.Popen(expr, stdout=sp.PIPE, stdin=sp.PIPE, stderr=sp.PIPE, universal_newlines=args.universal_newlines, shell=args.unsafe_shell_call)
    if load_in and isinstance(load_in, str): 
        try:
            proc.stdin.write(load_in.encode('utf-8'))
        except: pass
    elif load_in and isinstance(load_in, list):
        try:
            proc.stdin.write('\n'.join(str(load_in)).encode('utf-8'))
        except: pass
    return proc
        
def safe_eval(text):
    try:
        return literal_eval(text)
    except:
        return None
        
def unsafe_eval(text):
    try: 
        return eval(text)
    except: 
        return None

args = parser.parse_args()

#try:
def wrap_res(res): 
    if not isinstance(res, sp.Popen): return res
    err= res.stderr.read()
    if err:
        print(err)
    return ioWrap(res.stdout)
    
def store_res(res, num):
    globals()["expr_{}".format(num)] = wrap_res(res)

def puts(res): 
    if isinstance(res, ioWrap): 
        print(res.s)
    else: 
        if isinstance(res, list): 
            for l in res: print(l)
        else: print(res)

stdin= r = ioWrap(sys.stdin)
expression = args.expression.split(';')
eval_failed =  False
for num, line in enumerate(expression): 
    re_res = re.search('`.*`', line)
    if re_res: 
        shell_expr = line[re_res.start():re_res.end()].strip('`')
        #print(shell_expr)
        shell_func = lambda: parse_shell_expr(shell_expr)
        py_expr = (line[:re_res.start()] + "shell_func() " + line[re_res.end():]).strip()
    else: py_expr= line
    #print(py_expr)
    try: 
        res = eval(py_expr)
    except SyntaxError: 
        #print("exec", py_expr)
        if args.use_exec: 
            exec(py_expr)
        else: 
            SyntaxError("eval failed")
    try:
        r = res= wrap_res(res)
    except: res = None
    if args.store_all: 
        globals()[args.store_format_string.format(num)] = res
else:
    puts(res)
#except: pass
"""
TODO: 

Add default imports
Add default macros
"""
