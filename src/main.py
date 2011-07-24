import re, logging
from time import sleep

logging.basicConfig(level=logging.INFO)

class Word(object):
    def __init__(self, function, name, types, inputs):
        if name == '': raise ValueError("Invalid name")
        if len(types) > 0 and len(types) != inputs: 
            raise ValueError("Types and inputs don't match")
        self.name = name
        self.function = function
        self.types = types  
        self.inputs = inputs

class Interpreter(object):
    def __init__(self):
        self.stack = []
        
        self.lex = re.compile("""([a-zA-Z_][a-zA-Z0-9_]*)|"""
                              """('(?:\\.|[^'])*'?)|"""
                              """("(?:\\.|[^"])*"?)|"""
                              """(-?[0-9]+)|"""
                              """(#[^\n\r]*)|(.)""", re.M)
        self.noop   = lambda x: x
        self.lexems = ["w","s","s","i","comment","w"]
        self.conv   = [self.noop,eval,eval,int,self.noop,self.noop]

        self.words = {}
        self.construct_language()
        
    def interpret(self, prg):
        c=[[(self.lexems[i],self.conv[i](j)) 
            for i,j in enumerate(x) if j != ''][0] 
            for x in self.lex.findall(prg)][::-1]
        logging.debug(c)
        def recurse_blocks(inp):
            s = []
            while True:
                i = c.pop()
                if    i[1] == '}': return ("b",s)
                elif  i[1] == '{': s.append(recurse_blocks(inp))
                else:              s.append(i)
            raise ValueError("Blocks don't match.")
        code = []
        while c:
            i = c.pop()
            if   i[1] == '{': code.append(recurse_blocks(c))
            elif i[1] == '}': raise ValueError("Blocks don't match.")
            else:             code.append(i)
        return code[::-1]

    def exec_ast(self, c):
        def try_run(tm,ks):
            logging.debug("try_run: %s %s %s" % (tm,ks,self.stack[-2:]))
            for k in ks:
                # go through possible type set and try to match
                if len(k) <= len(self.stack):
                    t = get_types(len(k))
                    if t == k:     
                        ex_func(tm,t)
                        return True
                else:
                    raise ValueError("Stack underflow. ",self.stack)
            return False
    
        def ex_func(tm,t):
            logging.debug("exec: %s %s %s" % (tm,t,self.stack))   
            sp = []
            for _ in range(self.words[tm][t].inputs): sp.append(self.stack.pop())
            r = self.words[tm][t].function(*sp)
            if r: self.stack.extend(r)
            
        def get_types(i):
            return ''.join([x[0] for x in self.stack[-i:]])
        
        logging.debug("exec_ast(): %s %s" % (self._quote(c[::-1])[0][1], self.stack))
        while c:
            i = c.pop()
            if i[0] == "w":
                # operator
                if i[1] in self.words:
                    # found token in wordlist
                    tm = i[1]
                    ks = self.words[tm].keys()
                    
                    if ks[0] != '': # word has typed parameters
                        if not try_run(tm,ks): 
                            # no match found, try and coerce the types to fit
                            #if tm not in "+-|&^": # only for these ops
                            #    raise ValueError("False coerce") # else error
                            self.stack[-1],self.stack[-2] = \
                                self._coerce(self.stack[-1],self.stack[-2])
                            ex_func(tm,get_types(2))
                    else:
                        # words with no types
                        ex_func(tm,'')
                        
                elif self.stack[-1][1] == ':':
                    # variable definition
                    self.stack.pop()
                    x = self.stack[-1]
                    f = (lambda: [x])
                    self.words[i[1]] = {'':Word(f,i[1],'',0)}
                    logging.debug("set: %s %s" % (i[1],self.stack[-1]))
                else:
                    raise ValueError("Function not found: %s" % (i[1]))

            else:
                # not a word, just add to stack
                self.stack.append(i)
        return self.stack
    
    def run(self, p):
        return self.exec_ast(self.interpret(p))
    
    def add_word(self, n, t, inp):
        def wrap(f):
            if n in self.words:
                self.words[n][t] = Word(f,n,t,inp)
            else:
                self.words[n] = {t:Word(f,n,t,inp)}
            return f
        return wrap
    
    def construct_language(self):
        @self.add_word('+', 'ii', 2) 
        def i_i_plus(a,b): return [('i', a[1]+b[1])]

        @self.add_word('+', 'aa', 2)
        def a_a_plus(a,b): return [('a', b[1]+a[1])]
        
        @self.add_word('+', 'bb', 2)
        def b_b_plus(a,b): return [('b', b[1]+a[1])]
    
        @self.add_word('-', 'ii', 2)
        def i_i_sub(a,b): return [('i', b[1]-a[1])]
        
        @self.add_word('-', 'aa', 2)
        def a_a_sub(a,b): return [('a', [x for x in b[1] if x not in a[1]])]
    
        @self.add_word('*', 'ii', 2)
        def i_i_mul(a,b): return [('i', a[1]*b[1])]
        
        @self.add_word('*', 'bi', 2)
        def b_i_mul(a,b): return [('i', b[1])]
        
        @self.add_word('*', 'ai', 2)
        def a_i_mul(a,b): return [('i', b[1])]
        
        @self.add_word('*', 'aa', 2)
        def a_a_mul(a,b): return [('a', a[1])]
        
        @self.add_word('*', 'ss', 2)
        def s_s_mul(a,b): return [('s', a[1])]
        
        @self.add_word('*', 'ab', 2)
        def a_b_mul(a,b):
#            x = len(b)-1
#            for _ in range(x):
#                i,j = b.pop(),b.pop()
#                cm = a[::-1]+[i]+[j]
#                self.exec_ast(cm)
#                self.stack.append(self.stack[-1])
            pass
        
    
        @self.add_word('/', 'ii', 2)
        def i_i_each(a,b): return [('i', b[1]/a[1])]
        
        @self.add_word('/', 'aa', 2)
        def a_a_each(a,b): return [('a', b[1])]
        
        @self.add_word('/', 'ai', 2)
        def a_i_each(a,b): return [('i', b[1])]
        
        @self.add_word('/', 'bb', 2)
        def b_b_each(a,b): return [('b', b[1])]
        
        @self.add_word('/', 'ab', 2)
        def a_b_each(a,b): return [('b', b[1])]
        
        @self.add_word('/', 'ss', 2)
        def s_s_each(a,b): return [('s', b[1])]
    
        @self.add_word('%', 'ii', 2)
        def i_i_mod(a,b): return [('i', b[1]%a[1])]
        
        @self.add_word('%', 'aa', 2)
        def a_a_mod(a,b): raise ValueError("Unimplemented.")
        
        @self.add_word('%', 'ai', 2)
        def a_i_mod(a,b): return [('a', b[1][::a[1]])]
    
        @self.add_word('%', 'ab', 2)
        def a_b_mod(a,b):
            x = []
            for i in b[1]:
                cm = [i]+a[1]
                x.append(self.exec_ast(cm[::-1])[0])
            return [('a', x)]
    
        @self.add_word('?', 'ii', 2)
        def i_i_poww(a,b): return [('i', b[1]**a[1])]
        
        @self.add_word('?', 'ia', 2)
        def i_a_poww(a,b):
            for i,j in enumerate(b[1]): 
                if a[1] == j[0]: return [i]
            return [('i', -1)]
        
        @self.add_word('?', 'ab', 2)
        def a_b_poww(a,b):
            for i in b[1]:
                r = self.exec_ast(a[1][::-1]+[i])
                if r[0] == ('i', 1): return [i]
                
                
        @self.add_word('<', 'ii', 2)
        def i_i_lessert(a,b): return [('i', 0 if a[1]<b[1] else 1)]
        
        @self.add_word('<', 'ai', 2)
        def a_i_lessert(a,b): return [('a', [i for i in b[1] if i[1]<a[1]])]
        
        @self.add_word('>', 'ii', 2)
        def i_i_greatert(a,b): return [('i', 0 if a[1]>b[1] else 1)]
        
        @self.add_word('>', 'ai', 2)
        def a_i_greatert(a,b): return [('a', [i for i in b[1] if i[1]>=a[1]])]
    
        @self.add_word('~', 'i', 1)
        def i_bitwise(a): return [('i', ~a[1])]
        
        @self.add_word('~', 's', 1)
        def s_bitwise(a): return self.exec_ast(self.interpret(a[1]))
        
        @self.add_word('~', 'b', 1)
        def b_bitwise(a): return self.exec_ast(a[1][::-1])
        
        @self.add_word('~', 'a', 1)
        def a_bitwise(a): return a[1]
    
        @self.add_word(',', 'i', 1)
        def i_comma(a): return [('a', [('i', x) for x in range(a[1])])]
        
        @self.add_word(')', 'i', 1)
        def i_inc(a): return [('i', a[1]+1)]
        
        @self.add_word('(', 'i', 1)
        def i_dec(a): return [('i', a[1]-1)]
        
        @self.add_word('!', 'i', 1)
        def i_exlamation(a): return [('i',1-a[1])]
        
        @self.add_word('\\', '', 2)
        def swap(a,b): return [a,b]
        
        @self.add_word('.', '', 1)
        def dup(a): return [a,a]
        
        @self.add_word(';', '', 1)
        def drop(a): pass
        
        @self.add_word('@', '', 3)
        def rot3(a,b,c): return [b,a,c] 
        
        @self.add_word('`', '', 1)
        def quote(a): return self._quote(a)
        
        @self.add_word('[', '', 0)
        def bracko(): return [('w','[')]

        @self.add_word(']', '', 0)
        def bracke():        
            l = []
            while self.stack and self.stack[-1][1] != '[': l.append(self.stack.pop())
            if self.stack and self.stack[-1][1] == '[': self.stack.pop()
            self.stack.append(('a', l[::-1]))  
        
        @self.add_word('p', '', 1)
        def pputs(): print quote()[1]
        
        @self.add_word(' ', '', 0)
        def none(): pass
        
        @self.add_word(':', '', 0)
        def sett(): return [('w',':')]
    
        @self.add_word('do', 'b', 1)
        def b_doo(a): 
            while True:
                self.exec_ast(a[1][::-1])
                if not self._true(self.stack.pop()): break

        @self.add_word('$', 'i', 1)
        def i_dollar(a): return [self.stack[-(a[1]+1)]] 
        
        @self.add_word('$', 'a', 1)
        def a_dollar(a): return [('a', a[1].sort())]
        
        @self.add_word('$', 's', 1)
        def s_dollar(a): return [('s', a[1])]
        
        @self.add_word('$', 'b', 1)
        def b_dollar(a): return [('b', [])]

    # 0 [] "" {} = false, everything else = true
    def _false(self, a):
        return a == ('i', 0) or a == ('a', []) or a == ('s', '') or a == ('b', [])
    
    def _true(self, a):
        return not self._false(a)
    
    def _quote(self, a):
        logging.debug(a)
        def ww(i):
            if i[0] == 'i': return repr(i[1])
            if i[0] == 's': return i[1] #'\"' + i[1] + '\"'
            if i[0] == 'w': return i[1]
            if i[0] == 'a': return "[" + ' '.join([ww(x) for x in i[1]]) + "]"
            if i[0] == 'b': return '{' + ''.join([ww(x) for x in i[1]]) + '}'
        if   type(a) == type([]): t = ' '.join([ww(x) for x in a])
        elif type(a) == type(()): t = ww(a)
        return [('s', t)]

    def _coerce(self,a,b):
        def _raise(a):
            if a[0] == 'i': return ('a', [a])
            if a[0] == 'a': return ('s', str(a[1]))
            if a[0] == 's': return ('b', [a]+[('w',' ')])
        
        order = {'i':0,'a':1,'s':2,'b':3}
        
        logging.debug("%s %s" % (a,b))
    
        while a[0] != b[0]:
            if   order[a[0]] > order[b[0]]: b = _raise(b)
            elif order[b[0]] > order[a[0]]: a = _raise(a)
        
        return a,b
 
def run_tests():
    gs_com = [("""5~""","""-6"""),
              (""""1 2+"~""","""3"""),
              ("""{1 2+}~""","""3"""),
              ("""[1 2 3]~""","""1 2 3"""),
              ("""1`""",""" "1" """),
              ("""[1 [2] 'asdf']`""",' \"[1 [2] \\\"asdf\\\"]\"'),
              (""" "1"`""",""" "\"1\"" """),
              ("""{1}""",""" "{1}" """),
              ("""1 2 3 4 @""","""1 3 4 2"""),
              ("""1 2 3 4 5  1$""","""1 2 3 4 5 4"""),
              ("""'asdf'$""",""" "adfs" """),
              ("""[5 4 3 1 2]{-1*}$""","""[5 4 3 2 1]"""),
              ("""5 7+""","""12"""),
              ("""'asdf'{1234}+""","""{asdf 1234}"""),
              ("""[1 2 3][4 5]+""","""[1 2 3 4 5]"""),
              ("""1 2-3+""","""1 -1"""),
              ("""1 2 -3+""","""1 -1"""),
              ("""1 2- 3+""","""2"""),
              ("""[5 2 5 4 1 1][1 2]-""","""[5 5 4]"""),
              ("""2 4*""","""8"""),
              ("""2 {2*} 5*""","""64"""),
              ("""[1 2 3]2*""","""[1 2 3 1 2 3]"""),
              ("""3'asdf'*""",""" "asdfasdfasdf" """),
              ("""[1 2 3]','*""",""" "1,2,3" """),
              ("""[1 2 3][4]*""","""[1 4 2 4 3]"""),
              ("""'asdf'' '*""",""" "a s d f" """),
              ("""[1 [2] [3 [4 [5]]]]'-'*""",""" "1-\002-\003\004\005" """),
              ("""[1 [2] [3 [4 [5]]]][6 7]*""","""[1 6 7 2 6 7 3 [4 [5]]]"""),
              ("""[1 2 3 4]{+}*""","""10"""),
              #("""'asdf'{+}*""","""414"""),
              ("""7 3 /""","""2"""),
              ("""[1 2 3 4 2 3 5][2 3]/""","""[[1] [4] [5]]"""),
              ("""'a s d f'' '/""","""["a" "s" "d" "f"]"""),
              ("""[1 2 3 4 5] 2/""","""[[1 2] [3 4] [5]]"""),
              ("""0 1 {100<} { .@+ } /""","""89 [1 1 2 3 5 8 13 21 34 55 89]"""),
              ("""[1 2 3]{1+}/""","""2 3 4"""),
              ("""7 3 %""","""1"""),
              #("""'assdfs' 's'%""","""["a" "df"]"""),
              #("""'assdfs' 's'/""","""["a" "" "df" ""]"""),
              ("""[1 2 3 4 5] 2%""","""[1 3 5]"""),
              ("""[1 2 3 4 5] -1%""","""[5 4 3 2 1]"""),
              ("""[1 2 3]{.}%""","""[1 1 2 2 3 3]"""),
              #("""5 3 |""","""7"""),
              #("""[1 1 2 2][1 3]&""","""[1]"""),
              #("""[1 1 2 2][1 3]^""","""[2 3]"""),
              #("""'\n'""",""" "\\n" """),
              #("""' \' '""",""" " ' " """),
              #(""" "\n" """,""" "\n" """),
              #(""" "\144" """,""" "d" """),
              ("""1 2 [\]""","""[2 1]"""),
              ('1 2 3',"""1 3 2"""),
              ("""1:a a""","""1 1"""),
              ("""1:O;O""","""1"""),
              ("""1 2 3;""","""1 2"""),
              ("""3 4 <""","""1"""),
              #(""" "asdf" "asdg" <""","""1"""),
              ("""[1 2 3] 2 <""","""[1 2]"""),
              ("""{asdf} -1 <""","""{asd}"""),
              ("""3 4 >""","""0"""),
              (""" "asdf" "asdg" >""","""0"""),
              ("""[1 2 3] 2 >""","""[3]"""),
              ("""{asdf} -1 >""","""{f}"""),
              ("""3 4 =""","""0"""),
              (""" "asdf" "asdg" =""","""0"""),
              ("""[1 2 3] 2 =""","""3"""),
              ("""{asdf} -1 =""","""102"""),
              ("""10,""","""[0 1 2 3 4 5 6 7 8 9]"""),
              ("""10,,""","""10"""),
              ("""10,{3%},""","""[1 2 4 5 7 8]"""),
              ("""1 2 3""","""1 2 3 3"""),
              ("""2 8?""","""256"""),
              ("""5 [4 3 5 1] ?""","""2"""),
              ("""[1 2 3 4 5 6] {.* 20>} ?""","""5"""),
              ("""5(""","""4"""),
              ("""[1 2 3](""","""[2 3] 1"""),
              ("""5)""","""6"""),
              ("""[1 2 3])""","""[1 2] 3"""),
              ("""1 2 3 if""","""2"""),
              ("""0 2 {1.} if""","""1 1""")
              ]
    tests = [("""3 2.""","3 2 2"),
             ("""[3 2].[5]""","[3 2] [3 2] [5]"),
             ("""1 2 3@""","2 3 1"),
             ("""1 2\\""","2 1"),
             ("""1 1+""","2"),
             ("""2 4*""","8"),
             ("""7 3 /""","2"),
             ("""5 2 ?""","25"),
             ("""5`""","5"),
             ("""[1 2 3]`""","[1 2 3]"),
             (""" 3 4 >""","0"),
             ("""[1 2 3 4]{+}*""","10"),
             ("""{[2 3 4] 5 3 6 {.@\%.}*}`""","{[2 3 4] 5 3 6 {.@\%.}*}"),
             (""" 5,`""","[0 1 2 3 4]"),
             ("""[1 2 3 4 5 6]{.* 20>}?""","5"),
             ("""5 1+,1>{*}*""","120"),
             ("""[1 2 3][4 5]+""","[1 2 3 4 5]"),
             ("""5{1-..}do""","4 3 2 1 0 0"),
             ("""2706 410{.@\%.}do;""","82"),
             ("""5 2,~{.@+.100<}do""","5 89 144"),
             ("""5,{1+}%{*}*""","120")]
    
    #program = """~:@.{0\`{15&.*+}/}*1=!"happy sad "6/=@,{@\)%!},,2=4*"non-prime">"""
    #program = """'asdf'{+}*"""
    #program = """99{n+~."+#,#6$DWOXB79Bd")base`1/10/~{~2${~1$+}%(;+~}%++=" is "\"."1$4$4-}do;;;"magic." """
    #program = """''6666,-2%{2+.2/@*\/10.3??2*+}*`50<~\;"""
    ntp = Interpreter()
    for it in gs_com:
        #print it
        #try:
        res = ntp._quote(ntp.run(it[0]))[0][1]
        if it[1]==res: print "SUCC:",it[0],"=>",res
        else: print "FAIL:",it[0],"=>",res," | ",it[1]
        ntp.stack = []

run_tests()           
#print exec_ast(interpret("""5:B;B"""), [])
