# Articulations must support:
#   The basics: source and destination taxa, and an RCC-5 (or similar) relation
#   A comment explaining the reason the articulation might be true
#   Reversal
#   Composition
#   Disjunction ??

import collections
import relation as rel
import checklist as cl
import property
import diff

# Articulations

Articulation = \
  collections.namedtuple('Articulation',
                         ['dom', 'cod', 'relation', 'factors', 'reason', 'diff'])

def _articulation(dom, cod, re, factors = None, reason = None):
  assert dom > 0
  assert cod > 0
  assert re
  assert re.name
  dif = diff.all_diffs
  if cl.is_accepted(dom) and cl.is_accepted(cod):
    dif = diff.differences(dom, cod)
  if factors == None: factors = []
  assert isinstance(factors, list)
  ar = Articulation(dom, cod, re, factors, reason, dif)
  if len(factors) == 0: factors.append(ar)
  return ar

def express(ar):
  return "%s %s %s" % (cl.get_unique(ar.dom),
                       ar.relation.name,
                       cl.get_unique(ar.cod))

def compose(p, q):
  if not composable(p, q):
    print("** Not composable:\n  %s &\n  %s" %
          (express(p), express(q)))
    assert False
  if is_identity(p): return q
  if is_identity(q): return p
  return _articulation(p.dom,
                       q.cod,
                       rel.compose(p.relation, q.relation),
                       p.factors + q.factors,
                       p.reason + "+" + q.reason)

def composable(p, q):
  return (p.cod == q.dom and
          rel.composable(p.relation, q.relation))

def conjoin(p, q):
  if not conjoinable(p, q):
    print("** Not conjoinable:\n  %s &\n  %s" %
          (express(p), express(q)))
    assert False
  return p                      # ???

def conjoinable(p, q):
  return (p.dom == q.dom and
          p.cod == q.cod and
          rel.conjoinable(p.relation, q.relation))

def get_comment(art):
  return art.relation.name

def reverse(art):
  f = list(reversed(art.factors))
  return _articulation(art.cod, art.dom, rel.reverse(art.relation), f,
                       art.reason)    # Reason

def is_identity(art):
  return art.dom == art.cod and art.relation == rel.eq

def inverses(ar1, ar2):
  return (ar1.cod == ar2.dom and 
          ar1.dom == ar2.cod and 
          rel.inverses(ar1.relation, ar2.relation))

# ---------- Synonymy relationship within one tree

def synonymy(synonym, accepted):
  assert synonym > 0
  assert accepted > 0
  status = (cl.get_nomenclatural_status(synonym) or \
            cl.get_taxonomic_status(synonym) or \
            "synonym")
  re = synonym_relation(status)
  return _articulation(synonym, accepted, re,
                       reason="synonym")

# I don't understand this

def synonym_relation(nom_status):
  if nom_status == None:
    return rel.eq
  re = synonym_relations.get(nom_status)
  if re: return re
  print("Unrecognized nomenclatural status: %s" % nom_status)
  return rel.reverse(rel.eq)    # foo

# These relations go from synonym to accepted (the "has x" form)
# TBD: Put these back into the articulation somehow

synonym_relations = {}

def declare_synonym_relations():

  def b(nstatus, rcc5 = rel.eq, name = None, revname = None, relation = rel.eq):
    if False:
      if name == None: name = "has-" + nstatus.replace(" ", "-")
      if revname == None: revname = nstatus.replace(" ", "-") + "-of"
    re = rel.reverse(rcc5)
    synonym_relations[nstatus] = re
    return re

  b("homotypic synonym")    # GBIF
  b("authority")
  b("scientific name")        # (actually canonical) exactly one per node
  b("equivalent name")        # synonym but not nomenclaturally
  b("misspelling")
  b("unpublished name")    # non-code synonym
  b("genbank synonym")        # at most one per node; first among equals
  b("anamorph")
  b("genbank anamorph")    # at most one per node
  b("teleomorph")
  b("acronym")
  b("blast name")             # large well-known taxa
  b("genbank acronym")      # at most one per node
  b("BOLD id")

  # More dubious
  synonym = b("synonym")
  b("heterotypic synonym")      # GBIF
  b("misnomer")
  b("type material")
  b("merged id", revname = "split id")    # ?
  b("accepted")    # EOL
  b("invalid")     # EOL

  # Really dubious
  b("genbank common name")    # at most one per node
  b("common name")

  b("includes", rcc5=rel.gt, name="part-of", revname="included-in")
  b("in-part",  rcc5=rel.lt, name="included-in", revname="part-of")  # part of a polyphyly
  b("proparte synonym", rcc5=rel.lt)

declare_synonym_relations()

# ---------- Different kinds of articulation

def extensional(dom, cod, re, reason):
  return bridge(dom, cod, re, reason)

def monotypic(dom, cod, re):
  return bridge(dom, cod, re, "monotypic")

def intensional(dom, cod):
  return bridge(dom, cod, rel.eq, "name")

def bridge(dom, cod, re, reason):
  assert cl.get_checklist(dom) != cl.get_checklist(cod)
  return _articulation(dom, cod, re, reason=reason)

# ---------- Utility: collapsing a set of matches

# Reduce a set of articulations grouped first by RCC5 relation, then
# within each group, collapsed (conjoined) so that the codomains are
# all different.

def collapse_matches(arts):
  if len(arts) <= 1: return arts
  arts = sorted(arts, key=conjoin_sort_key)
  previous = None
  matches = []
  for ar in arts:
    if not previous:
      previous = ar
    elif conjoinable(previous, ar):
      previous = conjoin(previous, ar)
    else:
      matches.append(previous)
      previous = None
  if previous:
    matches.append(previous)
  assert len(matches) <= len(arts)
  return matches

# This one is for deduplication (grouping by codomain)

def conjoin_sort_key(ar):
  assert ar.dom
  return (rel.sort_key(ar.relation),
          ar.cod)

# ---------- This one is for tie breaking (when codomains differ)

# Less-bad articulations first.

def badness(ar):
  (drop, change, add) = ar.diff
  return(
         rel.sort_key(ar.relation),     # '=' sorts earliest
         # Changes are bad
         # Low-bit changes are better than high-bit changes
         # Additions don't matter
         change,
         drop,
         # Using synonym is bad, using two is worse
         len(ar.factors),
         # Added fields are benign
         # Dropped fields are so-so
         # What is this about?
         cl.get_mutex(ar.cod))

def sort_matches(arts):
  return sorted(arts, key=badness)
