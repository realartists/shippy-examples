#!/usr/bin/env python

"""Uses the Ship API to find open problems that are blocked by other open problems"""

import sys
import shippy
import argparse
import subprocess

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description=globals()["__doc__"])
  parser.add_argument("--apitoken", help="Ship API Key (if omitted, will be read from environment variable SHIP_API_TOKEN)")
  
  args = parser.parse_args()
  api = shippy.Api(token=args.apitoken, dry_run=False)
  
  try:
    api.me()
  except:
    sys.stderr.write("Unable to connect to the Ship API. Double check your API token\n\n")
    parser.print_usage()
    sys.exit(1)
  
#   Relationship Types to int codes: 
#
#   RelatedTo = 100,
# 
#   ParentOf = 200,
#   ChildOf = 201,
# 
#   OriginalOf = 300,
#   DuplicateOf = 301,
# 
#   CauseOf = 400,
#   CausedBy = 401,
# 
#   BlockerOf = 500,
#   BlockedBy = 501,
# 
#   ClonedTo = 600,
#   ClonedFrom = 601,
  
  query = """state.resolved = NO AND SUBQUERY(relationships, $r, $r.type = 501 AND $r.ParentId = Id AND $r.child.state.resolved = NO).@count > 0"""
  
  blocked = api.problem_search(query)
  
  URL = "ship://%s" % "&".join([str(p["identifier"]) for p in blocked])
  
  print URL
  subprocess.call("open -a Ship '%s'" % URL, shell=True)

  
    