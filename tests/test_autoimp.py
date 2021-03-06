# pyflyby/test_autoimp.py

# License for THIS FILE ONLY: CC0 Public Domain Dedication
# http://creativecommons.org/publicdomain/zero/1.0/

from __future__ import absolute_import, division, with_statement

import ast
import os
import pytest
from   shutil                   import rmtree
import sys
from   tempfile                 import mkdtemp
from   textwrap                 import dedent

from   pyflyby                  import (Filename, ImportDB, auto_eval,
                                        auto_import, find_missing_imports)
from   pyflyby._autoimp         import LoadSymbolError, load_symbol


@pytest.fixture
def tpp(request):
    """
    A temporary directory which is temporarily added to sys.path.
    """
    d = mkdtemp(prefix="pyflyby_test_autoimp_", suffix=".tmp")
    d = Filename(d).real
    def cleanup():
        # Unload temp modules.
        for name, module in sorted(sys.modules.items()):
            if (getattr(module, "__file__", None) or "").startswith(str(d)):
                del sys.modules[name]
        # Clean up sys.path.
        sys.path.remove(str(d))
        # Clean up directory on disk.
        rmtree(str(d))
    request.addfinalizer(cleanup)
    sys.path.append(str(d))
    return d


def writetext(filename, text, mode='w'):
    text = dedent(text)
    filename = Filename(filename)
    with open(str(filename), mode) as f:
        f.write(text)
    return filename


def test_find_missing_imports_basic_1():
    result   = find_missing_imports("os.path.join", namespaces=[{}])
    expected = ["os.path.join"]
    assert expected == result


def test_find_missing_imports_in_namespace_1():
    result   = find_missing_imports("os.path.join", namespaces=[{"os":os}])
    expected = []
    assert expected == result


def test_find_missing_imports_builtins_1():
    result   = find_missing_imports("os, sys, eval", [{"os": os}])
    expected = ['sys']
    assert expected == result


def test_find_missing_imports_undefined_1():
    result   = find_missing_imports("numpy.arange(x) + arange(y)", [{"y": 3}])
    expected = ['arange', 'numpy.arange', 'x']
    assert expected == result


def test_find_missing_imports_in_scope_1():
    result   = find_missing_imports("import numpy; numpy.arange(x) + arange(x)", [{}])
    expected = ['arange', 'x']
    assert expected == result


def test_find_missing_imports_in_scope_2():
    result   = find_missing_imports("from numpy import pi; numpy.pi + pi + x", [{}])
    expected = ['numpy.pi', 'x']
    assert expected == result


def test_find_missing_imports_in_scope_3():
    result   = find_missing_imports("for x in range(3): print numpy.arange(x)", [{}])
    expected = ['numpy.arange']
    assert expected == result


def test_find_missing_imports_in_scope_funcall_1():
    result   = find_missing_imports("foo1 = func(); foo1.bar + foo2.bar", [{}])
    expected = ['foo2.bar', 'func']
    assert expected == result


def test_find_missing_imports_in_scope_assign_attr_1():
    result   = find_missing_imports("a.b.y = 1; a.b.x, a.b.y, a.b.z", [{}])
    expected = ['a.b.x', 'a.b.z']
    assert expected == result


def test_find_missing_imports_lambda_1():
    result   = find_missing_imports("(lambda x: x*x)(7)", [{}])
    expected = []
    assert expected == result


def test_find_missing_imports_lambda_2():
    result   = find_missing_imports("(lambda x: x*x)(7) + x", [{}])
    expected = ['x']
    assert expected == result


def test_find_missing_imports_list_comprehension_1():
    result   = find_missing_imports("[x+y+z for x,y in [(1,2)]], y", [{}])
    expected = ['z']
    assert expected == result


def test_find_missing_imports_list_comprehension_nested_tuple_1():
    result   = find_missing_imports("[w+x+y+z for x,(y,z) in []]", [{}])
    expected = ['w']
    assert expected == result


def test_find_missing_imports_list_comprehension_nested_tuple_2():
    result   = find_missing_imports(
        "[a+A+b+B+c+C+d+D+e+E+f+F+g+G for a,((b,c),d,[e,f,(g,)]) in []]", [{}])
    expected = ['A','B','C','D','E','F','G']
    assert expected == result


def test_find_missing_imports_generator_expression_1():
    result   = find_missing_imports("(x+y+z for x,y in [(1,2)]), y", [{}])
    expected = ['y', 'z']
    assert expected == result


def test_find_missing_imports_qualified_1():
    result   = find_missing_imports("( ( a . b ) . x ) . y + ( c + d ) . x . y", [{}])
    expected = ['a.b.x.y', 'c', 'd']
    assert expected == result


def test_find_missing_imports_ast_1():
    node = ast.parse("import numpy; numpy.arange(x) + arange(x)")
    result   = find_missing_imports(node, [{}])
    expected = ['arange', 'x']
    assert expected == result


def test_find_missing_imports_print_function_1():
    node = ast.parse(
        "from __future__ import print_function\n"
        "print (42, file=sys.stdout)\n"
    )
    result   = find_missing_imports(node, [{}])
    expected = ['sys.stdout']
    assert expected == result


def test_find_missing_imports_assignment_1():
    code = dedent("""
        def f():
            x = 1
            print x, y, z
            y = 2
    """)
    result   = find_missing_imports(code, [{}])
    expected = ['y', 'z']
    assert expected == result


def test_find_missing_imports_function_body_1():
    code = dedent("""
        x1 = 1
        def func59399065():
            return x1 + x2 + x3
        x3 = 3
    """)
    result   = find_missing_imports(code, [{}])
    expected = ['x2']
    assert expected == result


def test_find_missing_imports_function_paramlist_1():
    code = dedent("""
        X1 = 1
        def func85025862(x1=X1, x2=X2, x3=X3):
            return x1 + x2 + x3
        X3 = 3
    """)
    result   = find_missing_imports(code, [{}])
    expected = ['X2', 'X3']
    assert expected == result


def test_find_missing_imports_function_defaults_1():
    code = dedent("""
        e = 1
        def func32466773(a=b, b=c, c=a, d=d, e=e, f=1):
            pass
    """)
    result   = find_missing_imports(code, [{}])
    expected = ['a', 'b', 'c', 'd']
    assert expected == result


def test_find_missing_imports_function_defaults_kwargs_1():
    code = dedent("""
        def func16049151(x=args, y=kwargs, z=y, *args, **kwargs):
            pass
    """)
    result   = find_missing_imports(code, [{}])
    expected = ['args', 'kwargs', 'y']
    assert expected == result


def test_find_missing_imports_function_defaults_kwargs_2():
    code = dedent("""
        args = 1
        kwargs = 2
        def func69790319(x=args, y=kwargs, z=y, *args, **kwargs):
            pass
    """)
    result   = find_missing_imports(code, [{}])
    expected = ['y']
    assert expected == result


def test_find_missing_imports_function_paramlist_local_1():
    code = dedent("""
        x1 = 1
        x2 = 2
        def func77361554(x1, x3, x4):
            pass
        x4 = 4
        x1, x2, x3, x4, x5
    """)
    result   = find_missing_imports(code, [{}])
    expected = ['x3', 'x5']
    assert expected == result


def test_find_missing_imports_function_paramlist_selfref_1():
    code = dedent("""
        f1 = 'x'
        def f2(g1=f1, g2=f2, g3=f3):
            return (g1, g2, g3)
        f3 = 'x'
    """)
    result   = find_missing_imports(code, [{}])
    expected = ['f2', 'f3']
    assert expected == result


def test_find_missing_imports_function_paramlist_lambda_1():
    code = dedent("""
        X1 = 1
        def func85025862(x1=lambda: 1/X1, x2=lambda: 1/X2, x3=lambda: 1/X3):
            return x1() + x2() + x3()
        X3 = 3
    """)
    result   = find_missing_imports(code, [{}])
    expected = ['X2']
    assert expected == result


def test_find_missing_imports_decorator_1():
    code = dedent("""
        deco1 = 'x'
        @deco1
        @deco2
        @deco3
        def func33144383():
            pass
        deco3 = 'x'
    """)
    result   = find_missing_imports(code, [{}])
    expected = ['deco2', 'deco3']
    assert expected == result


def test_find_missing_imports_decorator_selfref_1():
    code = dedent("""
        deco = 'x'
        func1 = 'x'
        @deco(func1, func2, func3)
        def func2():
            pass
        func3 = 'x'
    """)
    result   = find_missing_imports(code, [{}])
    expected = ['func2', 'func3']
    assert expected == result


def test_find_missing_imports_decorator_paramlist_1():
    code = dedent("""
        p2 = 2
        def deco(*args): pass
        @deco(p1, p2, p3)
        def foo74632516():
            pass
        p3 = 3
    """)
    result   = find_missing_imports(code, [{}])
    expected = ['p1', 'p3']
    assert expected == result


def test_find_missing_imports_classdef_1():
    code = dedent("""
        class Mahopac:
            pass
        class Gleneida(Mahopac):
            pass
        Mahopac, Carmel, Gleneida
    """)
    result   = find_missing_imports(code, [{}])
    expected = ['Carmel']
    assert expected == result


def test_find_missing_imports_class_base_1():
    code = dedent("""
        Mill = object
        class Mohansic(Crom, Mill):
            pass
    """)
    result   = find_missing_imports(code, [{}])
    expected = ['Crom']
    assert expected == result


def test_find_missing_imports_class_name_1():
    code = dedent("""
        class Corinne(object):
            pass
        class Bobtail(object):
            class Chippewa(object):
                pass
            Rockton = Passall, Corinne, Bobtail, Chippewa
    """)
    result   = find_missing_imports(code, [{}])
    expected = ['Bobtail', 'Passall']
    assert expected == result


def test_find_missing_imports_class_members_1():
    code = dedent("""
        class Kenosha(object):
            x = 3
            z = x, y
    """)
    result   = find_missing_imports(code, [{}])
    expected = ['y']
    assert expected == result


def test_find_missing_imports_class_member_vs_function_1():
    code = dedent("""
        class Sidney(object):
            x = 3
            def barracuda(self):
                return x, y
    """)
    result   = find_missing_imports(code, [{}])
    expected = ['x', 'y']
    assert expected == result


def test_find_missing_imports_class_member_vs_function_2():
    code = dedent("""
        class Wayne: pass
        class Connaught(object):
            class Windsor: pass
            def Mercury(self):
                return Wayne, Connaught, Windsor
    """)
    result   = find_missing_imports(code, [{}])
    expected = ['Windsor']
    assert expected == result


def test_find_missing_imports_class_member_vs_lambda_1():
    code = dedent("""
        x1 = 1
        class Salsa(object):
            x2 = 2
            x3 = 3
            y = [lambda y3=x3, y4=x4: x1 + x2 + x5 + x6]
        x4 = 4
        x5 = 5
    """)
    result   = find_missing_imports(code, [{}])
    expected = ['x2', 'x4', 'x6']
    assert expected == result


def test_find_missing_imports_class_member_vs_paramlist_1():
    code = dedent("""
        class Drake:
            duck2 = 2
            def quack(self, mallard1=duck1, mallard2=duck2, mallard3=duck3):
                pass
            duck3 = 3
    """)
    result   = find_missing_imports(code, [{}])
    expected = ['duck1', 'duck3']
    assert expected == result


def test_find_missing_imports_class_member_vs_paramlist_lambda_1():
    code = dedent("""
        class Breakfast:
            def corn1(self):
                pass
            def cereal(self, maize1=lambda: corn1, maize2=lambda: corn2,
                             maize3=lambda: corn3):
                return (maize1(), maize2())
            def corn2(self):
                pass
        def corn3(self):
            pass
    """)
    result   = find_missing_imports(code, [{}])
    expected = ['corn1', 'corn2']
    assert expected == result


def test_find_missing_imports_class_member_vs_paramlist_local_1():
    code = dedent("""
        class Legume:
            x1 = 1
            x2 = 2
            def func13585710(x1, x3, x4):
                pass
            x4 = 4
            y = x1, x2, x3, x4, x5
    """)
    result   = find_missing_imports(code, [{}])
    expected = ['x3', 'x5']
    assert expected == result


def test_find_missing_imports_class_member_vs_decorator_1():
    code = dedent("""
        def deco(): 1/0
        class Cat:
            def panther1(self):
                pass
            @deco(panther1, panther2, panther3)
            def growl(self):
                pass
            def panther2(self):
                pass
    """)
    result   = find_missing_imports(code, [{}])
    expected = ['panther2', 'panther3']
    assert expected == result


def test_find_missing_imports_inner_class_method_1():
    code = dedent("""
        class Sand(object):
            Dirt = 100
            class Silicon:
                def f(self):
                    return Sand, Dirt, Silicon, Glass
        class Glass:
            pass
    """)
    result   = find_missing_imports(code, [{}])
    expected = ['Dirt', 'Silicon']
    assert expected == result


def test_find_missing_imports_inner_class_attribute_1():
    code = dedent("""
        x = 100
        class Axel(object):
            a = 100
            class Beth:
                b = x + a
    """)
    result   = find_missing_imports(code, [{}])
    expected = ['a']
    assert expected == result


def test_find_missing_imports_class_member_function_ref_1():
    code = dedent("""
        class Niska(object):
            def f1(self): pass
            g = f1, f2
    """)
    result   = find_missing_imports(code, [{}])
    expected = ['f2']
    assert expected == result


def test_find_missing_imports_class_member_generator_expression_1():
    # Verify that variables leak out of list comprehensions but not out of
    # generator expressions.
    # Verify that both can see members of the same ClassDef.
    code = dedent("""
        class Caleb(object):
            x = []
            g1 = (1 for y1 in x)
            g2 = [1 for y2 in x]
            h = [y1, y2]
    """)
    result   = find_missing_imports(code, [{}])
    expected = ['y1']
    assert expected == result


def test_find_missing_imports_latedef_def_1():
    code = dedent("""
        def marble(x):
            return x + y + z
        z = 100
    """)
    result   = find_missing_imports(code, [{}])
    expected = ['y']
    assert expected == result


def test_find_missing_imports_latedef_lambda_1():
    code = dedent("""
        granite = lambda x: x + y + z
        z = 100
    """)
    result   = find_missing_imports(code, [{}])
    expected = ['y']
    assert expected == result


def test_find_missing_imports_latedef_def_def_1():
    code = dedent("""
        def twodot():
            return sterling() + haymaker() + cannon() + twodot()
        def haymaker():
            return 100
    """)
    result   = find_missing_imports(code, [{}])
    expected = ['cannon', 'sterling']
    assert expected == result


def test_find_missing_imports_latedef_innerdef_1():
    code = dedent("""
        def kichawan(w):
            def turkey(x):
                return v + w + x + y + z
            z = 100
        v = 200
    """)
    result   = find_missing_imports(code, [{}])
    expected = ['y']
    assert expected == result


def test_find_missing_imports_latedef_innerdef_2():
    code = dedent("""
        def maple(w):
            def drumgor(x):
                return v + w + x + y + z
            z = 100
        def springmere(w):
            def dorchester(x):
                return v + w + x + y + z
        v = 200
    """)
    result   = find_missing_imports(code, [{}])
    expected = ['y', 'z']
    assert expected == result


def test_find_missing_imports_latedef_classdef_1():
    code = dedent("""
        a = 100
        class Granite:
            x = a, b
            def springs(self):
                x, y, z
        b = 100
        z = 100
    """)
    result   = find_missing_imports(code, [{}])
    expected = ['b', 'x', 'y']
    assert expected == result


def test_find_missing_imports_latedef_func_class_func_1():
    code = dedent("""
        def Nellie():
            class Shelley:
                def Norman(self):
                    return Alfred, Sherry, Grover, Kirk
            Sherry = 100
        Kirk = 200
    """)
    result   = find_missing_imports(code, [{}])
    expected = ['Alfred', 'Grover']
    assert expected == result


def test_find_missing_imports_latedef_if_1():
    code = dedent("""
        if 1:
            def cavalier():
                x, y
        if 1:
            x = 1
    """)
    result   = find_missing_imports(code, [{}])
    expected = ['y']
    assert expected == result


def test_find_missing_imports_class_scope_comprehension_1():
    code = dedent("""
        class Plymouth:
            x = []
            z = list(1 for t in x+y)
    """)
    result   = find_missing_imports(code, [{}])
    expected = ['y']
    assert expected == result


def test_find_missing_imports_global_1():
    code = dedent("""
        def func10663671():
            global x
            x = x + y
        x = 1
    """)
    result   = find_missing_imports(code, [{}])
    expected = ['y']
    assert expected == result


def test_find_missing_imports_complex_1():
    code = dedent("""
        x = 3+4j+5L+k+u'a'
    """)
    result   = find_missing_imports(code, [{}])
    expected = ['k']
    assert expected == result


def test_find_missing_imports_code_1():
    f = lambda: foo.bar(x) + baz(y)
    result   = find_missing_imports(f.func_code, [{}])
    expected = ['baz', 'foo.bar', 'x', 'y']
    assert expected == result


def test_find_missing_imports_code_args_1():
    def f(x, y, *a, **k):
        return g(x, y, z, a, k)
    result   = find_missing_imports(f.func_code, [{}])
    expected = ['g', 'z']
    assert expected == result


def test_find_missing_imports_code_use_after_import_1():
    def f():
        import foo
        foo.bar()
    result   = find_missing_imports(f.func_code, [{}])
    expected = []
    assert expected == result


def test_find_missing_imports_code_lambda_scope_1():
    f = lambda x: (lambda: x+y)
    result   = find_missing_imports(f.func_code, [{}])
    expected = ['y']
    assert expected == result


def test_find_missing_imports_code_conditional_1():
    def f():
        y0 = x0
        if c:
            y1 = y0 + x1
        else:
            y2 = x2 + y0
        x3 + y0
        y1 + y2
    result   = find_missing_imports(f.func_code, [{}])
    expected = ['c', 'x0', 'x1', 'x2', 'x3']
    assert expected == result


def test_find_missing_imports_code_loop_1():
    def f():
        for i in range(10):
            if i > 0:
                use(x)
                use(y)
            else:
                x = "hello"
    result   = find_missing_imports(f.func_code, [{}])
    expected = ['use', 'y']
    assert expected == result


def test_load_symbol_1():
    assert load_symbol("os.path.join", {"os": os}) is os.path.join


def test_load_symbol_2():
    assert load_symbol("os.path.join.func_name", {"os": os}) == "join"


def test_load_symbol_missing_1():
    with pytest.raises(LoadSymbolError):
        load_symbol("os.path.join.asdfasdf", {"os": os})


def test_load_symbol_missing_2():
    with pytest.raises(LoadSymbolError):
        load_symbol("os.path.join", {})


def load_symbol_eval_1():
    assert 'a/b' == load_symbol("os.path.join('a','b')", {"os": os})
    assert '/'   == load_symbol("os.path.join('a','b')[1]", {"os": os})
    assert 'A'   == load_symbol("os.path.join('a','b')[0].upper()", {"os": os})


def load_symbol_eval_2(capsys):
    assert '/' == load_symbol("(os.path.sep[0])", {}, autoimport=True,
                              allow_eval=True)
    out, _ = capsys.readouterr()
    expected = dedent("""
        [PYFLYBY] import os
    """).lstrip()
    assert expected == out


def load_symbol_no_eval_1():
    with pytest.raises(LoadSymbolError):
        load_symbol("os.path.join('a','b')", {"os": os})
    with pytest.raises(LoadSymbolError):
        load_symbol("os.path.join('a','b')[1]", {"os": os})
    with pytest.raises(LoadSymbolError):
        load_symbol("os.path.join('a','b')[0].upper", {"os": os})


def load_symbol_wrap_exc_1():
    class Foo89503828(object):
        def __getattr__(self, k):
            1/0
    ns = [{"foo": Foo89503828()}]
    try:
        load_symbol("foo.bar", ns)
    except LoadSymbolError as e:
        assert type(e.__cause__) == ZeroDivisionError
    else:
        assert False


def load_symbol_wrap_exc_eval_1():
    def foo31617859():
        1/0
    ns = [{"foo": foo31617859()}]
    try:
        load_symbol("foo()", ns, auto_eval=True)
    except LoadSymbolError as e:
        assert type(e.__cause__) == ZeroDivisionError
    else:
        assert False


def load_symbol_wrap_exc_eval_getattr_1():
    class Foo15356301(object):
        def __getattr__(self, k):
            1/0
    ns = [{"foo": Foo15356301()}]
    try:
        load_symbol("foo.bar", ns, auto_eval=True)
    except LoadSymbolError as e:
        assert type(e.__cause__) == ZeroDivisionError
    else:
        assert False


def test_auto_eval_1():
    result = auto_eval("b64decode('aGVsbG8=')")
    assert result == 'hello'


def test_auto_eval_locals_import_1():
    mylocals = {}
    result = auto_eval("b64decode('aGVsbG8=')", locals=mylocals)
    assert result == 'hello'
    assert mylocals["b64decode"] is __import__("base64").b64decode


def test_auto_eval_globals_import_1():
    myglobals = {}
    result = auto_eval("b64decode('aGVsbG8=')", globals=myglobals)
    assert result == 'hello'
    assert myglobals["b64decode"] is __import__("base64").b64decode


def test_auto_eval_custom_locals_1():
    result = auto_eval("b64decode('aGVsbG8=')",
                                   locals=dict(b64decode=lambda x: "blah"))
    assert result == 'blah'


def test_auto_eval_custom_globals_1():
    result = auto_eval("b64decode('aGVsbG8=')",
                                   globals=dict(b64decode=lambda x: "blah"))
    assert result == 'blah'


def test_auto_eval_exec_1():
    mylocals = dict(x=[])
    auto_eval("if True: x.append(b64decode('aGVsbG8='))",
              locals=mylocals)
    assert mylocals['x'] == ['hello']
    assert mylocals["b64decode"] is __import__("base64").b64decode


def test_auto_eval_no_auto_flags_ps_flagps_1(capsys):
    auto_eval("print 3.00", flags=0, auto_flags=False)
    out, _ = capsys.readouterr()
    assert out == "3.0\n"


def test_auto_eval_no_auto_flags_ps_flag_pf1():
    with pytest.raises(SyntaxError):
        auto_eval("print 3.00", flags="print_function", auto_flags=False)


def test_auto_eval_no_auto_flags_pf_flagps_1():
    with pytest.raises(SyntaxError):
        auto_eval("print(3.00, file=sys.stdout)", flags=0, auto_flags=False)


def test_auto_eval_no_auto_flags_pf_flag_pf1(capsys):
    auto_eval("print(3.00, file=sys.stdout)",
              flags="print_function", auto_flags=False)
    out, _ = capsys.readouterr()
    assert out == "[PYFLYBY] import sys\n3.0\n"


def test_auto_eval_auto_flags_ps_flagps_1(capsys):
    auto_eval("print 3.00", flags=0, auto_flags=True)
    out, _ = capsys.readouterr()
    assert out == "3.0\n"


def test_auto_eval_auto_flags_ps_flag_pf1(capsys):
    auto_eval("print 3.00", flags="print_function", auto_flags=True)
    out, _ = capsys.readouterr()
    assert out == "3.0\n"


def test_auto_eval_auto_flags_pf_flagps_1(capsys):
    auto_eval("print(3.00, file=sys.stdout)", flags=0, auto_flags=True)
    out, _ = capsys.readouterr()
    assert out == "[PYFLYBY] import sys\n3.0\n"


def test_auto_eval_auto_flags_pf_flag_pf1(capsys):
    auto_eval("print(3.00, file=sys.stdout)",
              flags="print_function", auto_flags=True)
    out, _ = capsys.readouterr()
    assert out == "[PYFLYBY] import sys\n3.0\n"


def test_auto_eval_proxy_module_1(tpp, capsys):
    os.mkdir("%s/tornado83183065"%tpp)
    writetext(tpp/"tornado83183065/__init__.py", """
        import sys
        twister = 54170888
        class P:
            def __getattr__(self, K):
                k = K.lower()
                if k == K:
                    raise AttributeError
                else:
                    return getattr(self, k)
        p = P()
        p.__dict__ = globals()
        p._m = sys.modules[__name__]
        sys.modules[__name__] = p
    """)
    writetext(tpp/"tornado83183065/hurricane.py", """
        cyclone = 79943637
    """)
    # Verify that we can auto-import a sub-module of a proxy module.
    result = auto_eval("tornado83183065.hurricane.cyclone")
    out, _ = capsys.readouterr()
    expected = dedent("""
        [PYFLYBY] import tornado83183065
        [PYFLYBY] import tornado83183065.hurricane
    """).lstrip()
    assert out == expected
    assert result == 79943637
    # Verify that the proxy module can do its magic stuff.
    result = auto_eval("tornado83183065.TWISTER")
    out, _ = capsys.readouterr()
    assert out == "[PYFLYBY] import tornado83183065\n"
    assert result == 54170888
    # Verify that the proxy module can do its magic stuff with a submodule
    # that's already imported.
    result = auto_eval("tornado83183065.HURRICANE.cyclone")
    out, _ = capsys.readouterr()
    assert out == "[PYFLYBY] import tornado83183065\n"
    assert result == 79943637


def test_auto_import_1(capsys):
    auto_import("sys.asdfasdf", [{}])
    out, _ = capsys.readouterr()
    expected = dedent("""
        [PYFLYBY] import sys
    """).lstrip()
    assert expected == out


def test_auto_import_multi_1(capsys):
    auto_import("sys.asdfasdf + os.asdfasdf", [{}])
    out, _ = capsys.readouterr()
    expected = dedent("""
        [PYFLYBY] import os
        [PYFLYBY] import sys
    """).lstrip()
    assert expected == out


def test_auto_import_nothing_1(capsys):
    auto_import("sys.asdfasdf", [{"sys":sys}])
    out, _ = capsys.readouterr()
    assert out == ""


def test_auto_import_some_1(capsys):
    auto_import("sys.asdfasdf + os.asdfasdf", [{"sys":sys}])
    out, _ = capsys.readouterr()
    expected = dedent("""
        [PYFLYBY] import os
    """).lstrip()
    assert expected == out


def test_auto_import_custom_1(tpp, capsys):
    writetext(tpp/"trampoline77069527.py", """
        print('hello  world')
    """)
    auto_import("trampoline77069527.asdfasdf", [{}])
    out, _ = capsys.readouterr()
    expected = dedent("""
        [PYFLYBY] import trampoline77069527
        hello  world
    """).lstrip()
    assert expected == out


def test_auto_import_custom_in_pkg_1(tpp, capsys):
    os.mkdir(str(tpp/"truck56331367"))
    writetext(tpp/"truck56331367/__init__.py", "")
    writetext(tpp/"truck56331367/tractor.py", """
        print('hello  there')
    """)
    auto_import("truck56331367.tractor", [{}])
    out, _ = capsys.readouterr()
    expected = dedent("""
        [PYFLYBY] import truck56331367
        [PYFLYBY] import truck56331367.tractor
        hello  there
    """).lstrip()
    assert expected == out


def test_auto_import_unknown_1(capsys):
    # Verify that if we try to access something that doesn't appear to be a
    # module, we don't attempt to import it (or at least don't log any visible
    # errors for it).
    auto_import("electron91631346.asdfasdf", [{}])
    out, _ = capsys.readouterr()
    assert out == ""


def test_auto_import_unknown_but_in_db1(tpp, capsys):
    # Verify that if we try to access something that's in the known-imports
    # database, but it doesn't actually exist, we get a visible error for it.
    db = ImportDB('import photon70447198')
    auto_import("photon70447198.asdfasdf", [{}], db=db)
    out, _ = capsys.readouterr()
    expected = dedent("""
        [PYFLYBY] import photon70447198
        [PYFLYBY] Error attempting to 'import photon70447198': ImportError: No module named photon70447198
        Traceback (most recent call last):
    """).lstrip()
    assert out.startswith(expected)


def test_auto_import_fake_importerror_1(tpp, capsys):
    writetext(tpp/"proton24412521.py", """
        raise ImportError("No module named proton24412521")
    """)
    auto_import("proton24412521.asdfasdf", [{}])
    out, _ = capsys.readouterr()
    expected = dedent("""
        [PYFLYBY] import proton24412521
        [PYFLYBY] Error attempting to 'import proton24412521': ImportError: No module named proton24412521
        Traceback (most recent call last):
    """).lstrip()
    assert out.startswith(expected)


def test_auto_import_indirect_importerror_1(tpp, capsys):
    writetext(tpp/"neutron46291483.py", """
        import baryon96446873
    """)
    auto_import("neutron46291483.asdfasdf", [{}])
    out, _ = capsys.readouterr()
    expected = dedent("""
        [PYFLYBY] import neutron46291483
        [PYFLYBY] Error attempting to 'import neutron46291483': ImportError: No module named baryon96446873
        Traceback (most recent call last):
    """).lstrip()
    assert out.startswith(expected)


def test_auto_import_nameerror_1(tpp, capsys):
    writetext(tpp/"lepton69688541.py", """
        foo
    """)
    auto_import("lepton69688541.asdfasdf", [{}])
    out, _ = capsys.readouterr()
    expected = dedent("""
        [PYFLYBY] import lepton69688541
        [PYFLYBY] Error attempting to 'import lepton69688541': NameError: name 'foo' is not defined
        Traceback (most recent call last):
    """).lstrip()
    assert out.startswith(expected)
