#!/bin/env python3

debug = False

import sys, csv
import argparse

import checklist as cl
import relation as rel
import articulation as art
import eulerx
import alignment
import diff
import merge

# A is lower priority, B is higher

def main(c1, c1_tag, c2, c2_tag, share_ids, out, format):
  A = cl.read_checklist(c1, c1_tag + ".", "left-checklist")
  B = cl.read_checklist(c2, c2_tag + ".", "right-checklist")
  print ("Node counts:", len(A.get_all_nodes()), len(B.get_all_nodes()))
  write_report(A, B, share_ids, format, out)

def write_report(A, B, share_ids, format, outpath):
  if outpath == "-":
    really_write_report(A, B, format, sys.stdout)
  else:
    with open(outpath, "w") as outfile:
      print ("Preparing:", outpath)
      really_write_report(A, B, format, outfile)

def really_write_report(A, B, format, outfile):
  # Map each B to a corresponding A
  (al, xmrcas) = alignment.align(B, A)
  # Where to xmrcas come from?

  if format == "eulerx":
    eulerx.dump_alignment(al, outfile)
  else:
    (parents, roots) = merge.merge_checklists(A, B, al, xmrcas)
    print ("# Number of roots in merge: %s" % len(roots))
    print ("# Number of non-roots in merge: %s" % len(parents))
    report(A, B, al, roots, parents, outfile)

# Default (simplified) report format

def report(A, B, al, roots, parents, outfile):
  inv = invert_alignment(al)
  writer = csv.writer(outfile)
  writer.writerow(["indent", "operation", "dom", "dom id", "relation", "cod id", "cod", "unchanged", "changed_props", "reason"])
  children = cl.invert_dict(parents)
  all_props = set.intersection(set(A.properties), set(B.properties))
  changed = find_changed_merged_subtrees(roots, children, all_props)
  def process(mnode, indent):
    (x, y) = mnode
    childs = children.get(mnode, [])
    re = None
    d = None
    reason = None
    if x and y:
      op = "KEEP"
      comparison = diff.differences(x, y, all_props)
      if not diff.same(comparison):
        props = diff.unpack(comparison)
        d = ("; ".join(map(lambda x:x.pet_name, props)))
      reason = al[x].reason
    elif x:
      op = "DELETE"
      ar = al.get(x)
      if ar:
        re = ar.relation.name
        # Equivalence, usually, but sometimes not
        y = ar.cod

        if rel.is_variant(ar.relation, rel.eq):
          op += " (merge)"
        elif rel.is_variant(ar.relation, rel.conflict):
          op += " (conflict)"
        elif rel.is_variant(ar.relation, rel.lt):
          op += " (loss of resolution)"
    else:                       # y
      op = "ADD"
      ar = al.get(y)
      if ar:
        re = ar.relation.revname
        x = ar.cod
        if rel.is_variant(ar.relation, rel.eq):
          op += " (split)"
        elif rel.is_variant(ar.relation, rel.conflict):
          op += " (reorganization)"
        elif rel.is_variant(ar.relation, rel.lt):
          op += " (increased resolution)"

    status = changed.get(mnode)
    ch = None
    if not status and len(childs) > 0:
      ch = "subtree="

    report_one_articulation(op, ch, d, x, re, y, reason, writer, indent)
    jndent = indent + "__"
    if status:
      for child in childs:
        process(child, jndent)
  for root in roots:
    process(root, "")

def report_one_articulation(op, ch, d, x, re, y, reason, writer, indent):
  ux = None
  ix = None
  uy = None
  iy = None
  if x:
    ux = cl.get_unique(x)
    ix = cl.get_node_id(x)
  if y:
    uy = cl.get_unique(y)
    iy = cl.get_node_id(y)
  writer.writerow([indent, op,
                   ux, ix, re,
                   iy, uy, ch, d, reason])

# --------------------
# utilities

def invert_alignment(alignment):
  inv = {}
  for ar in alignment.values():
    rev = art.reverse(ar)
    if rev.dom in inv:
      inv[rev.dom].append(rev)
    else:
      inv[rev.dom] = [rev]
  return inv

# Returns table with True for merged nodes all of whose descendants are
# unchanged

def find_changed_merged_subtrees(roots, children, all_props):
  status = {}
  def process(node):
    node_changed = False
    (x, y) = node
    if not x or not y:
      node_changed = True
    else:
      comparison = diff.differences(x, y, all_props)
      if not diff.same(comparison):
        node_changed = True
    descendant_changed = False
    for child in children.get(node, []):
      if process(child):
        descendant_changed = True
    status[node] = descendant_changed       # Cache it
    return descendant_changed or node_changed
  for root in roots:
    status[root] = process(root)
  count = 0
  for key in status:
    if status[key]: count += 1
  print("# Changed status: %s, changed: %s" % (len(status), count))
  return status

# --------------------

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('left', help='A checklist')    # Lower priority
  parser.add_argument('right', help='B checklist')   # Higher priority
  parser.add_argument('--left-tag', default="A")
  parser.add_argument('--right-tag', default="B")
  parser.add_argument('--share_ids', default=False)
  parser.add_argument('--out', help='file name for report', default='diff.csv')
  parser.add_argument('--format', help='report format', default='ad-hoc')
  args = parser.parse_args()
  alignment.shared_idspace = args.share_ids
  main(args.left, args.left_tag, args.right, args.right_tag,
       args.share_ids, args.out, args.format)

