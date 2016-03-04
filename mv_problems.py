#!/usr/bin/python

"""
Bulk moves open Ship problems described by a query, predicate, or a milestone
to a destination milestone.
"""

import sys
import argparse
import traceback

def prompt(msg=None, resp=False):
  if msg is None:
    msg = 'Confirm'

  if resp:
    msg = '%s [%s]|%s: ' % (msg, 'y', 'n')
  else:
    msg = '%s [%s]|%s: ' % (msg, 'n', 'y')
    
  while True:
    ans = raw_input(msg)
    if not ans:
      return resp
    if ans not in ['y', 'Y', 'n', 'N']:
      print 'please enter y or n.'
      continue
    if ans == 'y' or ans == 'Y':
      return True
    if ans == 'n' or ans == 'N':
      return False

try:
  import shippy
except:
  sys.stderr.write("""Ship python API module 'shippy' is required.
If you have pip:
  sudo pip install shippy
  
If you don't have pip:
  sudo easy_install pip && sudo pip install shippy
  
See https://www.realartists.com/docs/api/python.html for more information. 
""")
  sys.exit(1)



if __name__ == "__main__":
  parser = argparse.ArgumentParser(description=globals()["__doc__"], epilog="Exactly one of --srcquery, --srcproblems, --srcpredicate, or --srcmilestone is required")
  
  parser.add_argument("--apitoken", help="Ship API Key (if omitted, will be read from environment variable SHIP_API_TOKEN)")
  
  parser.add_argument("--srcquery", help="Ship URL to a saved query describing problems (e.g. ship://Query/UYnF8JlyQp2IQrqTBiCP7A)")
  parser.add_argument("--srcproblems", help="Ship URL to a list of problems (e.g. ship://Problems/349&563&31&127&562&404&561)")
  parser.add_argument("--srcpredicate", help="NSPredicate formatted query matching a set of problems (e.g. \"assignee.name == 'James Howard'\")")
  parser.add_argument("--srcmilestone", help="Name of a Ship milestone (e.g. Future)")
  
  parser.add_argument("--dstmilestone", help="Name of the milestone to move the problems to (e.g. Next). If omitted, problems will be moved to the Backlog")
  
  interactive = sys.__stdin__.isatty()
  
  args = parser.parse_args()
  
  api = shippy.Api(token=args.apitoken, dry_run=False)
  if not api.token:
    sys.stderr.write("Could not locate Ship API token\n\n")
    parser.print_help()
    sys.exit(1)
  
  if not (args.srcquery or args.srcproblems or args.srcpredicate or args.srcmilestone):
    parser.print_help()
    sys.exit(1)
  
  try:
    api.me()
  except:
    traceback.print_exc()
    sys.stderr.write("\n\nUnable to connect to Ship API (check your token and network settings)")
    sys.exit(1)
  
  problems = None
  
  milestone = None
  milestoneName = args.dstmilestone
  if not milestoneName:
    milestoneName = "Backlog"
  
  if args.dstmilestone:
    milestones = api.milestones("name = '%s'" % args.dstmilestone)
    if len(milestones) == 0:
      sys.stderr.write("Milestone \"%s\" doesn't exist\n" % args.dstmilestone)
      if interactive:
        if prompt("Do you want to create it?"):
          data = { "name": args.dstmilestone }
          milestone = api._post("milestones", json=data).json()
        else:
          sys.exit(1)
      else:
        sys.exit(1)
    else:
      milestone = milestones[0]
  
  if args.srcquery:
    problems = api.problem_search(savedQueryURL=args.srcquery)
  elif args.srcproblems:
    x = args.srcproblems
    if x.startswith("ship://Problems/"):
      x = x.replace("ship://Problems/", "")
    elif x.startswith("ship://"):
      x = x.replace("ship://", "")
    else:
      sys.stderr.write("--srcproblems value doesn't look like a Ship problems URL")
      sys.exit(1)
    
    try:
      problemIDs = [int(p) for p in x.split("&")]
    except:
      sys.stderr.write("--srcproblems value doesn't look like a Ship problems URL")
      sys.exit(1)
    
    predicate = "state.resolved = NO AND identifier IN {%s}" % (", ".join([str(p) for p in problemIDs]))
    
    problems = api.problem_search(predicate=predicate)
  elif args.srcpredicate:
    try:
      problems = api.problem_search(predicate=args.srcpredicate)
    except:
      traceback.print_exc()
      sys.stderr.write("\n\nInvalid predicate?")
      sys.exit(1)
  elif args.srcmilestone:
    predicate = "state.resolved = NO AND milestone.name =[c] '%s'" % args.srcmilestone
    problems = api.problem_search(predicate=predicate)
  
  problems = [p for p in problems if p["state"]["resolved"] == False]
  
  if interactive:
    print("Query returned %d open problems:" % len(problems))
    for p in problems:
      print("%d\t%s" % (p["identifier"], p["title"]))
    print("\nOpen in Ship (select and context click -> Open URL): ship://Problems/%s\n" % ("&".join([str(p["identifier"]) for p in problems])))
    if not prompt("OK to proceed moving these problems to \"%s\"?" % milestoneName):
      sys.exit(1)
  
  skipped = 0
  moved = 0
  for p in problems:
    if milestone is None and (not "milestone" in p or p["milestone"] is None):
      skipped += 1
      continue
    elif milestone is not None and "milestone" in p and p["milestone"] is not None and p["milestone"]["identifier"] == milestone["identifier"]:
      skipped += 1
      continue
    api.problem_update(p["identifier"], { "milestone": milestone })
    moved += 1
  
  print("Processed %d problems. Moved %d problems to \"%s\" (skipped %d already there)" % (len(problems), moved, milestoneName, skipped))
