# Module for pre-parsing user files in preparation for the parser
# Usage:
#   from bootstraparse.modules.preparser import preparser
#   pp = preparser(file, enviroment)
#   pp.do_import() # imports all the modules and adds them to the file, do the same for all the files that are to be imported  # noqa
#   pp.do_replacements() # replaces all images and shortcuts in the file
#   pp.readlines() # returns the lines of ORIGINAL file
#   pp.get_all_lines() # returns the lines of the file after replacements and imports


import os
from io import StringIO

from bootstraparse.modules import pathresolver as pr
from bootstraparse.modules import environment
from bootstraparse.modules import syntax
from bootstraparse.modules import error_mngr
from bootstraparse.modules import export

import rich
from rich.tree import Tree

# list of regexps
_rgx_import_file = syntax.rgx_import_file


class PreParser:
    """
    Takes a path and environment, executes all pre-parsing methods on the specified file.
    """
    def __init__(self, file_path, _env, list_of_paths=None, dict_of_imports=None):
        """
        Initializes the PreParser object.
        Takes the following parameters:
        :param file_path: the path of the file to be parsed
        :param _env: the environment object
        :param list_of_paths: the list of files that have been imported in this branch of the import tree
        :param dict_of_imports: Dictionary of all imports made to avoid duplicate file opening / pre-parsing
        :type file_path: str
        :type _env: environment.Environment
        :type list_of_paths: list[str]
        :type dict_of_imports: dict[str, PreParser]
        """
        if list_of_paths is None:
            list_of_paths = []
        if dict_of_imports is None:
            dict_of_imports = {}

        # Set the environment & path
        self._env = _env
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
        """
        self.file_with_all_imports = StringIO()
        self.file_with_all_replacements = StringIO()
        self.imports_done = False
        self.replacements_done = False

    def new_temporary_files(self):
        """
        Make new temporary files, if the old one are not referenced,
        the garbage collector will delete them.
        """
        self.make_temporary_files()

    def do_imports(self):
        """
        Execute all actions needed to do the imports and setup for the next step
        :return: The file descriptor of the file with all imports
        :rtype: StringIO
        """
        self.parse_import_list()
        self.make_import_list()
        self.export_with_imports()
        self.current_origin_for_read = self.file_with_all_imports
        return self.current_origin_for_read

    def do_replacements(self):
        """
        Execute all actions needed to do the replacements.
        :return: The file descriptor of the file with all replacements
        :rtype: StringIO
        """
        self.do_imports()
        self.parse_shortcuts_and_images()
        self.current_origin_for_read = self.file_with_all_replacements
        return self.current_origin_for_read

    def readlines(self):
        """
        Reads the original file and returns a list of lines.
        :return: a list of lines
        :rtype: list[str]
        """
        with open(self.relative_path_resolver(self.name), 'r') as f:
            return f.readlines()

    def get_all_lines(self):
        """
        Get the lines from the file on the step you are in
        :return: A list of lines
        :rtype: list[str]
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
        :rtype: dict[str, PreParser]
        """
        import_list = self.parse_import_list()
        if self.is_global_dict_of_imports_initialized:
            return self.local_dict_of_imports

        for e, l in import_list:
            if e in self.list_of_paths:
                error_mngr.log_exception(
                    RecursionError(f"Error: {e} was imported earlier in {self.list_of_paths}"), level='CRITICAL'
                )
            if e in self.global_dict_of_imports:
                self.local_dict_of_imports[e] = self.global_dict_of_imports[e]
            else:
                try:
                    pp = PreParser(e, self._env, self.list_of_paths.copy(), self.global_dict_of_imports)
                    self.global_dict_of_imports[e] = pp
                    pp.make_import_list()
                    self.local_dict_of_imports[e] = pp
                except FileNotFoundError:
                    error_mngr.log_exception(
                        ImportError("The import {} in file {} line {} doesn't exist".format(e, self.name, l))
                    )
        self.is_global_dict_of_imports_initialized = True
        return self.local_dict_of_imports

    def parse_import_list(self):
        """
        Parses the import list of the file.
        :return: a list of files to be imported, and the line number of the import statement
        :rtype: list[(str, int)]
        """
        if self.saved_import_list:
            return self.saved_import_list
        import_list = []
        line_count = 0

        for line in self.readlines():
            results = _rgx_import_file.searchString(line)
            if results:
                for e in results[0]:
                    import_list += [(e.rstrip(), line_count)]
            line_count += 1
        # converts relative paths to absolute and returns a table
        self.saved_import_list = [(self.relative_path_resolver(p), l) for p, l in import_list]
        return self.saved_import_list

    def export_with_imports(self):
        """
        Return the file object with all file imports done
        :return: a filelike object with all file imports done
        :rtype: StringIO
        """
        self.make_import_list()

        # If the imports are already done, reset the cursor position and return the file
        # We could also decide to duplicate the file instead of resetting the cursor
        if self.imports_done:
            self.file_with_all_imports.seek(0)
            error_mngr.log_message(
                level='INFO',
                message=f'Imports were already done on {self.path}, returning as is;'
                        f' rewound to the beginning of the file.'
            )
            return self.file_with_all_imports

        temp_file = self.file_with_all_imports
        source_line_count = 0
        import_list = self.parse_import_list()
        source_lines = self.readlines()
        for import_path, import_line in import_list:
            source_lines[import_line] = ""  # remove the line where the import was
            temp_file.writelines(source_lines[source_line_count:import_line])  # copy origin to destination
            source_line_count = import_line  # update origin for next import
            import_file = self.global_dict_of_imports[import_path].export_with_imports()
            temp_file.writelines(import_file.readlines())
        temp_file.writelines(source_lines[source_line_count:])
        temp_file.seek(0)
        self.current_origin_for_read = temp_file
        self.imports_done = True
        return self.current_origin_for_read

    def parse_shortcuts_and_images(self):
        """
        Parses through the output files from export_with_imports
        and replaces shortcuts and images calls with appropriate html
        :return: The file descriptor of the file with all replacements
        :rtype: StringIO
        """
        temp_file = self.file_with_all_imports
        temp_text = ''
        for line in temp_file.readlines():
            line_match = syntax.line_to_replace.parse_string(line)
            for match in line_match:
                if match.label == 'text':
                    temp_text = match.content.text
                elif match.label == 'image':
                    temp_text = self.get_image_from_config(match.content.image_name, match.content.optional)
                elif match.label == 'alias':
                    temp_text = self.get_alias_from_config(match.content.alias_name, match.content.optional)
                self.file_with_all_replacements.write(temp_text)
            self.file_with_all_replacements.write("\n")
        self.file_with_all_replacements.seek(0)
        self.replacements_done = True
        return self.file_with_all_replacements

    def get_element_from_config(self, *list_keys):
        """
        Fetches an element from the config (a nested dictionary) going through the list of keys
        Raises an error if the element is not found
        :param list_keys: the list of keys to go through the config
        :type list_keys: str
        """
        sub_dict = self._env.config.loaded_conf
        validated_elements = []
        for key in list_keys:
            try:
                sub_dict = sub_dict[key]
                validated_elements.append(f'[{key}]')
            except KeyError:
                error_mngr.log_exception(
                    KeyError(f"Could not find key {key} in dict config{''.join(validated_elements)} "
                             f"in configs {'; '.join(self._env.config.config_folders)}"),
                    level='CRITICAL'
                )
        return sub_dict

    @staticmethod
    def make_replacements(message, *var_list, **var_dict):
        """
        Tries to format the message or give an error message and return the original message
        :param message: the message to format
        :type message: str
        :param var_list: the list of variables to replace in the message
        :type var_list: str
        :keyword var_dict: the dictionary of variables to replace in the message
        :type var_dict: dict[str, str]
        """
        try:
            return message.format(*var_list, **var_dict)
        except (KeyError, IndexError) as e:
            error_mngr.log_message(
                'Could not find appropriate replacement values in options provided'
                f'"{message}" : {var_list}, {var_dict}'
                f"{str(e)}", level='WARNING'
            )
            return message

    def get_alias_from_config(self, shortcut, optionals):
        """
        Returns the alias from the config and makes the replacements with the options provided
        :param shortcut: id of the shortcut to fetch
        :type shortcut: str
        :param optionals: optional parameters along with alias
        :type optionals: syntax.Optional
        :return: the html to insert as a string
        :rtype: str
        """
        output = self.get_element_from_config('aliases', 'shortcuts', shortcut)
        _, _, var_list, var_dict = syntax.split_optionals(optionals)

        return self.make_replacements(output, *var_list, **var_dict)

    def get_image_from_config(self, shortcut, optionals):
        """
        Returns the image from the config and makes the replacements with the options provided
        :param shortcut: id of the image to fetch
        :type shortcut: str
        :param optionals: optional parameters along with image
        :type optionals: syntax.Optional
        :return: the html to insert as a string
        """
        shortcut_s = self.get_element_from_config('aliases', 'images', shortcut)

        _, _, var_list, var_dict = syntax.split_optionals(optionals)
        request = export.ExportRequest('inline_elements', 'image', optionals)  # noqa : F841
        output = self._env.export_mngr(request)

        return output.start + self.make_replacements(shortcut_s, *var_list, **var_dict) + output.end

    def __repr__(self):
        """
        Returns a string representation of the PreParser object.
        """
        return "PreParser[{}](path={}, name={}, base_path={}, " \
               "relative_path_resolver={}, list_of_paths={}, " \
               "global_dict_of_imports={}, local_dict_of_imports={}" \
               ")".format(id(self), self.path, self.name, self.base_path,
                          id(self.relative_path_resolver), [os.path.basename(elt) for elt in self.list_of_paths],
                          self.global_dict_of_imports, self.local_dict_of_imports)

    def __str__(self):
        """
        Returns a string representation of the PreParser object.
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
        :type other: PreParser
        :return: True if the PreParser objects are not equal, False otherwise
        """
        return not self.__eq__(other)

    def rich_tree(self, prefix="", suffix="", force=True, strip_prefix=""):
        """
        Returns a rich representation of the PreParser object.
        :param prefix: the prefix to add to the representation
        :type prefix: str
        :param suffix: the suffix to add to the representation
        :type suffix: str
        :param force: if True, the representation is always computed, even if it has already been done
        :type force: bool
        :param strip_prefix: the prefix to remove from the path
        :type strip_prefix: str
        :return: a rich representation of the PreParser object
        """
        unparsed = False
        if self.tree_view and not force:
            return self.tree_view
        if strip_prefix == "":
            strip_prefix = self.base_path
        stripped_name = self.path.replace(strip_prefix, "")
        self.tree_view = Tree(prefix+stripped_name+suffix)
        for p, l in self.parse_import_list():
            try:
                self.tree_view.add(self.global_dict_of_imports[p].rich_tree(suffix=" (Line:{})".format(l), force=True, strip_prefix=strip_prefix))  # noqa
            except KeyError:  # The key isn't in the global dict yet
                self.tree_view.add(Tree(prefix+p+suffix+" !!"))
                unparsed = True
        if unparsed:
            self.tree_view.add(Tree("Some element are unparsed and are marked with !!"))
            self.tree_view.add(Tree("You can force the parsing of the file by calling the method "))
            self.tree_view.add(Tree("PreParser.make_import_list() or .do_import()"))
        return self.tree_view


# This part is only used for testing
if __name__ == "__main__":  # pragma: no cover
    from bootstraparse.modules import config
    from bootstraparse.modules import pathresolver
    __config = config.ConfigLoader(pathresolver.b_path("configs/"))
    __templates = config.ConfigLoader(pathresolver.b_path("templates/"))
    site_path = pathresolver.b_path("../../example_userfiles/test.bpr")
    config_path = pathresolver.b_path("../../example_userfiles/config/")
    _env = environment.Environment()
    _env.config = config.ConfigLoader(config_path)
    _env.export_mngr = export.ExportManager(__config, __templates)
    t_pp = PreParser(site_path, _env)
    out = t_pp.do_replacements()
    rich.print(t_pp.get_all_lines())
