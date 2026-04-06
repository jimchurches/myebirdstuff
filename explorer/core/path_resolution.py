"""
Path resolution for Personal eBird Explorer.

Helper: find_data_file(filename, candidate_dirs)
- Given a filename and a list of candidate directories, returns the first path
  where the file exists, plus that directory (for use as DATA_FOLDER).
- Reusable and easy to unit test with temp dirs.
"""

import os


def find_data_file(filename, candidate_dirs):
    """
    Return the first path where filename exists under a candidate directory.

    Args:
        filename: Name of the file (e.g. "MyEBirdData.csv").
        candidate_dirs: List of directory paths to search in order.

    Returns:
        (file_path, data_folder) if the file exists in one of the directories:
        - file_path: full path to the file (os.path.join(dir, filename))
        - data_folder: the directory that contained it (for use as DATA_FOLDER).
        (None, None) if the file was not found in any candidate directory.
    """
    for folder in candidate_dirs:
        path = os.path.join(folder, filename)
        if os.path.exists(path):
            return (os.path.normpath(path), os.path.normpath(folder))
    return (None, None)
