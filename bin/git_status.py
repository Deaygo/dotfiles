#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from __future__ import print_function
from __future__ import unicode_literals
from collections import OrderedDict
from subprocess import PIPE, check_output
import os
import re
import socket

COLORS = {
    'venv': 6,
    'host': 6,
    'path': 4,
    'git_unstaged': 1,
    'git_staged': 6,
    'git_ahead': 6,
    'git_behind': 1,
    'git_both': 9
}


prompt_fmt = '''
{title}
{t.normal}{t.venv}{venv[0]}
{t.normal}{user_at_host}
{t.normal}{path}
{t.normal}{git}
{t.normal}$
{t.normal} '''.replace('\n', '')
letters = {'?': '+', 'A': '+', 'M': '±', 'R': '±', 'C': '±', 'D': '-', 'U': '!'}
symbols = {'ahead': '→', 'behind': '←', 'both': '↔'}


try:
    import blessings
except ImportError:
    blessings = None


class TermWrapper(object):
    def __init__(self, *a, **kw):
        self.term = blessings and blessings.Terminal(*a, **kw)

    @property
    def alive(self):
        return bool(self.term)

    def __getattr__(self, k):
        if not self.term:
            return ''
        if k != 'color' and k in COLORS:
            v = self.term.color(COLORS[k])
        else:
            v = getattr(self.term, k)
        if isinstance(v, basestring) and not self.term.is_a_tty:
            return "\\[{}\\]".format(v)
        else:
            return v


def git_stats():
    try:
        res = check_output("git status --untracked --short --branch".split(), stderr=PIPE)
    except:
        return None

    work_stat = OrderedDict()
    for d in "+±-!":
        work_stat[d] = 0

    staged_stat = OrderedDict()
    for d in "+±-!":
        staged_stat[d] = 0

    ahead = 0
    behind = 0
    remote = False
    branch = None

    for l in res.splitlines():
        m = re.match(r"^([^#])(.) (?P<path1>.*?)(?: -> (?P<path2>.*))?$", l)
        if m:
            i, w = m.group(1, 2)
            if i in letters and i not in "?U":
                staged_stat[letters[i]] += 1
            if w in letters:
                work_stat[letters[w]] += 1
        m = re.match(r"^## (?P<branch>[^.]+)(?:\.\.\.(?P<upstream>\S+)(?: \[(?:ahead (?P<ahead>\d+))?(?:, )?(?:behind (?P<behind>\d+))?\])?)?$", l)
        if m:
            branch = m.group('branch') or None
            remote = m.group('upstream') is not None
            ahead = int(m.group('ahead') or 0)
            behind = int(m.group('behind') or 0)

    work_stat = "".join("{}{}".format(k, v) for k, v in work_stat.items() if v)
    staged_stat = "".join("{}{}".format(k, v) for k, v in staged_stat.items() if v)

    return {"branch": branch, "remote": remote, "ahead": ahead, "behind": behind, "work": work_stat, "staged": staged_stat, "remote": remote}


def get_venv(fmt='{}'):
    if "VIRTUAL_ENV" in os.environ:
        return (fmt.format(os.path.basename(os.environ["VIRTUAL_ENV"])),')')
    else:
        return ('','')


def get_userinfo(term):
    s = ""
    #if "SSH_CONNECTION" in os.environ:
    s += "{t.yellow}{0}{t.normal}@{t.cyan}{1}".format(os.environ.get('USER'), socket.gethostname(), t=term)
    return s


def bash_escape(s):
    return s.replace("\\", "\\\\")


def trail(*a):
    return os.path.join(*(list(a) + ['']))


def getcwd():
    if "PWD" in os.environ:
        return os.environ["PWD"]
    return os.getcwd()


def windows_path():
    letter = check_output("hostname")[0].upper()
    return "{}:{}".format(letter, getcwd().replace("/", "\\"))


def short_path():
    hd = os.path.expanduser("~")
    if trail(getcwd()).startswith(trail(hd)):
        return getcwd().replace(hd, "~", 1)
    return getcwd()


def get_prompt(term, path):
    if term.is_a_tty or (not os.environ["TERM"].startswith("xterm") and not os.environ["TERM"].startswith("rxvt")):
        title_fmt = ""
    else:
        title_fmt = "\\[\033]0;{}\a\\]"
    if "TITLE" in os.environ:
        set_title = title_fmt.format(os.environ["TITLE"])
    else:
        set_title = title_fmt.format("{}{}@{}:{}".format(get_venv('({})')[0],
                                                          os.environ["LOGNAME"],
                                                          socket.gethostname(),
                                                          short_path()))

    gitinfo = git_stats()
    if not gitinfo:
        return prompt_fmt.format(git="",
                                 path=path,
                                 t=term,
                                 title=set_title,
                                 venv=get_venv('({})'),
                                 user_at_host=get_userinfo(term))

    branch = gitinfo["branch"]

    real_branch = branch

    if not branch:
        try:
            branch = check_output("git rev-parse --short HEAD".split(), stderr=PIPE).strip()
        except:
            branch = False

    staged = " " + term.green + gitinfo["staged"] if gitinfo["staged"] else ""
    work = ("" if staged else " ") + term.red + gitinfo["work"] if gitinfo["work"] else ""
    if staged and work:
        delim = term.normal + "|"
    else:
        delim = ""

    count = ""
    op, cp = "[", "]"

    if branch is False:
        bc = term.git_ahead
        op, cp = "(", ")"
        branch = "INIT"
    elif gitinfo["ahead"] and gitinfo["behind"]:
        bc = term.git_both
        count = " {t.git_behind}{}{t.white}{}{t.git_ahead}{}".format(gitinfo["behind"], symbols['both'], gitinfo["ahead"], t=term)
    elif gitinfo["ahead"] and not gitinfo["behind"]:
        bc = term.git_ahead
        count = " {}{t.git_ahead}{}".format(symbols['ahead'], gitinfo["ahead"], t=term)
    elif gitinfo["behind"] and not gitinfo["ahead"]:
        bc = term.git_behind
        count = " {t.git_behind}{}{t.white}{}".format(gitinfo["behind"], symbols['behind'], t=term)
    elif not real_branch:
        bc = term.git_both
    elif not gitinfo["remote"]:
        bc = term.git_ahead  # we haven't pushed this branch
    else:
        bc = term.cyan

    prompt = " {t.white}{op}{branch}{t.normal}{t.white}{count}{t.normal}{staged}{delim}{work}{t.normal}{t.white}{cp} "\
        .format(t=term, branch=(term.bold if False and real_branch else "") + bc + bash_escape(branch),
            staged=staged, work=work, delim=delim, count=count, op=op, cp=cp)

    return prompt_fmt.format(git=prompt,
                             path=path,
                             t=term,
                             title=set_title,
                             venv=get_venv('({})'),
                             user_at_host=get_userinfo(term))


def main(colour=True, windows=False):
    term = TermWrapper(force_styling=True if colour else None)

    if windows:
        path = windows_path()
    else:
        path = short_path()

    if len(path) > 20:
        parts = path.split(os.sep)
        newparts = []
        for p in parts:
            if len(p) > 3:
                p = p[:2] + "*"
            newparts.append(p)
        path = os.sep.join(newparts)

    p = get_prompt(term, bash_escape(path))
    print(p.encode("utf8"), end="\n" if term.is_a_tty else "")

if __name__ == '__main__':
    main()
