import os
import readline


def _exit(code):
    try:
        writeHistory()
    except:
        pass
    try:
        raise SystemExit(code)
    except Exception as e:
        return "", e


def save(data, file, mode):
    with open(file, mode) as f:
        f.write(data)
    return 1


def _out(_stdout, tup):
    out, err = tup
    if not _stdout:
        return out + err
    elif "&" in _stdout[0]:
        data = out + err
        ret = ""
    elif "2" in _stdout[0]:
        data = err
        ret = out
    else:
        data = out
        ret = err
    save(data, _stdout[1], "a" if ">>" in _stdout[0] else "w")
    return ret


def findExe(arg):
    for path in exePaths().split(os.pathsep):
        binPath = os.path.join(path, arg)
        if os.access(binPath, os.X_OK):
            # Only first path # fix
            return binPath


def chkType(args):
    result = []
    for arg in args:
        binPath = findExe(arg)
        if arg in builtins():
            result.append(f"{arg} is a shell builtin")
        elif binPath:
            result.append(f"{arg} is {binPath}")
        else:
            result.append(f"{arg}: not found")
    return "\n".join(result), ""


def cd(args):
    try:
        path = args[0] if args else "~"
        os.chdir(os.path.expanduser(path))
        return "", ""
    except Exception as e:
        return "", f"cd: {args[0]}: No such file or directory"


def parseRedirection(args):
    if not args:
        return args, None
    for i in range(len(args) - 1):
        if args[i] in [
            ">",
            ">|",
            ">>",
            "1>",
            "1>|",
            "1>>",
            "2>",
            "2>|",
            "2>>",
            "&>",
        ]:  # fix with regex
            return args[:i], (args[i], args[i + 1])
    return args, None


def tokenize(s):
    result = []
    token = ""
    state = " "  # can be ' ', 'a', "'", '"', or '\\'
    escape = False
    i = 0
    quoted = False

    while i < len(s):
        c = s[i]

        if state == " ":
            if c.isspace():
                i += 1
                continue
            elif c == "'":
                state = "'"
                quoted = True
            elif c == '"':
                state = '"'
                quoted = True
            elif c == "\\":
                escape = True
                state = "a"
            else:
                token += c
                state = "a"

        elif state == "a":
            if escape:
                token += c
                escape = False
            elif c.isspace():
                result.append(token)
                token = ""
                state = " "
            elif c == "'":
                state = "'"
                quoted = True
            elif c == '"':
                state = '"'
                quoted = True
            elif c == "\\":
                escape = True
            else:
                token += c

        elif state == "'":
            if c == "'":
                state = "a"
            else:
                token += c

        elif state == '"':
            if c == '"':
                state = "a"
            elif c == "\\":
                i += 1
                if i < len(s):
                    next_c = s[i]
                    if next_c in '"\\$`':
                        token += next_c
                    else:
                        token += "\\" + next_c
                else:
                    token += "\\"
            else:
                token += c

        i += 1

    if escape:
        raise ValueError("No escaped character")
    if state in ("'", '"'):
        raise ValueError("No closing quotation")
    if token or quoted:
        result.append(token)
    return result


def exePaths():
    # UNIX
    result = os.getenv("PATH", "")
    if result:
        return result
    # Windows
    return os.getenv("Path", "")


def allCmds():
    cmds = set(builtins().keys())
    for path in exePaths().split(os.pathsep):
        try:
            for f in os.listdir(path):
                if os.access(os.path.join(path, f), os.X_OK):
                    cmds.add(f)
        except Exception:
            pass
    return cmds


def completer(_in, index):
    # fix completion for paths
    if not hasattr(completer, "cached"):
        completer.cached = allCmds()
    matches = [cmd for cmd in completer.cached if cmd.startswith(_in)]
    return matches[index] + " " if index < len(matches) else None


def customDisplay(substitution, matches, longest_match_length):
    print()
    print(" ".join(matches))
    prompt = "$ " + readline.get_line_buffer()
    print(prompt, end="", flush=True)


"""
def fileSize(paths):
    result = 0
    if not paths:
        return result
    for path in paths:
        try:
            result += os.path.getsize(
                os.path.expanduser(path) if path.startswith("~") else path
            )
        except:
            continue
    return result
"""


def splitPipes(_stdin):
    result = []
    rawPipe = ""
    for cmd in _stdin.split(" | "):
        if cmd.split()[0] in builtins():
            if rawPipe:
                result.append(rawPipe)
                rawPipe = ""
            result.append(cmd)
        else:
            rawPipe += " | " + cmd if rawPipe else cmd
    if rawPipe:
        result.append(rawPipe)
    return result


"""
fix
function to split logical operators && ||
def splitLogicalOps 
"""


def _history(args):
    start = -1
    end = readline.get_current_history_length()
    if not args:
        start = 0
    elif len(args) == 1 and args[0].isdigit():
        n = int(args[0])
        start = end - n if n > 0 and n < end else 0
    elif args[0] not in ["-r", "-w", "-a"] or len(args) > 2:
        return "", "unexpected arguement"
    elif args[0] == "-r":
        readHistory(args[1])
    elif args[0] == "-w":
        writeHistory(args[1])
    elif args[0] == "-a":
        appendHistory(args[1])

    if start == -1:
        return "", ""
    return historyRange(start, end)


def historyRange(start, end):
    result = ""
    for i in range(start + 1, end + 1):
        cmd = readline.get_history_item(i)
        result += f"    {i}  {cmd}\n" if cmd else ""
    return result, ""


def readHistory(file=None):
    if not file:
        file = os.getenv("HISTFILE")
    readline.read_history_file(file)


def writeHistory(file=None):
    if not file:
        file = os.getenv("HISTFILE")
    readline.write_history_file(file)


def appendHistory(file=None):
    if not file:
        file = os.getenv("HISTFILE")
    n = readline.get_current_history_length()
    readline.append_history_file(n - getattr(appendHistory, "last", 0), file)
    appendHistory.last = n


def builtins(_stdout=None):
    return {
        "exit": lambda args: _out(_stdout, _exit(int(args[0]) if args else 0)),
        "type": lambda args: _out(_stdout, chkType(args)),
        "echo": lambda args: _out(_stdout, (" ".join(args) + "\n", "")),
        "pwd": lambda args: _out(_stdout, (os.getcwd(), "")),
        "cd": lambda args: _out(_stdout, cd(args)),
        "history": lambda args: _out(_stdout, _history(args)),
    }


def execPython(_stdin, env):
    try:
        result = eval(_stdin, env)
        print(result)
    except:
        exec(_stdin, env)


def execSh(_stdin, pipe=""):
    # _stdin = _stdin.replace("tail -f", "tail")
    command, *args = tokenize(_stdin)
    args, _stdout = parseRedirection(args)
    if command in builtins():
        return builtins(_stdout)[command](args)
        # return builtins(_stdout)[command](args + tokenize(pipe) if pipe else args)
    elif findExe(command):
        prefix = f"echo -ne {repr(pipe)} | " if pipe else ""
        errLog = ".stderr.log"
        outLog = ".stdout.log"
        args = " ".join(args)
        cmd = f"{prefix} '{command}' {args} 2>{errLog} >{outLog}"
        # size = fileSize(args)
        os.system(cmd)
        with open(outLog, "r") as f:
            out = f.read()
        with open(errLog, "r") as f:
            err = f.read()
        return _out(_stdout, (out, err))
    return None


def main():
    # Retain values of variables in REPL
    env = {}
    readline.set_completer(completer)
    # readline.set_completion_display_matches_hook(customDisplay)  # fix, unsupported on windows
    readline.parse_and_bind("tab: complete")
    try:
        readHistory()
    except:
        pass

    while True:

        try:
            _stdin = input("$ ")  # fix add multiline support
            if not _stdin.strip():
                continue
        except EOFError:
            print()
            _exit(0)
        except:
            print()
            continue

        try:
            outList = []
            cmds = splitPipes(_stdin)
            for cmd in cmds:
                if not outList:
                    out = execSh(cmd)
                elif outList[-1] is None:
                    break
                else:
                    out = execSh(cmd, outList[-1])
                outList.append(out)
            if outList and outList[-1] is not None:
                if outList[-1] != "":
                    print(outList[-1].rstrip())
                continue
        except Exception as e:
            print(e)
            continue

        try:
            execPython(_stdin, env)
        except NameError as e:
            print(f"{_stdin.split()[0]}: command not found")
        except Exception as e:
            print(e)


if __name__ == "__main__":
    main()
    