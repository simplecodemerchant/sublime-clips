import sublime_plugin, sublime
import re
import sys
import os

# In development

def fixUniCode( text ):
    rep = [
        (u"\u2019", "'"),
        (u"\u2018", "'"),
        (u"\u201C", "\""),
        (u"\u201D", "\""),
        (u"\u2014", '&amp;mdash;'),
        (u"\u2013", '&amp;ndash;'),
        ("&\s", '&amp;'),
    ]
    rep = dict( (re.escape( k ), v) for k, v in rep )
    pattern = re.compile( "|".join( rep.keys() ) )

    return pattern.sub( lambda f: rep[ re.escape( f.group( 0 ) ) ], text )


# Label = r or c or ch + any combo 4 characters long
rowPatternAA = re.compile( r"^(?:r|ch|c)?([a-zA-Z0-9]{1,4})(?:[.:\)]*?)(?:[\s\t]+?)(.+)$" )
# No label found. Just start labeling at 1 and increment
rowPatternCA = re.compile( r"^(.*)$" )


# Question template
question_template = """
<{question} 
  label="{label}"{extra}> 
  <title>{title}</title>
{cells}
</{question}>
""".strip()

# Question regex
cellFragmentStart = "<row|<col|<choice|<comment|<group|<net|<exec|\s+\@"
questionPatternAA = re.compile("^\s*(?:([a-zA-Z0-9]+)(?:\.([0-9]))?)\s*[.)\]]*([\w\W]*)")
cellPatternStartAA = re.compile("{}".format(cellFragmentStart))
# questionPatternAA = re.compile(("^\s*(?:([a-zA-Z0-9]+)(?:\.([0-9]))?)\s*[.)\]]*"
#                                 "([\w\s\n\r<>=\"\'/]*?)"
#                                 "(?:{})?".format(cellFragmentStart)))

class CellFactory:
    def __init__(self, **options):
        self.prefix = options.get('prefix', 'r')
        self.cell = options.get('cell', 'row')
        self.delimiter = options.get('delimiter', '\n')

    def smart_label(self, line, idx ):

        line = re.sub( r"\n([\s]*)\n", r"\n", line )
        line = re.sub( r"[_]{2,}", r"", line )
        line = re.sub( r"((?i)other|specify)([:)]*)([\s]*)([_]+)", r"\1\2", line )

        row_paa = rowPatternAA.search( line )

        if row_paa:
            label, text = row_paa.groups()
        else:
            catchall = rowPatternCA.search( line )
            label = idx
            text = catchall.groups()[ 0 ]

        extra = ''
        if re.match( r"((?i)other.*specify)", text ):
            extra = u' other="1" openSize="20" randomize="0"'

        return { 'label': label, 'text': text, 'extra': extra }

    def make_label(self, lines ):

        ppa = [ ]
        for idx, line in enumerate( lines, 1 ):
            ppa.append( self.smart_label( line, idx ) )
        return ppa

    def from_template(self, line):
        template = '  <{cell} label="{prefix}{label}"{extra}>{text}</{cell}>'
        return template.format(cell=self.cell, prefix=self.prefix, **line)

    def run(self, text):
        lines = text.split(self.delimiter)
        return  '\n'.join(list(map(self.from_template, self.make_label(lines))))


class CellTask:

    def __init__(self, view, edit, method, **options):
        self.view = view
        self.edit = edit
        self.options = options

        self.method = self.get_method(method)

    def get_method(self, method):
        return {
            'cell': CellFactory
        }[method](**self.options)


    def run(self):
        try:
            for sel in self.view.sel():
                pp = fixUniCode( self.view.substr( sel ).strip() )
                pp = self.method.run(pp)

                self.view.replace(self.edit, sel, pp)

        except Exception as e:
            print(e)


class Cells(sublime_plugin.TextCommand):
    def run (self, edit, **args):
        (CellTask(
            self.view,
            edit,
            'cell',
            cell=args['cell'],
            prefix=args['prefix']
        )).run()


class QuestionFactory:
    def __init__(self, **options):
        self.question = options.get('question')
        self.special = options.get('special')

    def set_extras( self ):
        extras = []
        if self.question in ['checkbox']:
            extras.append('atleast="1"')

        if self.question in ['text', 'textarea', 'select']:
            extras.append('optional="0"')

        if len(extras):
            return '\n  {}'.format('\n  '.join(extras))
        else:
            return ''


    def get_label( self, text ):
        question_group = questionPatternAA.search(text)

        if question_group:
            label, labelextra, rest = question_group.groups()
            cellindex = cellPatternStartAA.search(rest).start()

            if labelextra:
                label = '{}_{}'.format(label, labelextra)

            # todo: This needs to be re-thought
            title = rest[:cellindex]
            cells = rest[ cellindex: ].strip()
            cells = re.sub('\n\s*({})'.format(cells), '\n  \1', cells)
            cells = re.sub('\n\s+@', '\n@', cells)
            cells = '{}'.format(cells)

            return label, title, cells
        else:
            raise Exception('Invalid label / title setup')

    def run( self, text ):
        label, title, cells = self.get_label(text)

        return question_template.format(question=self.question,
                                        label=label,
                                        title=title,
                                        extra=self.set_extras(),
                                        cells=cells)

class QuestionTask:

    def __init__(self, view, edit, method, **options):
        self.view = view
        self.edit = edit
        self.options = options

        self.method = self.get_method(method)

    def get_method(self, method):
        return {
            'question': QuestionFactory
        }[method]( **self.options )


    def run(self):
        try:
            for sel in self.view.sel():
                pp = fixUniCode( self.view.substr( sel ).strip() )
                pp = self.method.run(pp)

                self.view.replace(self.edit, sel, pp)

        except Exception as e:
            print(e)


class Questions(sublime_plugin.TextCommand):
    def run( self, edit, **args ):
        ( QuestionTask(
            self.view,
            edit,
            'question',
            question=args['question'],
            special=args.get('special', None)
        ) ).run()