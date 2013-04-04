import os


def norm_path(*args):
    """
    Returns normalized for current os, absolute path, joined by arguments.
    :param args: path components
    :return: joined, normalized, absolute path.
    """
    return os.path.abspath(os.path.normpath(os.path.join(*args)))


def file_path(file_name, path):
    for p in path:
        file_path = norm_path(p, file_name)
        if os.path.isfile(file_path):
            if file_path.startswith(p):
                return file_path
    raise OSError('File not found: {}, {}'.format(file_name, path))


def get_file_list(path, prefix='.'):
    l = []
    for root, sub, files in os.walk(prefix, path):
        for f in files:
            l.append(os.path.relpath(os.path.join(root, f), prefix))
    return l
