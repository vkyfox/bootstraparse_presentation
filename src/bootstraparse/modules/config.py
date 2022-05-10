# Interprets config files
import os
import yaml
from bootstraparse import error_mngr


class ConfigLoader:
    """
    Reads all config files in a folder
    Behaves like a dictionary of all config files
    return FileNotFound Error on Error
    :param config_folder: The folder to read
    """

    def __init__(self, config_folder=None, extensions=("yaml", "yml")):
        """
        Defines the config folder and loads all configs
        :param config_folder: path to config file
        :param extensions: file extensions to load
        :return: None
        """
        if config_folder is None:
            self.config_folders = []
        elif isinstance(config_folder, str):
            self.config_folders = [config_folder]
        elif isinstance(config_folder, (list, tuple)):
            self.config_folders = config_folder
        else:
            error_mngr.log_exception(TypeError(f"Incorrect config type given. Expected a string, list or tuple; "
                                               f"got {type(config_folder).__name__} instead."), level='CRITICAL')
        self.loaded_conf = {}
        self.extensions = extensions
        self.reload_all()

    def reload_all(self):
        """
        Reloads all configs
        :return: None
        """
        self.loaded_conf = {}
        for folder in self.config_folders:
            self.load_from_folder(folder)

    def add_folder(self, folder):
        """
        Add a Folder to the list of configs
        :param folder: path to folder
        :return: None
        """
        self.config_folders.append(folder)
        self.load_from_folder(folder)

    def load_from_file(self, filepath):
        """
        Loads a config file
        :param filepath: path to config file
        :return: None
        """
        basename = os.path.basename(filepath)
        name, ext = os.path.splitext(basename)
        with open(filepath, "r") as f:
            try:
                if name not in self.loaded_conf:
                    self.loaded_conf[name] = yaml.safe_load(f)
                else:
                    self.loaded_conf[name].update(yaml.safe_load(f))
                    error_mngr.log_message(f"Warning: {name} is already in {self.loaded_conf}", level='WARNING')
            except yaml.parser.ParserError as e:
                error_mngr.log_message(f'Error parsing in file {basename} at {filepath}.', level='CRITICAL')
                error_mngr.log_exception(yaml.parser.ParserError(e), level='CRITICAL')

    def load_from_folder(self, folder):
        """
        Loads all configs in the config folder
        :return: None
        """
        for filename in os.listdir(folder):
            file_ext = os.path.splitext(filename)[1][1:]
            if file_ext in self.extensions:
                self.load_from_file(os.path.join(folder, filename))

    def __getitem__(self, item):
        """
        Returns a yaml config object if in self.loaded_conf
        :param item: config key
        :return: config value
        """
        try:
            return self.loaded_conf[item]
        except KeyError:
            error_mngr.log_exception(KeyError(f"Error: {item} is not in {self.loaded_conf}"), level='CRITICAL')

    def __repr__(self):
        """
        Returns config as string
        :return: config as string
        """
        return self.loaded_conf.__repr__()


# class UserConfig(ConfigLoader):
#     """
#     Reads user config file.
#     :param config_folder: path to config file
#     :return: None
#     """
#     def __init__(self, config_folder):
#         super().__init__(config_folder)
#
#
# class GlobalConfig(ConfigLoader):
#     """
#     Reads global config file.
#     :param config_folder: path to config file
#     :return: None
#     """
#     def __init__(self, config_folder):
#         super().__init__(config_folder)


# conf = ConfigLoader("./example_userfiles/config/aliases.yaml")
