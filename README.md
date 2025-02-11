# bootstraparse
bootstraparse is a personal project started with a specific goal in mind: creating static html pages for direct display from a markdown-like file.
bootstraparse aims to be customisable in that regard, but its first iteration and main focus will be to create a bootstrap-powered html.


You can refer to the `example_userfiles` for an idea of what the parser expects you to feed it and find an example of our automated generation at https://idle-org.github.io/bootstraparse/ for this particular folder. Or you can run the program yourself for the same result!

- Main
  - [![Python Tests and Lint](https://github.com/idle-org/bootstraparse/actions/workflows/python-tests.yml/badge.svg?branch=main)](https://github.com/idle-org/bootstraparse/actions/workflows/python-tests.yml)
- Releases
  - [![Python Tests and Lint](https://github.com/idle-org/bootstraparse/actions/workflows/python-tests.yml/badge.svg?branch=develop)](https://github.com/idle-org/bootstraparse/actions/workflows/python-tests.yml)
- Deploy
  - [![Python Deployment](https://github.com/idle-org/bootstraparse/actions/workflows/python-deploy.yml/badge.svg?branch=main)](https://github.com/idle-org/bootstraparse/actions/workflows/python-deploy.yml)
---
## Release Notes
### V1.0.1
- Remove old regex usage
- Add copy behaviour to config file
- Add the type and return types of all functions
- Add documentation to remaining lone functions
- Copy un-parsable files to destination folder without modifications
- Many bug fixes and improvements

### V1.0.2
- Put out many fires

### V1.0.3
- Put out many more fires
- Fixed continuous integration
- Added doc generation

## Roadmap
### V1.0.4
- Make the default example site way more useful ☐
- Write a documentation for the application (use specs.yaml) ☐
- Move the WARNING-level output to INFO for config overwrite ☐

### V1.1
- Functioning `table` Token ☐
- Functioning `code` Token ☐
- Establish a list of all configurable parameters to implement in the future, and update the roadmap with them. ☐
- Decide level of logic to be implemented, and whether it should be configurable ☐
- Update the uses of remaining files ☐


### V1.2
- Check error messages and add a real debug level to parameters ☐
- Functioning `blockquote` Token ☐

### V1.3
- Add advanced lookahead logic for `*`
- Functioning `lead` Token

### V1.4
- Add html indentation for human readability of the output. ☐

### V2
- Add a functioning post-context enhancer able to generate menus and elements from arbitrary logic.
- Achieve perfect markdown compatibility with appropriate config parameters

### V3
- Add Template customisation.
