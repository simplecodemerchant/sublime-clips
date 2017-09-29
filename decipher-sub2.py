import sublime_plugin, sublime
import sys
import os
import re

try:
    from factory.Cells import Cells
except ImportError:
    try:
        from .factory.Cells import Cells
    except ImportError as e:
        if str( e ).find( 'bad magic number' ) != -1:
            need_package_control_upgrade = True
        else:
            raise


class Director():

    def __init__( self, view, edit, req, t ):
        self.view = view
        self.edit = edit
        self.req = req
        self.t = t


    def fixUniCode( self, text ):
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


    def clean( self, text ):
        return self.fixUniCode( text )


    def run( self ):
        try:
            for sel in self.view.sel():
                text = self.clean( self.view.substr( sel ).strip() )
                req = self.req()
                text = req.run( text, self.t )

                self.view.replace(self.edit, sel, text )
        except Exception as e:
            print( e )


class Custom( sublime_plugin.TextCommand ):
    def run( self, edit ):
        d = Director( self.view, edit, Cells, 'row')
        d.run()
