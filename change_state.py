#!/usr/bin/python

"""
Bulk transitions the state of Ship problems described by a query, predicate, or list
to a specified new state.
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
    
  real_raw_input = vars(__builtins__).get('raw_input',input)
  while True:
    ans = real_raw_input(msg)
    if not ans:
      return resp
    if ans not in ['y', 'Y', 'n', 'N']:
      print('please enter y or n.')
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
  parser = argparse.ArgumentParser(description=globals()["__doc__"], epilog="Exactly one of --srcquery, --srcproblems, or --srcpredicate is required")
  
  parser.add_argument("--apitoken", help="Ship API Key (if omitted, will be read from environment variable SHIP_API_TOKEN)")
  
  parser.add_argument("--srcquery", help="Ship URL to a saved query describing problems (e.g. ship://Query/UYnF8JlyQp2IQrqTBiCP7A)")
  parser.add_argument("--srcproblems", help="Ship URL to a list of problems (e.g. ship://Problems/349&563&31&127&562&404&561)")
  parser.add_argument("--srcpredicate", help="NSPredicate formatted query matching a set of problems (e.g. \"assignee.name == 'James Howard'\")")
  
  parser.add_argument("--state", help="Name of the state to transition the problems to. Required.")
  
  interactive = sys.__stdin__.isatty()
  
  args = parser.parse_args()
  
  api = shippy.Api(token=args.apitoken, dry_run=False)
  if not api.token:
    sys.stderr.write("Could not locate Ship API token\n\n")
    parser.print_help()
    sys.exit(1)
  
  if not (args.srcquery or args.srcproblems or args.srcpredicate):
    parser.print_help()
    sys.exit(1)

  if not (args.state):
    parser.print_help()
    sys.exit(1)
  
  try:
    api.me()
  except:
    traceback.print_exc()
    sys.stderr.write("\n\nUnable to connect to Ship API (check your token and network settings)")
    sys.exit(1)
  
  problems = None
  
  state = None
  stateName = None
  states = api.states("name = '%s'" % args.state)
  if len(states) == 0:
    sys.stderr.write("State \"%s\" doesn't exist\n" % args.state)
    sys.exit(1)
  else:
    state = states[0]
    stateName = state["name"]
  
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
    
    predicate = "identifier IN {%s}" % (", ".join([str(p) for p in problemIDs]))
    
    problems = api.problem_search(predicate=predicate)
  elif args.srcpredicate:
    try:
      problems = api.problem_search(predicate=args.srcpredicate)
    except:
      traceback.print_exc()
      sys.stderr.write("\n\nInvalid predicate?")
      sys.exit(1)
  
  if interactive:
    print("Query returned %d problems:" % len(problems))
    for p in problems:
      print("%d\t%s\t%s" % (p["identifier"], p["state"]["name"], p["title"]))
    print("\nOpen in Ship (select and context click -> Open URL): ship://Problems/%s\n" % ("&".join([str(p["identifier"]) for p in problems])))
    if not prompt("OK to proceed transitions these problems to state \"%s\"?" % stateName):
      sys.exit(1)
  
  skipped = 0
  updated = 0
  for p in problems:
    if p["state"]["name"] == stateName:
      skipped += 1
      continue
    api.problem_update(p["identifier"], { "state": state })
    updated += 1
  
  print("Processed %d problems. Set state of %d problems to \"%s\" (skipped %d already in that state)" % (len(problems), updated, stateName, skipped))
