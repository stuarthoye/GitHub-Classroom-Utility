#!/usr/bin/env python

import sys
import json

from utils.classroom_manager import *
from utils import spimgrader as grader
import utils.moss
import utils.graderII as graderII

# flags:  
def help():  
    return \
"""---------------------------------------------------------------------------------------
|   USER COMMANDS
|   
|   NAME
|       main.py - The entry point into a toolset to manage classrooms using Git, Github, MOSS, 
|       & Jenkins.
|
|   SYNOPSIS
|       main.py [OPTION]...
|
|   DECRIPTION
|       main.py provides an interface to the a set of tools that can be used to automate classroom 
|       administration for a course.
|
|   OPTIONS
|   Informational options
|   -h, --help: 
|       print help
|   -D: 
|       print defaults                                      ([D]efaults)
|
|   Setup options
|   -P <prefix>: 
|       set optional prefix for assignments                 (set [P]refix)
|   -S <server url>: 
|       set server url                                      (set [S]erver)
|   -O <organization_name>: 
|       set organization name                               ([O]rg set)
|   -R <repo_name>: 
|       set repo for script                                 ([R]epo set)
|   -A <archive_folder>: 
|       set archive directory                               ([A]rchive set)
|
|   Main Actions
|   -u:
|       gather usernames from github by referencing emails in ./config/users.txt
|   -d:
|       distribute repos, set webhooks, and notify
|   -f:
|       fetch repos, mark them with autograder, and compare with MOSS
|
|   Supplementary actions
|   -j: 
|       create Jobs DSL file for Jenkins                    ([j]obs DSL)
|   -t: 
|       set teams for the organization locally              ([t]eams set)
|   -a <team> <member>: 
|       Add <member> to <team>                              ([a]dd member)
|   -r <team> <member>: 
|       remove <member> from <team>                         ([r]emove member)
|   -s (-R <repo>): 
|       distribute base repo to teams on GitHub             ([s]et repos)
|   -g (-R <base_repo>): 
|       collect repos from students                         ([g]et repos)
|   -w (-R <repo>): 
|       set webhooks for teams working on repo              (set [w]ebhooks)
|   -n: 
|       notify students of repo distribution                ([n]otify)
|   -m: 
|       mark repos                                          ([m]ark repos)
|   -c: 
|       compare repos using MOSS                            ([c]ompare)
|   -x: 
|       clear local repos (-r <assignment>)                 ()
|   -X: 
|       clear teams & repos on GitHub                       ()
|
---------------------------------------------------------------------------------------
"""

# Purpose:
#   Returns a dictionary used to represent default values for the manager to use.
def defaults():
    try:
        f = open("./config/defaults.json", "r")
        defaults = json.load(f)
        f.close()   
        return defaults
    except:
        return {"org": "", "repo": "", "archives": ""}

# Param:
#   field: field in defaults.json to be update.
#   new_value: the value to overwrite where the field is.
# Purpose:
#   Updates the default values used for the manager to the most-recently used ones.
def update(defs):
    try:
        f = open("./config/defaults.json", "w")
        json.dump(defs, f)
        f.close()
        return
    except:
        return

def pretty(defs):
    p = "--------------------------------------------------\n"
    p += "| Current Values Used by the Classroom Manager\n"
    p += "|\n"
    for k, v in defs.items():
        if k == "repo" or k == "org":
            p += "| {}:\t\t{}\n".format(k, v)
        else:
            p += "| {}:\t{}\n".format(k, v)
    p += "--------------------------------------------------\n"
    return p

def parse_flag(flag, args):
    start = args.index(flag)+1
    end = start
    while end < len(args):
        if args[end][0] == "-":
            break
        end += 1
    if start == end:
        return [""]
    else:
        return args[start:end]

def main():
    defs = defaults()
    args = sys.argv

    if "-h" in args or "-H" in args or "--help" in args:
        print help()
        return

    # SETUP
    #----------------------------------------------------------------------------------
    if "-P" in args:
        print "Updating prefix."
        defs["prefix"] = parse_flag("-P", args)[0]

    if "-O" in args:
        print "Updating organization."
        defs["org"] = parse_flag("-O", args)[0]

    if "-R" in args:
        print "Updating repo."
        defs["repo"] = parse_flag("-R", args)[0]

    if "-A" in args:
        print "Updating archives."
        defs["archives"] = parse_flag("-A", args)[0]

    if "-S" in args:
        print "Updating server."
        defs["server"] = parse_flag("-S", args)[0]
    
    update(defs)

    if "-D" in args:
        print pretty(defs)
        return

    # WORK
    #----------------------------------------------------------------------------------
    m = None
    if defs["org"] != "":
        m = Manager(defs["org"])
    else:
        print("WARNING: Organization is not set for the service.")
        return

    if "-u" in args:
        m.get_usernames()

    if "-t" in args:
        m.set_teams()                           # local
        m.set_git_teams()                       # remote
        m.git_to_csv()                          # setup csv for teams

    if "-a" in args:
        flag_args = parse_flag("-a", args)      # parse
        team = flag_args[0]                     # set team
        members = flag_args[1:]                 # set members
        m.add_members(team, members)            # add

    if "-r" in args:
        flag_args = parse_flag("-r", args)      # parse
        team = flag_args[0]                     # set team
        members = flag_args[1:]                 # set members
        m.del_members(team, members)            # delete
    
    if "-s" in args:
        if not m.is_assigned(defs["repo"]):
            m.set_repos(defs["repo"])               # Set github repos
        else:
            print("The repo {} has already been assigned to at least one team".format(defs["repo"]))

    if "-w" in args:
        if m.is_assigned(defs["repo"]):
            m.set_hooks(defs["repo"])               # Set webhooks to distributed repos
        else:
            print("You must distribute the repo {} before performing this action.".format(defs["repo"]))

    if "-d" in args:
        if not m.is_assigned(defs["repo"]):
            m.distribute(defs["repo"])
        else:
            print("The repo {} has already been assigned to at lest one team".format(defs["repo"]))

    if "-f" in args:
        if m.is_assigned(defs["repo"]):
            r = defs["repo"]
            a = defs["archives"]

            m.get_repos(r)
            if r == "lab1":
                grader.main(r)               # Grade with spimgrader
            else:
                graderII.main(r)
            moss.submit(r, archives=a)
        else:
            print("You must distribute the repo {} before performing this action.".format(defs["repo"]))
    
    if "-j" in args:
        m.make_jobs_DSL(defs["lab"])         # Concatenate components of DSL into valid file

    
    if "-n" in args:
        m.notify_all(defs["repo"])              # Notification for repo distribution

    if "-g" in args:
        if m.is_assigned(defs["repo"]):
            m.get_repos(defs["repo"])               # Get github repos
        else:
            print("You must distribute the repo {} before performing this action.".format(defs["repo"]))

    if "-m" in args:
        if m.is_assigned(defs["repo"]):
            if defs["repo"] == "lab1":
                grader.main(defs["repo"])               # Grade with spimgrader
            else:
                graderII.main(defs["repo"])
        else:
            print("You must distribute the repo {} before performing this action.".format(defs["repo"]))

    if "-c" in args:
        if m.is_assigned(defs["repo"]):
            moss.submit(defs["repo"], archives=defs["archives"])    # Submit to Moss
        else:
            print("You must distribute the repo {} before performing this action.".format(defs["repo"]))

    if "-x" in args:
        print "THIS WILL CLEAR THE REMOTE REPOS FOR {}.".format(defs["repo"])
        confirm = (raw_input("Are you sure? [y/n]: ")[0].lower() == 'y')
        if confirm:
            m.del_git_repos()     # remove local repos

    if "-X" in args:
        print "THIS WILL CLEAR ALL TEAM REPOS & TEAMS FROM GitHub."
        confirm = (raw_input("Are you sure? [y/n]: ")[0].lower() == 'y')
        if confirm:
            m.del_git_repos()                   # remove remote repos
            m.del_git_teams()                   # remove remote teams

    
    # For automated testing.
    if "-Q" in args:
        m.del_git_repos()                   # remove remote repos
        m.del_git_teams()                   # remove remote teams

    return

if __name__ == "__main__":
    main()
