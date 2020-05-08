# Read and write Euler/X notation

"""
# Franz et al. 2014. Taxonomic Provenance: Two Influential Primate 
# Classifications Logically Aligned. Systematic Biology. (In Review)
# Figure 1
# Euler/X command - input visualization: euler -i figure1.txt --iv
# Euler/X command - alignment: euler -i figure1.txt -e mnpw --rcgo

taxonomy 2005 Groves_MSW3
(Microcebus Microcebus_berthae Microcebus_griseorufus Microcebus_murinus Microcebus_myoxinus Microcebus_ravelobensis Microcebus_rufus Microcebus_sambiranensis Microcebus_tavaratra)
(Mirza Mirza_coquereli)

taxonomy 1993 Groves_MSW2
(Microcebus Microcebus_coquereli Microcebus_murinus Microcebus_rufus)

articulation 2005-1993 Groves_MSW3-Groves_MSW2
[2005.Microcebus_berthae ! 1993.Microcebus]
[2005.Microcebus_griseorufus < 1993.Microcebus_murinus]
[2005.Microcebus_murinus < 1993.Microcebus_murinus]
[2005.Microcebus_myoxinus < 1993.Microcebus_murinus]
[2005.Microcebus_ravelobensis ! 1993.Microcebus]
[2005.Microcebus_rufus = 1993.Microcebus_rufus]
[2005.Microcebus_sambiranensis ! 1993.Microcebus]
[2005.Microcebus_tavaratra ! 1993.Microcebus]
[2005.Mirza_coquereli = 1993.Microcebus_coquereli]
"""

import sys
import io
import argparse
import checklist as cl
import relation as rel

def load(s, prefix = ""):
  ch = cl.Checklist(prefix)
  assert False
  return ch

def dump(ch, out):
  def process(node):
    children = cl.get_children(node)
    if children:
      if not cl.is_container(node):
        out.write("(%s" % cl.get_spaceless(node))
        for child in children:
          out.write(" %s" % cl.get_spaceless(child))
        out.write(")\n")
      for child in children:
        process(child)
  out.write("taxonomy %s %s\n" % (ch.prefix, ch.name.replace(" ", "_")))
  for root in cl.get_roots(ch):
    process(root)
  out.write("\n")

def dump_alignment(alignment, out):
  for key in alignment:
    look = alignment[key]
    break
  out.write("articulation %s %s" % \
            (cl.get_checklist(look.dom).name,
             cl.get_checklist(look.cod).name))
  def sort_key(a):
    p = cl.get_parent(a.dom)
    return (cl.get_sequence_number(p) if p else 0,
            cl.get_sequence_number(a.cod))
  for arts in sorted(alignment.values(), key=sort_key):
    a = alignment[arts[0]]
    out.write("[%s %s %s]\n" % (cl.get_unique(a.dom),
                                rel.rcc5_name(a.relation),
                                cl.get_unique(a.cod)))
  out.write("\n")

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('checklist', help='checklist')
  parser.add_argument('--tag', default="A")
  parser.add_argument('--name', default="generated by eulerx.py")
  args = parser.parse_args()
  ch = cl.read_checklist(args.checklist, args.tag, args.name)
  dump(ch, sys.stdout)
