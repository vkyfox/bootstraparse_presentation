# Module for pre-parsing user files in preparation for the parser
import logging
import os
import regex
from io import StringIO

from bootstraparse.modules import pathresolver as pr
from bootstraparse.modules import environment
from bootstraparse.modules import syntax
from bootstraparse.modules import error_mngr as em

import rich
from rich.tree import Tree

# list of regexps
_rgx_import_file = regex.compile(r'::( ?\< ?(?P<file_name>[\w\-._/]+) ?\>[ \s]*)+')

# _rgx_shortcut_alias = r'@\[(?P<alias_name>[\w\-._/]+)\]'
# _rgx_shortcut_image = r'@{(?P<image_name>[\w\-._/]+)}'
# _rgx_shortcut_class = r'({(?P<class>[^}]+)})?'
# _rgx_shortcut_variable = r'(\[(?P<variables>[^\]]+)\])?'
# _rgx_alias = regex.compile(f'({_rgx_shortcut_alias}{_rgx_shortcut_class}{_rgx_shortcut_variable} ?)+')
# _rgx_image = regex.compile(f'({_rgx_shortcut_image}{_rgx_shortcut_class}{_rgx_shortcut_variable} ?)+')


class PreParser:
    """
    Takes a path and environment, executes all pre-parsing methods on the specified file.
    """
    def __init__(self, file_path, __env, list_of_paths=None, dict_of_imports=None):
        """
        Initializes the PreParser object.
        Takes the following parameters:
        :param file_path: the path of the file to be parsed
        :param __env: the environment object
        :param list_of_paths: the list of files that have been imported in this branch of the import tree
        :param dict_of_imports: Dictionary of all imports made to avoid duplicate file opening / pre-parsing
        """
        if list_of_paths is None:
            list_of_paths = []
        if dict_of_imports is None:
            dict_of_imports = {}

        # Set the environment & path
        self.__env = __env
        self.path = file_path
        self.name = os.path.basename(file_path)
        self.base_path = os.path.dirname(file_path)
        self.relative_path_resolver = pr.PathResolver(file_path)

        # Set the variables for imports
        self.list_of_paths = list_of_paths + [self.relative_path_resolver(self.name)]
        self.global_dict_of_imports = dict_of_imports
        self.local_dict_of_imports = {}  # Dictionary of all local imports made to avoid duplicate file opening ?
        self.saved_import_list = None

        # The tree view of the import tree (if saved)
        self.tree_view = None

        # Temporary files, or streams
        self.file_with_all_imports = None
        self.file_with_all_replacements = None
        self.make_temporary_files()

        # File you are supposed to read from
        self.current_origin_for_read = None

        # State of operations
        self.is_global_dict_of_imports_initialized = False
        self.imports_done = False
        self.replacements_done = False

    def make_temporary_files(self):
        """
        Creates temporary files for the import list and the replacement.
        :return: None
        """
        self.file_with_all_imports = StringIO()
        self.file_with_all_replacements = StringIO()
        self.imports_done = False
        self.replacements_done = False

    def new_temporary_files(self):
        """
        Make new temporary files, if the old one are not referenced,
        the garbage collector will delete them.
        :return: None
        """
        self.make_temporary_files()

    def do_imports(self):
        """
        Execute all actions needed to do the imports and setup for the next step
        """
        # TODO: Implement this
        # Do all imports
        # parse_import_list()
        # make_import_list()
        # export_with_imports()
        # self.current_origin_for_read = self.file_with_all_imports
        # return self.current_origin_for_read
        pass

    def do_replacements(self):
        """
        Execute all actions needed to do the replacements.
        """
        # TODO: Implement this
        # Do all replacements
        #
        # self.current_origin_for_read = self.file_with_all_replacements
        # return self.current_origin_for_read
        pass

    def readlines(self):
        """
        Reads the original file and returns a list of lines.
        :return: A list of lines
        """
        with open(self.relative_path_resolver(self.name), 'r') as f:
            return f.readlines()

    def get_all_lines(self):
        """
        Get the lines from the file on the step you are in
        :return: A list of lines
        """
        if self.current_origin_for_read is None:
            return self.readlines()
        else:
            return self.current_origin_for_read.readlines()

    def make_import_list(self):
        """
        Creates a list of all files to be imported.
        Makes sure that the files are not already imported through a previous import statement.
        Recursively build a list of PreParser object for each file to be imported.
        :return: the dictionary of all files to be imported (key: file name, value: PreParser object)
        """
        import_list = self.parse_import_list()
        if self.is_global_dict_of_imports_initialized:
            return self.local_dict_of_imports

        for e, l in import_list:
            if e in self.list_of_paths:
                raise RecursionError("Error: {} was imported earlier in {}".format(e, self.list_of_paths))
            if e in self.global_dict_of_imports:
                pp = self.global_dict_of_imports[e]
            else:
                try:
                    pp = PreParser(e, self.__env, self.list_of_paths.copy(), self.global_dict_of_imports)
                    self.global_dict_of_imports[e] = pp
                    pp.make_import_list()
                except FileNotFoundError:
                    logging.error("The import {} in file {} line {} doesn't exist".format(e, self.name, l))
                    # TODO: raise a custom exception or define a default behaviour
                    raise ImportError("The import {} in file {} line {} doesn't exist".format(e, self.name, l))
            self.local_dict_of_imports[e] = pp
        self.is_global_dict_of_imports_initialized = True
        return self.local_dict_of_imports

    def parse_import_list(self):
        """
        Parses the import list of the file.
        :return: a list of files to be imported
        """
        if self.saved_import_list:
            return self.saved_import_list
        import_list = []
        line_count = 0

        for line in self.readlines():
            results = regex.match(_rgx_import_file, line)
            if results:
                for e in results.captures('file_name'):
                    import_list += [(e, line_count)]
            line_count += 1
        # converts relative paths to absolute and returns a table
        self.saved_import_list = [(self.relative_path_resolver(p), l) for p, l in import_list]
        return self.saved_import_list

    def export_with_imports(self):
        """
        Return the file object with all file imports done
        :return: a filelike object with all file imports done
        """

        self.make_import_list()

        # If the imports are already done, reset the cursor position and return the file
        # We could also decide to duplicate the file instead of resetting the cursor
        if self.imports_done:
            self.file_with_all_imports.seek(0)
            return self.file_with_all_imports

        temp_file = self.file_with_all_imports
        source_line_count = 0
        import_list = self.parse_import_list()
        source_lines = self.readlines()
        for import_path, import_line in import_list:
            source_lines[import_line] = ""
            temp_file.writelines(source_lines[source_line_count:import_line])
            source_line_count = import_line
            import_file = self.global_dict_of_imports[import_path].export_with_imports()
            temp_file.writelines(import_file.readlines())
        temp_file.writelines(source_lines[source_line_count:])
        temp_file.seek(0)
        self.imports_done = True
        return temp_file

    def parse_shortcuts_and_images(self):
        """
        Parses through the output files from export_with_imports
        and replaces shortcuts and images calls with appropriate html
        :return: a table of occurrences and their lines
        """
        line_count = 0
        temp_file = self.file_with_all_replacements
        for line in self.readlines():
            results = syntax.alias.parse_string(line)
            if results:
                temp_file.writelines(self.get_alias_from_config(results.alias_name))
            else:
                results = syntax.inage.parse_string(line)
                if results:
                    temp_file.writelines(self.get_picture_from_config(results.image_name))
                else:
                    temp_file.writelines(line)
            line_count += 1
        self.replacements_done = True
        return temp_file

    def get_alias_from_config(self, shortcut):
        """
        Fetches shortcut paths from aliases.yaml
        :return: the html to insert as a string
        :param shortcut: the id of the shortcut to fetch
        """
        # return self.__env.config["aliases"][shortcut]
        return f'<h1>{shortcut}</h1>'

    def get_picture_from_config(self, shortcut):
        """
        Fetches picture paths from aliases.yaml
        :return: the html to insert as a string
        :param shortcut: the id of the picture to fetch
        """
        # return self.__env.config["images"][shortcut]
        return f'<img src="{shortcut}"/>'

    def __repr__(self):
        """
        Returns a string representation of the PreParser object.
        :return: a string representation of the PreParser object
        """
        return "PreParser(path={}, name={}, base_path={}, " \
               "relative_path_resolver={}, ist_of_paths={}, " \
               "global_dict_of_imports={}, local_dict_of_imports={}" \
               ")".format(self.path, self.name, self.base_path,
                          self.relative_path_resolver, self.list_of_paths,
                          self.global_dict_of_imports, self.local_dict_of_imports)

    def __str__(self):
        """
        Returns a string representation of the PreParser object.
        :return: a string representation of the PreParser object
        """
        return self.__repr__()

    def __eq__(self, other):
        """
        Checks if the PreParser object is equal to another PreParser object.
        :return: True if the PreParser objects are equal, False otherwise
        :param other: the other PreParser object
        """
        if self.path == other.path:
            if self.name == other.name:
                if self.base_path == other.base_path:
                    for elt in self.parse_import_list():
                        if elt not in other.parse_import_list():
                            return False
                    return True
        return False

    def __ne__(self, other):
        """
        Checks if the PreParser object is not equal to another PreParser object.
        :param other: the other PreParser object
        :return: True if the PreParser objects are not equal, False otherwise
        """
        return not self.__eq__(other)

    def rich_tree(self, prefix="", suffix="", force=True):
        """
        Returns a rich representation of the PreParser object.
        :return: a rich representation of the PreParser object
        """
        if self.tree_view and not force:
            return self.tree_view
        self.tree_view = Tree(prefix+self.name+suffix)
        for p, l in self.parse_import_list():
            self.tree_view.add(self.global_dict_of_imports[p].rich_tree(suffix=" (Line:{})".format(l), force=True))
        return self.tree_view


# This part is only used for testing
if __name__ == "__main__":  # pragma: no cover
    from bootstraparse.modules import config
    site_path = "../../../example_userfiles/index.bpr"
    config_path = "../../../example_userfiles/config/"
    __env = environment.Environment()
    __env.config = config.ConfigLoader(config_path)
    t_pp = PreParser(site_path, __env)
    t_pp.parse_import_list()

    t_pp.make_import_list()
    out = t_pp.export_with_imports()
    # path = '../../../example_userfiles/output/show_me_what_you_got.txt'
    # os.makedirs(os.path.dirname(path), exist_ok=True)
    # with open(path, 'w+') as file:
    #     file.writelines(pp.export_with_imports().readlines())
    #

    # rich.print(michel.rich_tree())
    string_to_match = r'@[bite]{id=2}[saucisse=13] @[chaussette] @[bermuda]{tomate=tomate}[12] @[pasteque]'
    rich.print(out.readlines())
