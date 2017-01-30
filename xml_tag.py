from shlex import escape, shlex


class XmlTag:
    def __init__(self, original_lines=None, name=None, closing=None,
                 empty=None, attributes=None, indentation_level=0):
        self.original_lines = original_lines
        self.name = name
        self.closing = closing
        self.empty = empty
        self.attributes = attributes or []
        self.indentation_level = indentation_level

    @property
    def opening(self):
        return not self.closing

    def append(self, attr, value):
        self.attributes.append((attr, value))

    def __contains__(self, key):
        return key in (attr for attr, val in self.attributes)

    def clear(self):
        self.attributes.clear()

    def __getitem__(self, key):
        """Get the last value attr."""
        for i in range(1, len(self.attributes) + 1):  # enumerate_reversed
            attr, value = self.attributes[-i]
            if key == attr:
                return value
        else:
            return None

    def __setitem__(self, attr, value):
        """Set the value to the last occurence of attr, or append a new one."""
        for i in range(1, len(self.attributes) + 1):  # enumerate_reversed
            old_attr, _ = self.attributes[-i]
            if attr == old_attr:
                self.attributes[-i] = (attr, value)
                break
        else:
            self.attributes.append((attr, value))

    def __iter__(self):
        return iter(self.attributes)

    def __str__(self):
        opening = '' if self.opening else '/'
        empty = '/' if self.empty else ''
        attrs = ''.join(
            ' {}="{}"'.format(attr, val.replace('"', '&quot;')) for attr, val
            in self.attributes)
        return '{indent}<{opening}{name}{attrs}{empty}>'.format(
            opening=opening, name=self.name, attrs=attrs, empty=empty,
            indent='  '*self.indentation_level)

    def __repr__(self):
        return 'XmlTag(' + escape(self) + ')'

    @classmethod
    def parse(cls, line, line_number=None):
        parser = shlex(line[1:])  # TODO: radši jednou get_token() == '<'
        tag = cls()
        tag.original_lines = [(line_number, line)]
        attr = None
        value = None
        while True:
            token = parser.get_token()  # ValueError("No closing quotation")
            if not token:
                break
            elif tag.closing is None:
                tag.closing = token == '/'
                if tag.opening:
                    tag.name = token
            elif tag.name is None:
                if token == '>':
                    break
                tag.name = token
            elif attr is None:
                if token == '/':
                    tag.empty = True
                elif token == '>':
                    break
                elif token == '=':
                    break  # unexpected =
                else:
                    attr = token
                    value = '='  # expecting =
            elif tag.empty:
                if token == '>':
                    break
                else:
                    break  # unexpected /
            elif value == '=':
                if token == '=':
                    value = None  # expecting a value
                elif token == '/':
                    tag.append(attr, None)
                    tag.empty = True
                elif token == '>':
                    tag.append(attr, None)
                    break
                else:
                    tag.append(attr, None)  # got an empty value
                    attr = token  # immediately followed by another
            elif value is None:
                if (len(token) > 1 and token[0] in '\'"' and
                        token[0] == token[-1]):
                    token = token[1:-1]
                if '&quot;' in token:
                    token = token.replace('&quot;', '"')
                tag.append(attr, token)
                attr = None  # expecting an attribute
                value = None
        return tag
