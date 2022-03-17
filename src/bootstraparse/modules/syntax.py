# Dedicated module for the syntax of all the parsing
import os
import pyparsing as pp
import rich

pps = pp.Suppress


# Semantic group types
class SemanticType:
    """
    Allows us to access basic operations and identify each token parsed.
    """
    label = None

    def __init__(self, content):
        self.content = content

    def __str__(self):
        if type(self.content) == str:
            return f'{self.label}[{self.content}]'
        else:
            return f'{self.label}{self.content}'

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        if type(other) == type(self):
            for e1, e2 in zip(self.content, other.content):
                if e1 != e2:
                    return False
            return True
        return False


class UnimplementedToken(SemanticType):
    label = "unimplemented"


class AliasToken(SemanticType):
    label = "alias"


class ImageToken(SemanticType):
    label = "image"


class TextToken(SemanticType):
    label = "text"


class EnhancedToken(SemanticType):
    label = "text:enhanced"


class EtEmToken(SemanticType):
    label = "text:em"


class EtStrongToken(SemanticType):
    label = "text:strong"


class EtUnderlineToken(SemanticType):
    label = "text:underline"


class EtStrikethroughToken(SemanticType):
    label = "text:strikethrough"


class EtCustomSpanToken(SemanticType):
    label = "text:custom_span"


class EtUlistToken(SemanticType):
    label = "list:ulist"


class EtOlistToken(SemanticType):
    label = "list:olist"


class HeaderToken(SemanticType):
    label = "header"


class DisplayToken(SemanticType):
    label = "display"


class StructuralElementStartToken(SemanticType):
    label = "se:start"


class StructuralElementEndToken(SemanticType):
    label = "se:end"


class HyperlinkToken(SemanticType):
    label = "hyperlink"


class TableToken(SemanticType):
    label = "table"


class TableRowToken(SemanticType):
    label = "table:row"


class TableCellToken(SemanticType):
    label = "table:cell"


class TableSeparatorToken(SemanticType):
    label = "table:separator"


class OptionalToken(SemanticType):
    label = "optional"


def of_type(token_class):
    """
    Function creating a custom function for generating the given Token type.
    :param token_class: SemanticType class
    :return: returns a function creating an instance of the given class
    """
    def _of_type(_, __, content):
        return token_class(content)

    return _of_type


def readable_markup(list_of_tokens):
    """
    Function used for testing and readability purposes. Replaces matched markup with html-like tags.
    :param list_of_tokens: list of matched markup tokens in analysed text.
    :return: returns readable string.
    :rtype: string
    """
    readable_string = ''
    for token in list_of_tokens:
        if type(token) == str:
            readable_string += token
        else:
            readable_string += _add_tag(token)
    return readable_string


def _add_tag(token):
    """
    Function used for testing and readability purposes. Replaces matched markup with html-like tags.
    :param token: matched markup token in analysed text.
    :return: returns readable string.
    """
    if token.label == 'text':
        return token.content[0]
    if token.content:
        return "<{} = '{}' />".format(token.label, ",".join(token.content))


# Base elements
quotes = pp.Word(r""""'""")
value = (quotes + pp.Word(pp.alphanums + r'.') + pp.match_previous_literal(quotes) ^
         pp.common.fnumber)("value")
assignation = pp.Group(pp.common.identifier('var_name') + '=' + value('var_value'))("assignation")
text = pp.OneOrMore(pp.Word(pp.alphanums))('text').add_parse_action(of_type(TextToken))
url_characters = pp.common.url

# Composite elements
var = '[' + pp.delimitedList(assignation ^ value)("list_vars").set_name("list_vars") + ']'


# Specific elements
image_element = ('@{' + pp.common.identifier('image_name') + '}')("image_element")
alias_element = ('@[' + pp.common.identifier('alias_name') + ']')("alias_element")
expression = pp.Word(pp.alphanums + r'=+-_\'",;:!<> ')
html_insert = '{' + expression('html_insert') + '}'
structural_elements = (
        pp.CaselessLiteral('div') |
        pp.CaselessLiteral('article') |
        pp.CaselessLiteral('aside') |
        pp.CaselessLiteral('section')
)('structural_element')
header_element = pp.Word('#')
display_element = pp.Word('!')


# Optional elements
optional = (
        pp.Opt(html_insert)("html_insert") + pp.Opt(var)("var")
)("optional").add_parse_action(of_type(OptionalToken))

# Inline elements
il_link = pp.Regex(
    r"""\[(?P<text>.+)\]\(['"](?P<url>[a-zA-Z-_:\/=@#!%\?\d\(\)\.]+)['"]\)"""
).add_parse_action(of_type(HyperlinkToken))

# Enhanced text elements
et_em = pp.Literal('*')('em').add_parse_action(of_type(EtEmToken))
et_strong = pp.Literal('**')('strong').add_parse_action(of_type(EtStrongToken))
et_underline = pp.Literal('__')('underline').add_parse_action(of_type(EtUnderlineToken))
et_strikethrough = pp.Literal('~~')('strikethrough').add_parse_action(of_type(EtStrikethroughToken))
et_custom_span = (
        pps('(#') + pp.Word(pp.nums)('span_id') + pps(')')
).set_name('custom_span').add_parse_action(of_type(EtCustomSpanToken))

# markup sums up all in-line elements
markup = il_link | et_strong | et_em | et_strikethrough | et_underline | et_custom_span

# Multiline elements
se_start = (pps('<<') + structural_elements).add_parse_action(of_type(StructuralElementStartToken))
se_end = (structural_elements + pps('>>')).add_parse_action(of_type(StructuralElementEndToken))
se = se_end | se_start  # Structural element

# Oneline elements
one_header = (
        header_element + pp.SkipTo(pp.match_previous_literal(header_element))
).add_parse_action(of_type(HeaderToken))
one_display = (
        display_element + pp.SkipTo(pp.match_previous_literal(display_element))
).add_parse_action(of_type(DisplayToken))
one_olist = pp.line_start + (
        pp.Literal('#') + pps('.') + pp.SkipTo(pp.line_end)('olist_text')
).add_parse_action(of_type(EtOlistToken))
one_ulist = pp.line_start + (
        pp.Literal('-') + pp.SkipTo(pp.line_end)('ulist_text')
).add_parse_action(of_type(EtUlistToken))

# Final elements
enhanced_text = pp.ZeroOrMore(
    markup | pp.SkipTo(markup)('text').add_parse_action(of_type(TextToken)) + markup
) + pp.Opt(pp.rest_of_line("text").add_parse_action(of_type(TextToken)))


##############################################################################
# Pre_parser elements
##############################################################################

# Composite elements
image = image_element + optional
alias = alias_element + optional

# Syntax elements
line_to_replace = pp.OneOrMore(
    pp.SkipTo(image ^ alias)('text').add_parse_action(of_type(TextToken))
    ^ image.add_parse_action(of_type(ImageToken))
    ^ alias.add_parse_action(of_type(AliasToken))
) ^ pp.rest_of_line('text').add_parse_action(of_type(TextToken))

##############################################################################
# Temporary tests
##############################################################################
if __name__ == '__main__':  # pragma: no cover
    pp.autoname_elements()

    if not os.path.exists('../../../dev_outputs/'):
        os.mkdir('../../../dev_outputs/')
    enhanced_text.create_diagram("../../../dev_outputs/diagram.html")