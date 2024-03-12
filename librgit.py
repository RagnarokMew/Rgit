"""
Dependencies
os -> filesystem
sys -> access command-line arguments
argparse -> Rgit a CLI app, thus argparse is required to parse command line
            arguments
collections -> for the extra containers
configparser -> for reading and writing config files
datetime -> for dates/time
fnmatch -> for matching filenames
grp -> Unix groups
pwd -> Unix users, for displaying author
hashlib -> for hashing
zlib -> compression
re -> regular expressions
math -> math functions
"""

from datetime import datetime
from fnmatch import fnmatch
import os, sys, argparse, collections, configparser, grp, pwd, hashlib, zlib, re
from math import ceil


"""RGIT INTERNALS"""
class RgitRepository(object):
    '''git repo'''
    worktree = None
    gitdir = None
    conf = None

    def __init__(self, path, force=False):
        self.worktree = path
        self.gitdir = os.path.join(path, ".git")

        if not (force or os.path.isdir(self.gitdir)):
            raise Exception("Not a Rgit repository %s" % path)

        #Read config file in .git/config
        self.conf = configparser.ConfigParser()
        cf = repo_file(self, "config")

        if cf and os.path.exists(cf):
            self.conf.read([cf])
        elif not force:
            raise Exception("Configuration file missing")

        if not force:
            vers = int(self.conf.get("core", "repositoryformatversion"))
            if vers != 0:
                raise Exception("Unsupported repositoryformatversion %s" % vers)

class GitIgnore(object):
    absolute = None
    scoped = None

    def __init__(self, absolute, scoped):
        self.absolute = absolute
        self.scoped = scoped

class GitIndexEntry(object):
    def __init__(self, ctime=None, mtime=None, dev=None, ino=None,
                mode_type=None, mode_perms=None, uid=None, gid=None,
                fsize=None, sha=None, flag_assume_valid=None, flag_stage=None, name=None):

        #Last time file's metadata was changed: Pair of timestamp (seconds, nanoseconds)
        self.ctime = ctime

        #Last time file's data was changed: Pair of timestamp (seconds, nanoseconds)
        self.mtime = mtime

        #device Id containing file
        self.dev = dev

        #file inode numnber (number associated to file name unique in the file system)
        self.ino = ino 

        #object type b1000 (regular), b1010 (symLink), b1110 (gitLink)
        self.mode_type = mode_type

        #object permissions (int)
        self.mode_perms = mode_perms

        #owner id user
        self.uid = uid

        #owner id group
        self.gid = gid

        #object size in bytes
        self.fsize = fsize

        #object sha
        self.sha = sha
        self.flag_assume_valid = flag_assume_valid
        self.flag_stage = flag_stage

        #object name (full path)
        self.name = name

#begins with DIRC mahic bytes, version number and total number of entries
class GitIndex(object):
    version = None
    entries = []
    #ext = None
    #sha = None

    def __init__(self, version=2, entries=None):
        if not entries:
            entries = list()

        self.version = version
        self.entries = entries

class GitObject(object):

    def __init__(self, data=None):
        if data != None:
            self.deserialize(data)
        else:
            self.init()
    
    def serialize(self, repo):
        raise Exception("Must be called from subclasses for proper implementation")

    def deserialize(self, repo):
        raise Exception("Must be called from subclasses for proper implementation")

    def init(self):
        pass

def object_read(repo, sha):

    path = repo_file(repo, "objects", sha[0:2], sha[2:])

    if not os.path.isfile(path):
        return None

    with open(path, "rb") as f:
        raw = zlib.decompress(f.read())

        #Object type
        x = raw.find(b' ')
        format = raw[0:x]

        #Read and validate object size
        y = raw.find(b'\x00', x)
        size = int(raw[x:y].decode("ascii"))
        if size != len(raw)-y-1:
            raise Exception("Malformed object {0}: bad length".format(sha))

        #Constructor
        match format:
            case b'commit' : obj = GitCommit
            case b'tree' : obj = GitTree
            case b'tag' : obj=GitTag
            case b'blob' : obj=GitBlob
            case _ : raise Exception("Unknown type {0} for object {1}".format(format.decode("ascii"), sha))
        
        return obj(raw[y+1:])

def object_write(obj, repo=None):
    data = obj.serialize()
    result = obj.format + b' ' + str(len(data)).encode() + b'\x00' + data
    sha = hashlib.sha1(result).hexdigest()

    if repo:
        path=repo_file(repo, "objects", sha[0:2], sha[2:], mkdir=True)

        if not os.path.exists(path):
            with open(path, 'wb') as f:
                f.write(zlib.compress(result))
    
    return sha

class GitBlob(GitObject):
    format=b'blob'

    def serialize(self):
        return self.blobdata
    
    def deserialize(self, data):
        self.blobdata = data

class GitCommit(GitObject):
    format = b'commit'

    def deserialize(self, data):
        self.keyvaluelist = keyvaluelist_parse(data)

    def serialize(self):
        return keyvaluelist_serialize(self.keyvaluelist)

    def init(self):
        self.keyvaluelist = dict()


""" TREE FORMAT
 [mode] space [path] 0x00 [sha-1]
 [mode] = up to 6 bytes => file mode in ascii
 space = 0x20 ascii space
 0x00 = null-terminated path
 sha-1 = object's sha-1 in binary encoding on 20 bytes
 """

class GitTreeLeaf(object):
    def __init__(self, mode, path, sha):
        self.mode = mode
        self.path = path
        self.sha = sha

class GitTree(GitObject):
    format = b'tree'
    
    def deserialize(self, data):
        self.items = tree_parse(data)

    def serialize(self):
        return tree_serialize(self)

    def init(self):
        self.items = list()

class GitTag(GitCommit):
    format = b'tag'

#Path in repo's gitdir
def repo_path(repo, *path):
    return os.path.join(repo.gitdir, *path)

#repo_path but creates dirname(*path) if absent
def repo_file(repo, *path, mkdir=False):

    if repo_dir(repo, *path[:-1], mkdir=mkdir):
        return repo_path(repo, *path)

#repo_path but if mkdir path is absent
def repo_dir(repo, *path, mkdir=False):

    path = repo_path(repo, *path)

    if os.path.exists(path):
        if os.path.isdir(path):
            return path
        else:
            raise Exception("Not a directory %s" % path)
    
    if mkdir:
        os.makedirs(path)
        return path
    else:
        return None

#makes new repo at path
def repo_create(path):
    repo = RgitRepository(path, True)

    if os.path.exists(repo.worktree):
        if not os.path.isdir(repo.worktree):
            raise Exception("%s is not a directory!" % path)
        if os.path.exists(repo.gitdir) and os.listdir(repo.gitdir):
            raise Exception("%s is not empty!" % path)
    else:
        os.makedirs(repo.worktree)
    
    assert repo_dir(repo, "branches", mkdir=True)
    assert repo_dir(repo, "objects", mkdir=True)
    assert repo_dir(repo, "refs", "tags", mkdir=True)
    assert repo_dir(repo, "refs", "heads", mkdir=True)

    #.git/description
    with open(repo_file(repo, "description"), "w") as f:
        f.write("Unnamed repository; edit this file to name the repository.\n")

    #.git/HEAD
    with open(repo_file(repo, "HEAD"), "w") as f:
        f.write("ref: refs/heads/master\n")

    with open(repo_file(repo, "config"), "w") as f:
        config = repo_default_config()
        config.write(f)

    return repo

def repo_default_config():
    ret = configparser.ConfigParser()

    ret.add_section("core")
    ret.set("core", "repositoryformatversion", "0")
    ret.set("core", "filemode", "false")
    ret.set("core", "bare", "false")

    return ret

def repo_find_root(path=".", required=True):
    path = os.path.realpath(path)

    if os.path.isdir(os.path.join(path, ".git")):
        return RgitRepository(path)

    parent = os.path.realpath(os.path.join(path, ".."))

    if parent == path:
        if required:
            raise Exception("No git directory.")
        else:
            return None
    
    return repo_find_root(parent, required)

def object_find(repo, name, format=None, follow = True):
    sha = object_resolve(repo, name)

    if not sha:
        raise Exception("No such reference {0}.".format(name))

    if len(sha) > 1:
        raise Exception("Ambiguous reference {0}: Candidates are:\n -{1}".format(name, "\n - ".join(sha)))
    
    sha = sha[0]

    if not format:
        return sha

    while True:
        obj = object_read(repo, sha)

        if obj.format == format:
            return sha

        if not follow:
            return None

        if obj.format == b'tag':
            sha = obj.keyvaluelist[b'object'].decode("ascii")
        elif obj.format == b'commit' and format == b'tree':
            sha = obj.keyvaluelist[b'tree'].decode("ascii")
        else:
            return None

def object_resolve(repo, name):
    candidates = list()
    hashRE = re.compile(r"[0-9A-Fa-f]{4,40}$")

    if not name.strip(): #Abort if empty string
        return None

    if name == "HEAD":
        return [ ref_resolve(repo, "HEAD") ]

    if hashRE.match(name):
        name = name.lower()
        prefix = name[0:2]
        path = repo_dir(repo, "objects", prefix, mkdir=False)
        if path:
            remainder = name[2:]
            for file in os.listdir(path):
                if file.startswith(remainder):
                    candidates.append(prefix + file)

    as_tag = ref_resolve(repo, "refs/tags/" + name)
    if as_tag:
        candidates.append(as_tag)

    as_branch = ref_resolve(repo, "refs/heads/" + name)
    if as_branch:
        candidates.append(as_branch)
    
    return candidates

def cat_file(repo, object, format=None):
    object = object_read(repo, object_find(repo, object, format=format))
    sys.stdout.buffer.write(object.serialize())

def object_hash(file, format, repo=None):
    data = file.read()

    match format:
        case b'commit': obj = GitCommit(data)
        case b'tree': obj = GitTree(data)
        case b'tag' : obj = GitTag(data)
        case b'blob' : obj=GitBlob(data)
        case _ : raise Exception("Unknown type %s!" % format)

    return object_write(obj, repo)

def keyvaluelist_parse(raw, start=0, dct=None):
    
    if not dct:
        dct = collections.OrderedDict()

    space = raw.find(b' ', start)
    newline = raw.find(b'\n', start)

    # Baseline case: Blank line | final message
    # The remainder of the data is the message => stored in dictionary with None key and returned 
    if (space < 0) or (newline < space):
        assert newline == start
        dct[None] =raw[start+1:]
        return dct

    #key
    key = raw[start:space]

    #finding the end of value (continuation lines start with a space)
    end = start
    while True:
        end = raw.find(b'\n', end+1)
        if raw[end+1] != ord(' '): break

    value = raw[space+1:end].replace(b'\n ', b'\n')

    #Not overwriting existing content
    if key in dct:
        if type(dct[key]) == list:
            dct[key].append(value)
        else:
            dct[key] = [ dct[key], value ]
        
    else:
        dct[key] = value

    return keyvaluelist_parse(raw, start=end+1, dct=dct)

def keyvaluelist_serialize(keyvaluelist):
    result = b''

    for key in keyvaluelist.keys():
        if key == None: continue
        value = keyvaluelist[key]

        if type(value) != list:
            value = [ value ]
        
        for v in value:
            result += key + b' ' + (v.replace(b'\n', b'\n ')) + b'\n'

    result += b'\n' + keyvaluelist[None] + b'\n'

    return result

def log_graphics(repo, sha , seen):
    if sha in seen:
        return
    seen.add(sha)

    commit = object_read(repo, sha)
    short_hash = sha[0:8]
    message = commit.keyvaluelist[None].decode("utf8").strip()
    message = message.replace("\\", "\\\\")
    message = message.replace("\"", "\\\"")

    # Print first line only
    if "\n" in message:
        message = message[:message.index("\n")]

    print(" c_{0} [label=\"{1}: {2}\"]".format(sha, sha[0:7], message))
    assert commit.format==b'commit'

    #initial commit check
    if not b'parent' in commit.keyvaluelist.keys():
        return
    
    parents = commit.keyvaluelist[b'parent']

    if type(parents) != list:
        parents = [ parents ]

    for parent in parents:
        parent = parent.decode("ascii")
        print(" c_{0} -> c_{1};".format(sha, parent))
        log_graphics(repo, parent, seen)

def tree_parse_one(raw, start=0):

    x = raw.find(b' ', start)
    assert x-start == 5 or x-start==6

    mode = raw[start:x]
    if len(mode) == 5:
        #Normalized to 6 bytes
        mode = b" " + mode

    y = raw.find(b'\x00', x) #null-terminator location
    path = raw[x+1:y]

    sha = format(int.from_bytes(raw[y+1:y+21], "big"), "040x")
    return y+21, GitTreeLeaf(mode, path.decode("utf8"), sha)

def tree_parse(raw):
    pos = 0
    max = len(raw)
    result = list()
    while pos < max:
            pos, data = tree_parse_one(raw, pos)
            result.append(data)
    
    return result

### Normal git tree sorting behaviour:
# thing (file) => thing.c => thing (directory) (as thing/)
# as can be seen in git source in tree.c

def tree_leaf_sort_key(leaf):
    if leaf.mode.startswith(b"10"):
        return leaf.path
    else:
        return leaf.path + "/"

def tree_serialize(obj):
    obj.items.sort(key=tree_leaf_sort_key)
    result = b''
    for item in obj.items:
        result +=item.mode
        result +=b' '
        result += item.path.encode("utf8")
        result += b'\x00'
        sha = int(item.sha, 16)
        result+= sha.to_bytes(20, byteorder="big")
    return result

def ls_tree(repo, ref, recursive=None, prefix=""):
    sha = object_find(repo, ref, format=b"tree")
    obj = object_read(repo, sha)
    for item in obj.items:
        if len(item.mode) == 5:
            type = item.mode[0:1]
        else:
            type = item.mode[0:2]
        
        match type:
            case b'04': type = "tree"
            case b'10': type = "blob" #normal file
            case b'12': type = "blob" #a symlink. blob content is link target
            case b'16': type = "commit" # a submodule
            case _: raise Exception("Weird tree leaf mode {}".format(item.mode))

        # Leaf
        if not (recursive and type=='tree'): 
            print("{0} {1} {2}\t{3}".format(
                "0" * (6 - len(item.mode)) + item.mode.decode("ascii"),
                type, item.sha, os.path.join(prefix, item.path)))

        #branch
        else:
            ls_tree(repo, item.sha, recursive, os.path.join(prefix, item.path))

def tree_checkout(repo, tree, path):
    for item in tree.items:
        obj = object_read(repo, item.sha)
        dest = os.path.join(path, item.path)

        if obj.format == b"tree":
            os.mkdir(dest)
            tree_checkout(repo, obj, dest)
        elif obj.format == b"blob":
            with open(dest, 'wb') as file:
                file.write(obj.blobdata)

def ref_resolve(repo, ref):
    path = repo_file(repo, ref)

    if not os.path.isfile(path):
        return None

    with open(path, 'r') as filepath:
        data = filepath.read()[:-1]

    if data.startswith("ref: "):
        return ref_resolve(repo, data[5:])
    else:
        return data

def ref_list(repo, path=None):
    if not path:
        path = repo_dir(repo, "refs")

    result = collections.OrderedDict()
    # Git shows reds sorted
    # For the same result rgit uses an OrderedDict and sorts the output

    for f in sorted(os.listdir(path)):
        can = os.path.join(path, f)
        if os.path.isdir(can):
            result[f] = ref_list(repo, can)
        else:
            result[f] = ref_resolve(repo, can)
    
    return result

def show_ref(repo, refs, with_hash=True, prefix=""):
    for key, value in refs.items():
        if type(value) == str:
            print("{0}{1}{2}".format(
                value + " " if with_hash else "",
                prefix + '/' if prefix else "",
                key))
        else:
            show_ref(repo, value, with_hash=with_hash, prefix="{0}{1}{2}".format(prefix, "/" if prefix else "", key))

def tag_create(repo, name, ref, create_tag_object=False):
    sha = object_find(repo_ref)

    if create_tag_object:
        tag = GitTag(repo)
        tag.keyvaluelist = collections.OrderedDict()
        tag.keyvaluelist[b'object'] = sha.encode()
        tag.keyvaluelist[b'type'] = b'commit'
        tag.keyvaluelist[b'tag'] = name.encode()
        tag.keyvaluelist[b'tagger'] = b'<name_placeholder> <email_placeholder>'
        tag.keyvaluelist[None] = b"<tag_msg>"
        tag_sha = object_write(tag)
        ref_create(repo, "tags/" + name, tag_sha)
    else:
        ref_create(repo, "tags/" + name, sha)
    
def ref_create(repo, ref_name, sha):
    with open(repo_file(repo, "refs/" + ref_name), 'w') as filepath:
        filepath.write(sha + "\n")

def index_read(repo):
    index_file = repo_file(repo, "index")

    #Creating Index if it does not exist
    if not os.path.exists(index_file):
        return GitIndex()

    with open(index_file, 'rb') as f:
        raw = f.read()

    header = raw[:12]
    signature = header[:4]
    assert signature == b"DIRC" # == DirCache
    version = int.from_bytes(header[4:8], "big")
    assert version == 2 ### ONLY VERSION 2 IS IMPLEMENTED
    count = int.from_bytes(header[8:12], "big")

    entries = list()

    content = raw[12:]
    idx = 0
    for i in range(0, count):
        ctime_s = int.from_bytes(content[idx: idx+4], "big")
        ctime_ns = int.from_bytes(content[idx+4: idx+8], "big")

        mtime_s = int.from_bytes(content[idx+8: idx+12], "big")
        mtime_ns = int.from_bytes(content[idx+12: idx+16], "big")

        dev = int.from_bytes(content[idx+16: idx+20], "big")

        ino = int.from_bytes(content[idx+20: idx+24], "big")

        #ignore padding
        unused = int.from_bytes(content[idx+24: idx+26], "big")
        assert 0 == unused

        mode = int.from_bytes(content[idx+26: idx+28], "big")
        mode_type = mode >> 12
        assert mode_type in [0b1000, 0b1010, 0b1110]
        mode_perms = mode & 0b0000000111111111

        uid = int.from_bytes(content[idx+28: idx+32], "big")
        gid = int.from_bytes(content[idx+32: idx+36], "big")

        fsize = int.from_bytes(content[idx+36: idx+40], "big")

        #sha stored in lowercase hex string
        sha = format(int.from_bytes(content[idx+40: idx+60], "big"), "040x")

        #flags to be ignored
        flags = int.from_bytes(content[idx+60: idx+62], "big")

        #parsing flags
        flag_assume_valid = (flags & 0b1000000000000000) !=0
        flag_extended = (flags & 0b0100000000000000) != 0

        assert not flag_extended

        flag_stage = flags & 0b0011000000000000

        #length of name stored in 12 bits, max value is 0xFFFm 4095. Names can be larger
        #so  git treats 0xFFF meaning at least 0xFFF and lookks for the final 0x00 to find the end the name
        name_length = flags & 0b0000111111111111

        idx += 62 # 62 bytes have been read

        if name_length < 0xFFF:
            assert content[idx+ name_length] == 0x00
            raw_name = content[idx:idx+name_length]
            idx += name_length + 1
        else:
            print("Notice: Name is 0x{:X} bytes long.".format(name_length))

            # There may be errors when size is larger than 0xFFF
            null_idx = content.find('b\x00', idx + 0xFFF)
            raw_name = content[idx: null_idx]
            idx = null_idx + 1

        name = raw_name.decode("utf8")

        #data is padded by 8*N bytes for pointer alignment;
        #skip the pad
        idx = 8*ceil(idx/8)

        #adding to entry list
        entries.append(GitIndexEntry(ctime=(ctime_s, ctime_ns),
                                    mtime=(mtime_s, mtime_ns),
                                    dev=dev,
                                    ino=ino,
                                    mode_type=mode_type,
                                    mode_perms=mode_perms,
                                    uid=uid,
                                    gid=gid,
                                    fsize=fsize,
                                    sha=sha,
                                    flag_assume_valid = flag_assume_valid,
                                    flag_stage=flag_stage,
                                    name=name))

    return GitIndex(version = version, entries = entries)

def gitignore_parse1(raw):
    raw = raw.strip() #removing leading / trailing spaces

    if not raw or raw[0] == "#": #comments are ignored
        return None
    elif raw[0] == "!": # ! are always included
        return (raw[1:], False)
    elif raw[0] =="\\": #\ treats # and ! as literal chars
        return (raw[1:], True)
    else:
        return (raw, True)

def gitignore_parse(lines):
    result = list()

    for line in lines:
        parsed = gitignore_parse1(line)
        if parsed:
            result.append(parsed)

    return result

def gitignore_read(repo):
    result = GitIgnore(absolute=list(), scoped=dict())

    #Reading local config in .git/info/exclude
    repo_file = os.path.join(repo.gitdir, "info/exclude")
    if os.path.exists(repo_file):
        with open(repo_file, "r") as file:
            result.absolute.append(gitignore_parse(file.readlines()))

    #Global config
    if "XDG_CONFIG_HOME" in os.environ:
        config_home = os.environ["XDG_CONFIG_HOME"]
    else:
        config_home = os.path.expanduser("~/.config")
    global_file = os.path.join(config_home, "git/ignore")

    if os.path.exists(global_file):
        with open(ghlobal_file, "r") as file:
            result.absolute.append(gitignore_parse(file.readlines()))

    #.gitignore files in the index
    index = index_read(repo)

    for entry in index.entries:
        if entry.name == ".gitignore" or entry.name.endswith("/.gitignore"):
            dir_name = os.path.dirname(entry.name)
            contents = object_read(repo, entry.sha)
            lines = contents.blobdata.decode("utf8").splitlines()
            result.scoped[dir_name] = gitignore_parse(lines)
    return result
    
def check_ignore1(rules, path):
    result = None
    for (pattern, value) in rules:
        if fnmatch(path, pattern):
            result = value
    return result

def check_ignore_scoped(rules, path):
    parent = os.path.dirname(path)
    while True:
        if parent in rules:
            result = check_ignore1(rules[parent], path)
            if result != None:
                return result
            if parent == "":
                break
            parent = os.path.dirname(parent)
    return None

def check_ignore_absolute(rules, path):
    parent = os.path.dirname(path)
    for ruleset in rules:
        result = check_ignore1(ruleset, path)
        if result != None:
            return result
    return False

def check_ignore(rules, path):
    if os.path.isab(path):
        raise Exception("This function requires path to be relative to the repository's root")

    result = check_ignore_scoped(rules.scoped, path)
    if result != None:
        return result

    return check_ignore_absolute(rules.absolute, path)

def branch_get_active(repo):
    with open(repo_file(repo, "HEAD"), "r") as file:
        head = file.read()

    if head.startswith("ref: refs/heads/"):
        return(head[16:-1])
    else:
        return False

def tree_to_dict(repo, ref, prefix=""):
    result = dict()
    tree_sha = object_find(repo, ref, format=b"tree")
    tree = object_read(repo, tree_sha)

    for leaf in tree.items:
        full_path = os.path.join(prefix, leaf.path)

        #reading object to get type
        is_subtree = leaf.mode.startswith(b'04')

        if is_subtree: #recurse if subdir
            result.update(tree_to_dict(repo, leaf.sha, full_path))
        else: # store path if blob
            result[full_path] = leaf.sha

    return result

def index_write(repo, index):
    with open(repo_file(repo, "index"), "wb") as file:

        #HEADER

        #magic bytes
        file.write(b"DIRC")
        #version number
        file.write(index.version.to_bytes(4, "big"))
        #number of entries
        file.write(len(index.entries).to_bytes(4, "big"))

        #Entries
        idx = 0
        for entry in index.entries:
            file.write(entry.ctime[0].to_bytes(4, "big"))
            file.write(entry.ctime[1].to_bytes(4, "big"))
            file.write(entry.mtime[0].to_bytes(4, "big"))
            file.write(entry.mtime[1].to_bytes(4, "big"))
            file.write(entry.dev.to_bytes(4, "big"))
            file.write(entry.ino.to_bytes(4, "big"))

            #Mode
            mode = (entry.mode_type << 12) | entry.mode_perms
            file.write(mode.to_bytes(4, "big"))

            file.write(entry.uid.to_bytes(4, "big"))
            file.write(entry.gid.to_bytes(4, "big"))

            file.write(entry.fsize.to_bytes(4, "big"))
            file.write(int(entry.sha, 16).to_bytes(20, "big"))

            flag_assume_valid = 0x1 << 15 if entry.flag_assume_valid else 0

            name_bytes = entry.name.encode("utf8")
            bytes_len = len(name_bytes)
            if bytes_len >= 0xFFF:
                name_length = 0xFFF
            else:
                name_length = bytes_len

            # Merging the three parts into one (2 flags + length)
            file.write((flag_assume_valid | entry.flag_stage | name_length).to_bytes(2, "big"))

            file.write(name_bytes)
            file.write((0).to_bytes(1, "big"))

            idx += 62 + len(name_bytes) + 1

            # Adding padding if necessary

            if idx % 8 != 0:
                pad = 8 - (idx % 8)
                file.write((0).to_bytes(pad, "big"))
                idx += pad

def rm(repo, paths, delete=True, skip_missing=False):
    #find and read index
    index = index_read(repo)

    worktree = repo.worktree + os.sep

    #making paths absolute
    abspaths = list()
    for path in paths:
        abspath = os.path.abspath(path)
        if abspath.startswith(worktree):
            abspaths.append(abspath)
        else:
            raise Exception("Cannot remove paths outside of worktree: {}".format(paths))

    kept_entries = list()
    remove = list()

    for entry in index.entries:
        full_path = os.path.join(repo.worktree, entry.name)

        if full_path in abspaths:
            remove.append(full_path)
            abspaths.remove(full_path)
        else:
            kept_entries.append(entry) #saving entry

    if len(abspaths) > 0 and not skip_missing:
        raise Exception("Cannot remove paths not in the index: {}".format(abspaths))

    if delete:
        for path in remove:
            os.unlink(path)

    index.entries = kept_entries
    index_write(repo, index)

def add(repo, paths, delete=True, skip_missing=False):
    #remove all paths from index

    rm(repo, paths, delete=False, skip_missing=True)

    worktree = repo.worktree + os.sep

    #convert paths to paris: (absolute, relative_to_worktree)
    #delte them form index if present
    clean_paths = list()
    for path in paths:
        abspath = os.path.abspath(path)
        if not (abspath.startswith(worktree) and os.path.isfile(abspath)):
            raise Exception("Not a file, or outside the worktree: {}".format(paths))
        relpath = os.path.relpath(abspath, repo.worktree)
        clean_paths.append((abspath, relpath))

        #find an read the index; it was modified by rm

        index = index_read(repo)

        for(abspath, relpath) in clean_paths:
            with open(abspath, "rb") as fd:
                sha = object_hash(fd, b"blob", repo)

            stat = os.stat(abspath)

            ctime_s = int(stat.st_ctime)
            ctime_ns = stat.st_ctime_ns % 10**9
            mtime_s = int(stat.st_mtime)
            mtime_ns = stat.st_mtime_ns % 10**9

            entry = GitIndexEntry(ctime=(ctime_s, ctime_ns), mtime=(mtime_s, mtime_ns), dev=stat.st_dev, ino=stat.st_ino,
                                mode_type=0b1000, mode_perms=0o644, uid=stat.st_uid, gid=stat.st_gid,
                                fsize=stat.st_size, sha=sha, flag_assume_valid=False,
                                flag_stage=False, name=relpath)
            index.entries.append(entry)

        #writing index back
        index_write(repo, index)

def gitconfig_read():
    xdg_config_home = os.environ["XDG_CONFIG_HOME"] if "XDG_CONFIG_HOME" in os.environ else "~/.config"
    configfiles = [
        os.path.expanduser(os.path.join(xdg_config_home, "git/config")),
        os.path.expanduser("~/.gitconfig")
    ]

    config = configparser.ConfigParser()
    config.read(configfiles)
    return config

def gitconfig_user_get(config):
    if "user" in config:
        if "name" in config["user"] and "email" in config["user"]:
            return "{} <{}>".format(config["user"]["name"], config["user"]["email"])
    return "Unknown User"

def tree_from_index(repo, index):
    contents = dict()
    contents[""] = list()

    #Enumerate entries, and making them dictionaries ( key = directory, content = values)

    for entry in index.entries:
        dirname = os.path.dirname(entry.name)

        key = dirname
        while key!= "":
            if not key in contents:
                contents[key] = list()
            key = os.path.dirname(key)

        contents[dirname].append(entry)

    #sort paths descending by length
    sorted_paths = sorted(contents.keys(), key=len, reverse=True)

    #curr tree sha, after iteration it will be root tree sha
    sha = None

    for path in sorted_paths:
        tree = GitTree()

        for entry in contents[path]:
            if isinstance(entry, GitIndexEntry): #regular entry (file)
                #transcode the mode: entry is int, ascii is needed
                leaf_mode = "{:02o}{:04o}".format(entry.mode_type, entry.mode_perms).encode("ascii")
                leaf = GitTreeLeaf(mode = leaf_mode, path=os.path.basename(entry.name), sha=entry.sha)
            else: #Tree :+ sotred as a pair (basename, SHA)
                leaf = GitTreeLeaf(mode = b"0400000", path=entry[0], sha=entry[1])

            tree.items.append(leaf)

        #Write the new tree object to the store
        sha = object_write(tree, repo)

        #add new tree hash to curr dictionary's parent as pair (basename, SHA)
        parent = os.path.dirname(path)
        base = os.path.basename(path) # name without path: ex main.c for src/main.c
        contents[parent].append((base, sha))

    return sha

def commit_create(repo, tree, parent, author, timestamp, message):
    commit = GitCommit() #Create the new commit object.
    commit.keyvaluelist[b"tree"] =  tree.encode("ascii")
    if parent:
        commit.keyvaluelist[b"parent"] = parent.encode("ascii")

    #format timezone
    offset = int(timestamp.astimezone().utcoffset().total_seconds())
    hours = offset // 3600
    minutes = (offset % 3600) // 60
    tz = "{}{:02}{:02}".format("+" if offset > 0 else "-", hours, minutes)

    author = author + timestamp.strftime(" %s ") + tz

    commit.keyvaluelist[b"author"] = author.encode("utf8")
    commit.keyvaluelist[b"committer"] = author.encode("utf8")
    commit.keyvaluelist[None] = message.encode("utf8")

    return object_write(commit, repo)

"""RGIT COMMANDS"""

def rgit_init(args):
    repo_create(args.path)

def rgit_cat_file(args):
    repo=repo_find_root()
    cat_file(repo, args.object, format=args.type.encode())

def rgit_hash_object(args):
    if args.write:
        repo = repo_find_root()
    else:
        repo = None
    
    with open(args.path, "rb") as file:
        sha = object_hash(file, args.type.encode(), repo)
        print(sha)

def rgit_log(args):
    repo_find_root()

    print("digraph rgit-log{")
    print("  node[shape=rect]")
    log_graphics(repo, object_find(repo, args.commit), set())
    print("}")

def rgit_ls_tree(args):
    repo = repo_find_root()
    ls_tree(repo, args.tree, args.recursive)

def rgit_checkout(args):
    repo = repo_find_root()

    obj = object_read(repo, object_find(repo, args.commit))

    if obj.format == b'commit':
        obj = object_read(repo, obj.keyvaluelist[b'tree'].decode("ascii"))

    if os.path.exists(args.path):
        if not os.path.isdir(args.path):
            if not os.path.isdir(args.path):
                raise Exception("Not a directory {0}!".format(args.path))
            if os.listdir(args.path):
                raise Exception("Not empty {0}! Chance of erasing data. ABORTED".format(args.path))
    else:
        os.makedirs(args.path)
    
    tree_checkout(repo, obj, os.path.realpath(args.path))

def rgit_show_ref(args):
    repo = repo_find_root()
    refs = ref_list(repo)
    show_ref(repo, refs, prefix="refs")

def rgit_tag(args):
    repo = repo_find_root()

    if args.name:
        tag_create(repo, args.name, args.object, type="object" if args.create_tag_object else "ref")

    else:
        refs = ref_list(repo)
        show_ref(repo, refs["tags"], with_hash=False)

def rgit_rev_parse(args):
    if args.type:
        format = args.type.encode()
    else:
        format = None
    
    repo = repo_find_root()

    print(object_find(repo, args.name, format, follow=True))

def rgit_ls_files(args):
    repo = repo_find_root()
    index = index_read(repo)
    if args.verbose:
        print("Index file format v{}, containing {} entries.".format(index.version, len(intex.entries)))

    for entry in index.entries:
        print(entry.name)
        if args.verbose:
            print("  {} with perms: {:o}".format(
                {
                0b1000: "regular file",
                0b1010: "symlink",
                0b1110: "git link" }[entry.mode_type],
                entry.mode_perms
                ))
            print("  on blob: {}".format(entry.sha))
            print("  created: {}.{}".format(
                datetime.fromtimestamp(entry.ctime[0]),
                entry.ctime[1],
                datetime.fromtimestamp(entry.mtime[0]),
                entry.mtime[1]))
            print("  device: {}, inode: {}".format(entry.dev, entry.ino))
            print("  user: {} ({}) group: {} ({})".format(
                pwd.getpwuid(entry.uid).pw_name,
                entry.uid,
                grp.getgrgid(entry.gid).gr_name,
                entry.gid))
            print("  flags: stage={} assume_valid={}".format(
                entry.flag_stage,
                entry.flag_assume_valid))

def rgit_check_ignore(args):
    repo = repo_find_root()
    rules = gitignore_read(repo)
    for path in args.path:
        if check_ignore(rules, path):
            print(path)

def rgit_status(_):
    repo = repo_find_root()
    index = index_read(repo)

    rgit_status_branch(repo)
    rgit_status_head_index(repo, index)
    print()
    rgit_status_index_worktree(repo, index)

def rgit_status_branch(repo):
    branch = branch_get_active(repo)
    if branch:
        print("On branch {}.".format(branch))
    else:
        print("HEAD detached at {}".format (object_find(repo, "HEAD")))

def rgit_status_head_index(repo, index):
    print("Changes to be committed:")

    head = tree_to_dict(repo, "HEAD")
    for entry in index.entries:
        if entry.name in head:
            if head[entry.name] != entry.sha:
                print("  modified:", entry.name)
            del head[entry.name] #delete the key
        else:
            print("  added:  ", entry.name)

    #keys remaining in head that were not in the index get deleted
    for entry in head.keys():
        print("  deleted: ", entry)

def rgit_status_index_worktree(repo, index):
    print("Changes not staged for commit:")

    ignore = gitignore_read(repo)

    gitdir_prefix = repo.gitdir + os.path.sep

    all_files = list()

    #Walking the filesystem
    for (root, _, files) in os.walk(repo.worktree, True):
        if root == repo.gitdir or root.startswith(gitdir_prefix):
            continue
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, repo.worktree)
            all_files.append(rel_path)

    #Traversing the index + compare files with cached version\
    for entry in index.entries:
        full_path = os.path.join(repo.worktree, entry.name)

        # file name is in index
        if not os.path.exists(full_path):
            print("  deleted: ",entry.name)
        else:
            stat = os.stat(full_path)

            #compare metadata
            ctime_ns = entry.ctime[0] * 10**9 + entry.ctime[1]
            mtime_ns = entry.mtime[0] * 10**9 +entry.mtime[1]
            if (stat.st_ctime_ns != ctime_ns) or (stat.st_mtime_ns != mtime_ns):
                #if different, in-depth comparison
                # this will crash on symlinks to dir.
                with open(full_path, "rb") as fd:
                    new_sha = object_hash(fd, b"blob", None)
                    #if hashes are the same => files are the same
                    same = entry.sha == new_sha

                    if not same:
                        print("  modified:", entry.name)
        if entry.name in all_files:
            all_files.remove(entry.name)

    print()
    print("Untracked files:")

    for file in all_files:
        if not check_ignore(ignore, file):
            print(" ", file)

def rgit_rm(args):
    repo = repo_find_root()
    rm(repo, args.path)

def rgit_add(args):
    repo = repo_find_root()
    add(repo, args.path)

def rgit_commit(args):
    repo = repo_find_root()
    index = index_read(repo)
    #create trees & grab back sha for root tree
    tree= tree_from_index(repo, index)

    #create commit object
    commit = commit_create(repo,
                        tree,
                        object_find(repo, "HEAD"),
                        gitconfig_user_get(gitconfig_read()),
                        datetime.now(),
                        args.message)

    #update Head to tip of the active branch
    active_branch = branch_get_active(repo)
    if active_branch: #if on a branch, update refs/heads/BRANCH
        with open(repo_file(repo, os.path.join("refs/heads", active_branch)), "w") as fd:
            fd.write(commit + '\n')
    else: #update HEAD itself
        with open(repo_file(repo, "HEAD"), "w") as fd:
            fd.write("\n")

"""Parser and subparser for arguments"""

argparser = argparse.ArgumentParser(
    description='A git-like version control made by RagnarokMew, a testament to crunch culture and tutorials',
    epilog='I sometimes wonder why did I do this to myself')

argsubparsers = argparser.add_subparsers(title='Commands', dest='command')
argsubparsers.required = True

### this may not work since intellisense says it doesn't exist but python doc says it does
argsp = argsubparsers.add_parser("init", help="Initialize a new, empty repository.")
argsp.add_argument("path",
                    metavar="directory",
                    nargs="?",
                    default=".",
                    help="Where the repository gets created.")

argsp = argsubparsers.add_parser("cat-file", help="Provide content of repository objects")
argsp.add_argument("type",
                    metavar="type",
                    choices=["blob", "commit", "tag", "tree"],
                    help="Type of object to be displayed")
argsp.add_argument("object",
                    metavar="object",
                    help="The object to display")

argsp = argsubparsers.add_parser("hash-object",
                                help="Compute object ID and optionally creates a blob from a file")                  
argsp.add_argument("-t",
                    metavar="type",
                    dest="type",
                    choices=["blob", "commit", "tag", "tree"],
                    default="blob",
                    help="Specify the type")
argsp.add_argument("-w",
                    dest="write",
                    action="store_true",
                    help="Actually write the object into the database")
argsp.add_argument("path",
                    help="Read object from <file>")

argsp = argsubparsers.add_parser("log", help="Display history of a given commit.")
argsp.add_argument("commit",
                    default="HEAD",
                    nargs="?",
                    help="Commit to start at.")

argsp = argsubparsers.add_parser("ls-tree", help="Print a tree object.")
argsp.add_argument("-r",
                    dest = "recursive",
                    action="store_true",
                    help="Recurse into sub-trees")
argsp.add_argument("tree",
                    help=" A tree object")

argsp = argsubparsers.add_parser("checkout", help="Checkout a commit (inside of a directory)")
argsp.add_argument("commit",
                    help="The commit or tree to checkout.")
argsp.add_argument("path",
                    help="The EMPTY directory to checkout on.")

argsp = argsubparsers.add_parser("show-ref", help="List references")

argsp = argsubparsers.add_parser("tag", help="List and create tags")
argsp.add_argument("-a",
                    action="store_true",
                    dest="create_tag_object",
                    help="Whether to create a tag object")
argsp.add_argument("name",
                    nargs="?",
                    help="The new tag's name")
argsp.add_argument("object",
                    default="HEAD",
                    nargs="?",
                    help="The object the new tag will point to")

argsp = argsubparsers.add_parser("rev-parse", help="Parse revision (or other objects) identifiers")
argsp.add_argument("-rgit-type",
                    metavar="type",
                    dest="type",
                    choices=["blob", "commit", "tag", "tree"],
                    default=None,
                    help="Specify the expected type")
argsp.add_argument("name",
                    help="The name to parse")

argsp = argsubparsers.add_parser("ls-files", help="List all the staged files")
argsp.add_argument("--verbose", action="store_true", help="Show everything.")

argsp = argsubparsers.add_parser("check-ignore", help = "Check path(s) against ignore rules.")
argsp.add_argument("path", nargs="+", help="Paths to check")

argsp = argsubparsers.add_parser("status", help = "Show the working tree status.")

argsp = argsubparsers.add_parser("rm", help = "Remove files from the working tree and the index.")
argsp.add_argument("path", nargs="+", help = "Files to remove")

argsp = argsubparsers.add_parser("add", help = "Add files contents to the index.")
argsp.add_argument("path", nargs="+", help = "Files to add")

argsp =argsubparsers.add_parser("commit", help="Record changes to the repository.")

argsp.add_argument("-m",
                metavar="message",
                dest="message",
                help="Message to associate with this commit.")

"""Command handler"""

def main(argv = sys.argv[1:]):
    args = argparser.parse_args(argv)
    match args.command:
        case "add": rgit_add(args)
        case "cat-file": rgit_cat_file(args)
        case "check-ignore": rgit_check_ignore(args)
        case "checkout": rgit_checkout(args)
        case "commit": rgit_commit(args)
        case "hash-object": rgit_hash_object(args)
        case "init": rgit_init(args)
        case "log": rgit_log(args)
        case "ls-files": rgit_ls_files(args)
        case "ls-tree": rgit_ls_tree(args)
        case "rev-parse": rgit_rev_parse(args)
        case "rm": rgit_rm(args)
        case "show-ref": rgit_show_ref(args)
        case "status": rgit_status(args)
        case "tag": rgit_tag(args)
        case _ : print("No such command exists: {}.".format(args.command))

