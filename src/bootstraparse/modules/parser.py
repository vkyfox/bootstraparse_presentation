# Main parser, gets config files and parses them for the context manager.
# parse_line takes a io and outputs it all as a list of parsed elements
# Usage:
#   from bootstraparse.modules.parser import parse_line
#   parse_line(io) -> [element, element, element]

from io import StringIO

import bootstraparse.modules.syntax as syntax


def parse_line(io):
    """
    Takes an io string and returns the parsed output.
    :param io: The io string to parse.
    :type io: StringIO
    :return: The parsed output.
    :rtype: list[syntax.SemanticType]
    """
    output = []
    for line in io.readlines():
        output += syntax.line.parseString(line).asList() + [syntax.Linebreak('')]

    return output


if __name__ == "__main__":  # pragma: no cover
    hello = StringIO(
        """
        *hellooooooooooooooooooooooooooooooooooooooooooooooooo*
        my name is **bernard**
        # hello #
        """
    )
    print(parse_line(hello))
