#!/usr/bin/env python3

import shippy
import re
import subprocess
import argparse

def identifiers_from_line(line, match_urls=False):
    line = line.strip()
    
    fixes = re.findall(r'(?:Fix|Fixes|Fixed|Close|Closes|Closed)\s*#(\d+)', line, re.IGNORECASE)
    urls = []
    if match_urls:
        urls = re.findall(r'ship://(?:Problems/)?(\d+)', line, re.IGNORECASE)
    
    fixes = [int(i) for i in fixes]
    urls = [int(i) for i in urls]
    
    return set(fixes + urls)

def locate_fixed_problems(commit_message):
    """
    Parse the provided commit message and return an array of problem identifiers
    that have been fixed.
    
    A problem is believed to be fixed if it is part of a list of ship://Problem/{id}
    URLs placed at the top of the commit message (separated by newlines) or if the problem
    is indicated by the string Fix(es|ed) #{id} or Close(s|d) #{id}.
    
    Commit message for example:
    
        ship://Problems/314 <Update problems with build numbers from build bot>
        ship://Problems/322 <Create / Update problem APIs>
        
        Made some improvements. Yay me!
        
        Also Fix #403 and Close #407
    
    This method would parse out 314, 322, 403, 407
    
    Args:
        commit_message (str): The commit message to parse
    
    Returns:
        problem identifiers (set)
    """
    
    identifiers = set()
    
    commit_message = commit_message.strip()
    lines = commit_message.splitlines()
    
    match_urls = True
    for line in lines:
        ids = identifiers_from_line(line, match_urls)
        if len(ids) == 0:
            match_urls = False
        
        identifiers.update(ids)
    
    return identifiers

class Commit(object):
    """
    Attributes:
        commit_hash (str)
        author (str)
        date (str)
        message (str)
    """
    
    def __init__(self, commit_hash=None, author=None, date=None, message=None):
        self.commit_hash = commit_hash
        self.author = author
        self.date = date
        self.message = message
        
    def __repr__(self):
        return str(self)
        
    def __str__(self):
        return "commit %s\nAuthor: %s\nDate:   %s\n\n%s\n" %  (self.commit_hash, self.author, self.date, self.message)

def commits_between(repo_path, start, end):
    """
    Shells out to git(1), and locates the commits between start and end within repo_path.
    
    Returns a list of Commit objects for each commit in the range given.
    """
    
    git = subprocess.Popen(["git", "log", "%s..%s" % (start, end)], stdout=subprocess.PIPE, cwd=repo_path)
    log = git.stdout.read().decode("utf-8")
    
    cur = None
    commits = []
    
    for line in log.splitlines():
        cm = re.match(r'commit ([a-f0-9]{40})', line)
        if cm is not None:
            if cur:
                commits.append(cur)
            cur = Commit(cm.group(1))
            
        if cur is not None and cm is None:
            if cur.message is None:
                if line.startswith("Author:"):
                    cur.author = line[len("Author: "):]
                elif line.startswith("Date:"):
                    cur.date = line[len("Date:   "):]
                else:
                    cur.message = ""
            else:
                cur.message += line.strip() + "\n"
    
    if cur is not None:
        commits.append(cur)
    
    return commits

if __name__ == "__main__":
        
    parser = argparse.ArgumentParser()
    
    # Positional arguments
    parser.add_argument("bot", help="Name of the bot doing the build (used to set the keyword in ship)")
    parser.add_argument("build", help="Build number just performed (used to set the keyword value in ship)")
    parser.add_argument("repo", help="Path to git repo")
    parser.add_argument("start", help="Start git object (i.e. commit hash, branch, tag, etc")
    parser.add_argument("end", help="End git object (i.e. commit hash, branch, tag, etc")
    
    # Optional arguments
    parser.add_argument("--apitoken", help="Ship API Key (if omitted, will be read from environment variable SHIP_API_TOKEN)")
    parser.add_argument("--apiserver", help="Ship API Server (if omitted, will be https://api.realartists.com)")
    parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()
    
    commits = commits_between(args.repo, args.start, args.end)
    
    for commit in commits:
        print(commit)
    
    api = shippy.Api(token=args.apitoken)
    if args.dry_run:
        api.dry_run = True

    identifiers = set()    
    for commit in commits:
        identifiers.update(locate_fixed_problems(commit.message))
    
    for id in identifiers:
        print("Updating problem %d" % (id))
        api.problem_keyword_set(id, "Built in %s" % (args.bot), args.build)
    
    