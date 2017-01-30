from pygments.lexer import RegexLexer, bygroups
from pygments.token import *


# http://pygments.org/docs/lexerdevelopment/
class TagsetbenchLexer(RegexLexer):
    name = 'tagsetbench'
    aliases = ['tagsetbench']
    filenames = ['*.tagsetbench']
    tokens = {
        'root': [
            # (r'\s*[#%][^;\n]*\n', Comment),
            (r'\s*[#%][^;\n]*\n', Text),
            (r'(\s*)(COMPARE|EVALUATE|TRAINING_TESTING|TRAINING|TESTING|FILTER|MATCH|SET|DEL)',
             bygroups(Text, Keyword)),
            (r'(\s*)([^=\n;]+)(\s*)(=)(\s*)([^;\n]*)(;?)',
             bygroups(Text, Name.Attribute, Text, Operator, Text, String, Operator)),
            (r';', Operator),
            (r'[^\n;]+', String),
            # (r'[^;]*\n', Text),
        ]
    }


__all__ = ['TagsetbenchLexer']
# cd /usr/lib/python3.5/site-packages/pygments/lexers
# ln -s /home/Škola/Diplomka/tagsetbench/pygments_lexer.py tagsetbench.py
# python _mapping.py
# pygmentize -l tagsetbench -f html
