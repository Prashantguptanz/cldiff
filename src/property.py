# Properties (some of which will be used as fields)

import collections

# Selector: record * property -> value

Selector = \
  collections.namedtuple('Selector',
                         ['uri',
                          'pet_name',     # local to this code base
                          'specificity']) # with regard to taxon identity

selectors_by_uri = {}
selectors_by_pet_name = {}
selectors_by_specificity = []

def by_specificity(specificity):
  return selectors_by_specificity[specificity]  

def by_name(name):
  return selectors_by_pet_name.get(name)

def uri_to_pet_name(uri):
  return uri.split('/')[-1]

def uri_to_selector(uri):
  probe = selectors_by_uri.get(uri)
  if probe: return probe
  pet_name = uri_to_pet_name(uri)
  spec = len(selectors_by_specificity)
  sel = Selector(uri, pet_name, spec)
  selectors_by_uri[uri] = sel
  selectors_by_pet_name[pet_name] = sel
  selectors_by_specificity.append(sel)
  return sel

def alias(this, to_that):
  if this in pet_name_to_uri_table:
    raise "URI pet_name collision:  \n%s  \n%s" % (to_that, this)
  sel = by_name(to_that)
  selectors_by_pet_name[this] = sel

# Initialize non-field selectors

# We do this in order from least specific to most specific,
# for simplicity... low order bits first

# dwciri: (http://rs.tdwg.org/dwc/iri/)

# The entire record for the taxon in the checklist
record    = uri_to_selector("data:,property/record")

# dwc:TaxonID - "This term is no longer recommended for use."
#   http://rs.tdwg.org/dwc/terms

# URIs (columns) I'm considering adding:
#   - one URI for each table I set up in the analysis
#     - something for what I'm currently calling TNU id or 
#       'sequence number' (unique record key across all inputs)
#     - mutexes

uris = [
        "http://purl.org/dc/terms/source",     # checklist
        "http://rs.tdwg.org/dwc/terms/nomenclaturalStatus",
        "http://rs.tdwg.org/dwc/terms/taxonomicStatus",     # flush?
        "http://rs.tdwg.org/dwc/terms/verbatimTaxonRank",   # don't use this URI...
        "http://rs.tdwg.org/dwc/terms/taxonRank",
        "http://rs.tdwg.org/dwc/terms/scientificNameAuthorship",
        "http://rs.tdwg.org/dwc/terms/nameAccordingToID",
        "http://rs.tdwg.org/dwc/terms/taxonID",     # at the source!?  misused
        "http://rs.tdwg.org/dwc/terms/vernacularName",
        "http://rs.tdwg.org/dwc/terms/parentNameUsageID",
        "http://rs.tdwg.org/dwc/terms/namePublishedInYear",
        "http://rs.tdwg.org/dwc/terms/specificEpithet",
        "http://rs.tdwg.org/dwc/terms/infraspecificEpithet",
        "https://github.com/jar398/biodiversity/wiki/quasi_epithet",
        "http://rs.tdwg.org/dwc/terms/acceptedNameUsageID",
        "http://rs.gbif.org/terms/1.0/canonicalName",
        "http://rs.tdwg.org/dwc/terms/scientificName",
        "https://github.com/jar398/biodiversity/wiki/division",    # Extension, etc.
        "http://rs.tdwg.org/dwc/terms/taxonConceptID",
]
for uri in uris: uri_to_selector(uri)
  
number_of_selectors = len(selectors_by_specificity)

if __name__ == '__main__':
  import sys
  import yaml
  with open(sys.argv[1], 'r') as stream:
    print(yaml.load(stream))