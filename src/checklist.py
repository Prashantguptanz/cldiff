debug = False

import os, csv

import relation as rel
import rank
import chaitin
import property
import table

# ---------- Fields (columns, properties) in taxon table

# Particular fields of interest here (not all possible DwC fields)

def field(label):
  sel = property.by_name(label)
  assert sel
  return sel

nomenclatural_status = field("nomenclaturalStatus")
taxonomic_status     = field("taxonomicStatus")    # flush?
taxon_rank           = field("taxonRank")
parent_node_id    = field("parentNameUsageID")
node_id           = field("taxonID")
accepted_node_id  = field("acceptedNameUsageID")
canonical_name       = field("canonicalName")
scientific_name      = field("scientificName")

# ---------- Taxon registry and taxa

forest_tnu = 0

# Get the value of a field of a TNU record (via global registry)

def get_value(uid, field):
  assert field
  if uid == forest_tnu: return None
  return table.get_value(uid, field)

def get_checklist(uid):
  assert uid > 0
  return table.get_table(uid)

# ---------- Checklists

class Checklist(table.Table):
  def __init__(self, prefix, name):
    super().__init__()
    assert prefix
    self.prefix = prefix
    self.name = name    # not used?
    self.sequence_numbers = {}

  def get_all_nodes(self):
    return self.record_uids

  def tnu_count(self):
    return len(self.record_uids)

  def assign_sequence_numbers(self):
    n = len(self.sequence_numbers)    # dict
    def process(tnu, n):
      self.sequence_numbers[tnu] = n
      n = n + 1
      for inf in get_inferiors(tnu):
        n = process(inf, n)
      return n
    for root in get_roots(self):
      n = process(root, n)

# Sequence number within this checklist

def get_sequence_number(uid):
  return get_checklist(uid).sequence_numbers[uid]

# Read a checklist from a file

def read_checklist(specifier, prefix, name):
  assert prefix
  checklist = Checklist(prefix, name)
  if specifier.endswith(')'):
    checklist.populate_from_generator(chaitin.parse(specifier))
  else:
    checklist.populate_from_file(specifier)

  assert checklist.get_position(canonical_name) != None
  if checklist.get_position(node_id) == None:
    print (checklist.header())
    assert False

  checklist.assign_sequence_numbers()

  return checklist

# Utility - copied from another file - really ought to be shared
# Is this used?  Could be

def get_nodes_file_path(dwca_dir):
  for name in ["taxon.tsv",
               "Taxon.tsv",
               "taxon.tab",
               "Taxon.tab",
               "taxa.txt",
               "taxon.txt",
               "Taxon.txt"]:
    path = os.path.join(dwca_dir, name)
    if os.path.exists(path):
      return path
  raise ValueError("cannot find taxon file in this directory", dwca_dir)

# -------------------- indexing

# Get taxon records in checklist having a particular value in some column

canonical_empty_list = []

def get_nodes_with_value(checklist, field, value):
  return checklist.get_index(field).get(value, canonical_empty_list)

# Get unique (we hope) taxon record possessing a given identifier
# Can return None

def get_node_id(tnu):
  return get_value(tnu, node_id)

def get_record_with_node_id(checklist, id):
  records = checklist.get_index(node_id).get(id, None)
  if records:
    return records[0]
  else:
    return None
  return get_value(tnu, node_id)

# ----------------------------------------

# Logic for particular fields

# The following is for display purposes

def get_name(tnu):
  name = get_value(tnu, canonical_name)
  if name != None: return name
  name = get_value(tnu, scientific_name)
  if name != None: return name  
  return get_node_id(tnu)

def get_nominal_rank(tnu):
  if is_container(tnu): return None
  return get_value(tnu, taxon_rank)

# Unique name of the sort Nico likes

def get_spaceless(tnu):
  if tnu == None: return "none"
  if tnu == forest_tnu: return "forest"
  assert table.is_record(tnu)
  checklist = get_checklist(tnu)
  name = get_name(tnu)

  tnus_with_this_name = \
    get_nodes_with_value(checklist, canonical_name, name)
  if len(tnus_with_this_name) > 1:
    # TBD: what if id is None?  Use id of accepted?
    name = name + "#" + get_node_id(tnu)

  if not is_accepted(tnu):
    name = "?" + name

  name = name.replace(" ", "_")
  return name

def get_unique(tnu):
  if tnu:
    return get_checklist(tnu).prefix + get_spaceless(tnu)
  else:
    return get_spaceless(tnu)

# Roots - accepted tnus without parents

def get_roots(checklist):
  roots = []
  for tnu in checklist.get_all_nodes():
    assert tnu > 0
    if to_accepted(tnu) == tnu and get_parent(tnu) == forest_tnu:
      roots.append(tnu)
  return roots

# Superior/inferior

def get_inferiors(tnu):
  assert table.is_record(tnu)
  assert tnu != forest_tnu
  return get_synonyms(tnu) + get_children(tnu)

# ----------
# Parent/children and accepted/synonyms

def get_parent(tnu):
  assert tnu > 0
  # There are two checks here, and if the order of the checks matters,
  # the input checklist is ill-formed
  parent_id = get_value(tnu, parent_node_id)
  if parent_id != None:
    parent = get_record_with_node_id(get_checklist(tnu), parent_id)
    if parent != None:
      return to_accepted(parent)
  probe = get_accepted(tnu)
  if probe != None:
    return get_direct_parent(probe)
  else:
    return forest_tnu

def get_direct_parent(tnu):
  assert tnu > 0
  # There are two checks here, and if the order of the checks matters,
  # the input checklist is ill-formed
  parent_id = get_value(tnu, parent_node_id)
  if parent_id != None:
    parent = get_record_with_node_id(get_checklist(tnu), parent_id)
    if parent != None:
      return to_accepted(parent)
  return None

def get_children(parent):
  return get_nodes_with_value(get_checklist(parent),
                                 parent_node_id,
                                 get_node_id(parent))

# Get canonical record among a set of equivalent records

def to_accepted(tnu):
  if not table.is_record(tnu):
    print ("Not a record: %s" % tnu)
    assert False
  probe = get_accepted(tnu)
  if probe:
    return probe
  else:
    return tnu

# ----------
# Accepted/synonyms

# Returns None if this record has no accepted record

def get_accepted(tnu):
  probe = get_value(tnu, accepted_node_id)
  if probe != None:
    return get_record_with_node_id(get_checklist(tnu), probe)
  return None

def get_synonyms(tnu):
  return [syn
          for syn in get_nodes_with_value(get_checklist(tnu),
                                             accepted_node_id,
                                             get_node_id(tnu))]

def get_taxonomic_status(tnu):
  return get_value(tnu, taxonomic_status)

def get_nomenclatural_status(tnu):
  return get_value(tnu, nomenclatural_status)

def is_accepted(tnu):
  return not get_value(tnu, accepted_node_id)

# ---------- Hierarchy analyzers

def how_related(tnu1, tnu2):
  if tnu1 == tnu2:
    # If in differently checklists, this could be an incompatibility
    return rel.eq
  assert table.is_record(tnu1)
  assert table.is_record(tnu2)
  assert get_checklist(tnu1) == get_checklist(tnu2)
  (peer1, peer2) = find_peers(tnu1, tnu2)  
  if peer1 == peer2:
    if peer1 == tnu1:
      return rel.gt
    elif peer2 == tnu2:
      return rel.lt
  return rel.disjoint

def are_disjoint(tnu1, tnu2):
  assert table.is_record(tnu1)
  assert table.is_record(tnu2)
  if tnu1 == forest_tnu: return False
  if tnu2 == forest_tnu: return False
  if tnu1 == tnu2: return False
  (tnu1, tnu2) = find_peers(tnu1, tnu2)
  return tnu1 != tnu2

# Find ancestor(s) of tnu1 and/or tnu2 that are in the same mutex: either
# disjoint or equal.

def find_peers(tnu_1, tnu_2):
  assert table.is_record(tnu_1)
  assert table.is_record(tnu_2)

  tnu1 = to_accepted(tnu_1)
  tnu2 = to_accepted(tnu_2)

  if tnu1 == forest_tnu or tnu2 == forest_tnu:
    return (forest_tnu, forest_tnu)
  assert get_checklist(tnu1) == get_checklist(tnu2)  #?

  mutex1 = get_mutex(tnu1)
  mutex2 = get_mutex(tnu2)

  if mutex1 == mutex2:
    if debug:
      print ("# Kludge %s %s" % (get_unique(tnu1), get_unique(tnu2)))
    tnu1 = get_parent(tnu1)
    mutex1 = get_mutex(tnu1)    

  #print("# Mutexes are %s %s" % (mutex1, mutex2))
  # Mutex of the forest is 0.  Going in 0-ward direction.

  while mutex1 != mutex2:
    assert mutex1 >= 0
    assert mutex2 >= 0
    if mutex1 > mutex2:
      # If p2 is closer to the root, try going rootward from p1
      if tnu1 == forest_tnu: return (forest_tnu, forest_tnu)
      tnu1 = get_parent(tnu1)
      mutex1 = get_mutex(tnu1)
    else: # mutex1 < mutex2:
      # If p1 is closer to the root, try going rootward from p2
      if tnu2 == forest_tnu: return (forest_tnu, forest_tnu)
      tnu2 = get_parent(tnu2)
      mutex2 = get_mutex(tnu2)

  if debug:
   print("# find_peers(%s, %s) = %s, %s" % \
        (get_unique(tnu_1), get_unique(tnu_2), 
         get_unique(tnu1), get_unique(tnu2)))
  return (tnu1, tnu2)

# Common ancestor - utility
# Also computes number of matched tips
# None (not 0) is the identity for mrca

def mrca(tnu1, tnu2):
  while True:
    if tnu1 == forest_tnu: return forest_tnu
    if tnu2 == forest_tnu: return forest_tnu
    assert table.is_record(tnu1)
    assert table.is_record(tnu2)
    # to_accepted ??
    if tnu1 == tnu2: return tnu1
    (tnu1, tnu2) = find_peers(tnu1, tnu2)
    assert get_mutex(tnu1) == get_mutex(tnu2)

mutex_table = {}

def set_mutex(tnu, mutex):
  have = mutex_table.get(tnu, mutex)
  if have != mutex:
    verb = "Promoting" if have > mutex else "Demoting"
    print("# ** %s %s, %s -> %s" % \
          (verb, get_unique(tnu),
           rank.mutex_to_name(have),
           rank.mutex_to_name(mutex)))
  mutex_table[tnu] = mutex

def get_mutex(tnu):
  if not tnu:
    # Above root of tree = forest_tnu
    return rank.forest
  probe = mutex_table.get(tnu)
  if probe: return probe
  mutex = get_mutex_really(tnu)
  assert mutex >= 0
  mutex_table[tnu] = mutex    # Perhaps amended later
  return mutex

# Higher numbers are more tipward.
# Parent's level > child's level for all children.

def get_mutex_really(tnu):
  tnu = to_accepted(tnu)

  # Findest most rootward mutex of all the children
  children_mutex = rank.atom     # identity for min
  for child in get_children(tnu):
    children_mutex = min(children_mutex, get_mutex(child))

  # Treat given rank, if any, as normative
  if get_parent(tnu) == forest_tnu:
    mutex = rank.root
  else:
    nominal = get_nominal_mutex(tnu)
    mutex = nominal or (children_mutex - 10)
  set_mutex(tnu, mutex)

  # Demote children that have higher rank
  correct_children_mutexes(tnu, mutex)

  return mutex

def correct_children_mutexes(parent, parent_mutex):
  for child in get_children(parent):
    child_mutex = get_mutex(child)
    if child_mutex <= parent_mutex:
      if child_mutex == parent_mutex:
        print("# ** Child %s has same rank as parent %s" % \
              (get_unique(child), get_unique(parent)))
      else:
        print("# ** Child %s is of higher rank than parent %s" %\
              (get_unique(child), get_unique(parent)))
      if is_container(child):
        new_mutex = parent_mutex + 1 # demote!
        set_mutex(child, new_mutex)
        correct_children_mutexes(child, new_mutex) # ?
      else:
        set_mutex(child, parent_mutex + 10)  # demote!

def get_nominal_mutex(tnu):
  nominal = get_nominal_rank(tnu) # name of rank
  return rank.name_to_mutex(nominal)

def is_container(tnu):
  name = get_name(tnu).lower()
  return "unclassified" in name or \
         "incertae sedis" in name or \
         "unallocated" in name or \
         "unassigned" in name
  
# ---------- Approximate lookup

def get_similar_records(checklist, record, shared_idspace=False):
  assert record > 0
  assert get_checklist(record) != checklist
  # TBD: search on scientific_name epithet, etc. as well
  hits = get_nodes_with_value(checklist,
                                 canonical_name,
                                 get_name(record))
  if shared_idspace:
    id_hit = get_record_with_node_id(checklist, get_node_id(record))
    if id_hit and not id_hit in hits:
      hits = hits + [id_hit]
  return hits

# ---------- General utility that doesn't really belong here

def invert_dict(d):
  inv = {}
  for (key, val) in d.items():
    if val in inv:
      inv[val].append(key)
    else:
      inv[val] = [key]
  return inv

# Test

def self_test():
  checklist = read_checklist("work/ncbi/2020-01-01/primates.csv", "A.", "name")
  print ("Nodes:", len(checklist.get_all_nodes()))
  print ("Roots:", get_roots(checklist))
  tnus = checklist.get_index(taxon_id)
  tnu = get_record_with_node_id(checklist, '9455')
  print ("Specimen tnu:", tnu)
  print ("Name:", get_name(tnu))
  synos = get_synonyms(tnu)
  print ("Synonyms:", list(map(get_taxon_id, synos)))
  print ("Back atcha:", [get_accepted(syno) for syno in synos])

if __name__ == '__main__':
  self_test()
