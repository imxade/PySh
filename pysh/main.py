#!/usr/bin/env python


import os
import readline
import subprocess


def _exit(code, env):
    try:
        writeHistory(env)
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


def _out(_stdout, out, err):
    out = "" if out is None else out
    err = "" if err is None else err
    ret = out + err
    if not _stdout:
        return ret
    elif "&" in _stdout[0]:
        data = ret
        ret = ""
    elif "2" in _stdout[0]:
        data = err
        ret = out
    else:
        data = out
        ret = err
    save(data, _stdout[1], "a" if ">>" in _stdout[0] else "w")
    return ret


def findExe(arg, env):
    for path in allCmds.env.get("PATH", "").split(os.pathsep):
        binPath = os.path.join(path, arg)
        if os.access(binPath, os.X_OK):
            # Only first path # fix
            return binPath


def chkType(args, env):
    result = []
    err = []
    for arg in args:
        binPath = findExe(arg, env)
        if arg in builtins():
            result.append(f"{arg} is a shell builtin")
        elif binPath:
            result.append(f"{arg} is {binPath}")
        else:
            err.append(f"{arg}: not found")
    out, err = "\n".join(result), "\n".join(err)
    out += "\n" if out else ""
    err += "\n" if err else ""
    return out, err


def cd(args):
    try:
        path = args[0] if args else "~"
        os.chdir(os.path.expanduser(path))
        return "", ""
    except Exception as e:
        return "", f"cd: {args[0]}: No such file or directory\n"


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
        ]:
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


def getWindowsCmdlets(env=None):
    cmdlets = set()
    powershell_cmd = (
        "Get-Command | Select-Object -ExpandProperty Name; "
        "Get-Alias | Select-Object -ExpandProperty Name"
    )
    command = f'powershell -Command "{powershell_cmd}"'

    result = subprocess.run(
        ["powershell", "-Command", powershell_cmd],
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode == 0:
        for line in result.stdout.splitlines():
            line = line.strip()
            if line:
                cmdlets.add(line)

    return cmdlets


def allCmds():
    if hasattr(allCmds, "cached"):
        return allCmds.cached

    cmds = set(builtins().keys())
    for path in allCmds.env.get("PATH", "").split(os.pathsep):
        try:
            for f in os.listdir(path):
                if os.access(os.path.join(path, f), os.X_OK):
                    cmds.add(f)
        except Exception:
            continue

    if os.name == "nt":
        cmds.update(getWindowsCmdlets())

    allCmds.cached = cmds
    return cmds


def completer(text, state):
    # fix completion for paths
    matches = [cmd for cmd in allCmds() if cmd.startswith(text)]
    return matches[state] + " " if state < len(matches) else None


def customDisplay(substitution, matches, longest_match_length):
    print()
    print(" ".join(matches))
    prompt = "$ " + readline.get_line_buffer()
    print(prompt, end="", flush=True)


def readMultilineInput(prompt="$ "):
    lines, stack = [], []
    quote, colon, logicOp = None, False, False
    pairs = {"(": ")", "{": "}", "[": "]"}

    while True:
        line = input(prompt if not lines else "> ")
        lines.append(line)
        stripped = line.rstrip()

        # Handle colon block: require 2 blank lines after ":"
        # On top, to stay unaffected by other continuations
        if colon:
            if stripped == "":
                break
            else:
                continue

        # Line continuation
        if stripped.endswith("\\"):
            lines[-1] = stripped[:-1]
            continue

        # Quote tracking with escape
        i = 0
        while i < len(line):
            c = line[i]
            esc = i > 0 and line[i - 1] == "\\"
            if quote:
                if c == quote and not esc:
                    quote = None
            elif c in {"'", '"', "`"} and not esc:
                quote = c
            i += 1

        # Bracket balance
        for c in line:
            if c in pairs:
                stack.append(pairs[c])
            elif c in pairs.values() and stack and c == stack[-1]:
                stack.pop()

        # Continue if open quotes or brackets, others dont matter (Highest Priority)
        if quote or stack:
            continue

        # Continue if logic operators
        if stripped.endswith(("|", "&&")):
            logicOp = True
        elif logicOp and stripped != "":
            break
        if logicOp:
            continue

        # Continue if colon
        if stripped.endswith(":"):
            colon = True
            continue

        break

    return "\n".join(lines)


def splitLogicalOps(cmdLine):
    ops = {"&&", "||", "&"}
    result = []
    current = ""
    i = 0
    quote = None

    while i < len(cmdLine):
        c = cmdLine[i]

        # Quote tracking
        if quote:
            current += c
            if c == quote:
                quote = None
            i += 1
            continue
        elif c in {"'", '"'}:
            quote = c
            current += c
            i += 1
            continue

        # Check for operators only if outside quotes
        if cmdLine[i : i + 2] in {"&&", "||"}:
            result.append((current.strip(), cmdLine[i : i + 2]))
            current = ""
            i += 2
            continue
        elif c == "&":
            result.append((current.strip(), "&"))
            current = ""
            i += 1
            continue

        current += c
        i += 1

    if current.strip():
        result.append((current.strip(), None))
    return result


def splitByPipes(s):
    parts = []
    buf = ""
    quote = None
    escape = False

    for i, c in enumerate(s):
        if escape:
            buf += c
            escape = False
            continue
        if c == "\\":
            escape = True
            buf += c
            continue
        if c in {"'", '"'}:
            if quote == c:
                quote = None
            elif not quote:
                quote = c
        if c == "|" and not quote:
            parts.append(buf)
            buf = ""
        else:
            buf += c
    if buf:
        parts.append(buf)
    return parts


def _history(args, env):
    start = -1
    end = readline.get_current_history_length()
    if not args:
        start = 0
    elif len(args) == 1 and args[0].isdigit():
        n = int(args[0])
        start = end - n if n > 0 and n < end else 0
    elif args[0] not in ["-r", "-w", "-a"] or len(args) > 2:
        return "", "unexpected argument"
    elif args[0] == "-r":
        readHistory(env, args[1])
    elif args[0] == "-w":
        writeHistory(env, args[1])
    elif args[0] == "-a":
        appendHistory(env, args[1])

    if start == -1:
        return "", ""
    return historyRange(start, end)


def historyRange(start, end):
    result = ""
    for i in range(start + 1, end + 1):
        cmd = readline.get_history_item(i)
        result += f"    {i}  {cmd}\n" if cmd else ""
    return result, ""


def readHistory(env, file=None):
    if not file:
        file = env.get("HISTFILE")
    readline.read_history_file(file)


def writeHistory(env, file=None):
    if not file:
        file = env.get("HISTFILE")
    readline.write_history_file(file)


def appendHistory(env, file=None):
    if not file:
        file = env.get("HISTFILE")
    n = readline.get_current_history_length()
    readline.append_history_file(n - getattr(appendHistory, "last", 0), file)
    appendHistory.last = n


def unset(args, env):
    for arg in args:
        env.pop(arg, None)
    return "", ""


def showEnv(env):
    result = "\n".join(f"{k}={v}" for k, v in env.items())
    return result + "\n", ""


def substituteVars(cmd, env):
    result = ""
    i = 0
    while i < len(cmd):
        if cmd[i] == "$":
            if i + 1 < len(cmd) and cmd[i + 1] == "{":
                j = i + 2
                varName = ""
                while j < len(cmd) and cmd[j] != "}":
                    varName += cmd[j]
                    j += 1
                if j < len(cmd) and cmd[j] == "}":
                    result += env.get(varName, "")
                    i = j + 1
                else:
                    result += "$" + "{" + varName
                    i = j
            else:
                j = i + 1
                varName = ""
                while j < len(cmd) and (cmd[j].isalnum() or cmd[j] == "_"):
                    varName += cmd[j]
                    j += 1
                result += str(env.get(varName, ""))  # Only string concats
                i = j
        else:
            result += cmd[i]
            i += 1
    return result


def execChunk(chunk, env, stdinData=None):
    pipedCmds = splitByPipes(chunk)
    if not pipedCmds:
        return 1, None, "", "Empty pipeline\n"

    processes = []
    prevStdout = subprocess.PIPE
    finalStdout = None
    redir = None

    for i, cmd in enumerate(pipedCmds):
        tokens = tokenize(substituteVars(cmd.strip(), env))
        if not tokens:
            return 1, None, "", "Empty command\n"

        cmdName = tokens[0]
        args, redir = parseRedirection(tokens[1:])
        isLast = i == len(pipedCmds) - 1

        # Check if the command is a builtin
        if cmdName in builtins():
            if isLast:
                # Last command, execute builtin and return
                for proc in processes[:-1]:
                    proc.wait()
                if processes:
                    prevOutput, prevError = processes[-1].communicate(stdinData)
                else:
                    prevOutput = stdinData or ""
                    prevError = ""
                out, err = builtins(None, env)[cmdName](args)
                return 0, redir, out, err
            else:
                # Not the last command, execute builtin and continue
                out, err = builtins(None, env)[cmdName](args)
                stdinData = out
                continue

        if cmdName not in allCmds():
            return None

        full_cmd = [cmdName] + args
        if os.name == "nt":
            full_cmd = ["powershell", "-Command"] + full_cmd

        proc = subprocess.Popen(
            full_cmd,
            stdin=prevStdout,
            # Last command, in a Pipeline print to terminal
            stdout=None if isLast and i else subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={k: str(v) for k, v in env.items()},
            text=True,
            bufsize=1,
        )

        if prevStdout and prevStdout != subprocess.PIPE:
            prevStdout.close()

        processes.append(proc)
        prevStdout = proc.stdout

    # Collect final output and error (only from last process)
    if processes:
        if stdinData is not None:
            finalOut, finalErr = processes[-1].communicate(stdinData)
        else:
            finalOut, finalErr = processes[-1].communicate()
        exitCode = processes[-1].returncode
    else:
        finalOut, finalErr = "", ""
        exitCode = 0

    # Wait for all others to finish
    for proc in processes[:-1]:
        proc.wait()

    return exitCode, redir, finalOut, finalErr


def execPython(_stdin, env):
    try:
        result = eval(_stdin, env)
        print(result)
    except:
        exec(_stdin, env)


def builtins(_stdout=None, env=None):
    return {
        "exit": lambda args: _exit(int(args[0]) if args else 0, env),
        "type": lambda args: chkType(args, env),
        "echo": lambda args: (" ".join(args) + "\n", ""),
        "pwd": lambda args: (os.getcwd() + "\n", ""),
        "cd": lambda args: cd(args),
        "history": lambda args: _history(args, env),
        "unset": lambda args: unset(args, env),
        "env": lambda args: showEnv(env),
    }


def main():
    # Retain values of variables in REPL
    env = os.environ.copy()
    allCmds.env = env
    readline.set_completer(completer)
    """
    # fix, unsupported on windows
    readline.set_completion_display_matches_hook(
        customDisplay
    )  
    """
    readline.parse_and_bind("tab: complete")
    try:
        readHistory(env)
    except:
        pass

    while True:

        try:
            _stdin = readMultilineInput()
            if not _stdin.strip():
                continue
        except EOFError:
            print()
            _exit(0, env)
        except:
            print()
            continue

        try:
            runNext = True

            for chunk, op in splitLogicalOps(_stdin):
                if not runNext:
                    if op == "&":
                        continue
                    break

                out = execChunk(chunk, env)
                output = _out(*out[1:]) if out else None

                if output and output[:-1]:
                    print(output[:-1])

                success = out is not None and out[0] == 0

                if op == "&&":
                    runNext = success
                elif op == "||":
                    runNext = not success
                elif op == "&":
                    runNext = True  # Background: do not block

            if out is not None:
                continue  # Skip Python

        except (Exception, KeyboardInterrupt) as e:
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
