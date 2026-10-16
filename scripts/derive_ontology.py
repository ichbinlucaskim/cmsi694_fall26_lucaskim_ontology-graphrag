"""Derive the treatment ontology from Wikidata property constraints (SCRUM-17).

    python scripts/derive_ontology.py           # fetch what is not cached, write outputs
    python scripts/derive_ontology.py --offline # write outputs from the cache only
    python scripts/derive_ontology.py --check   # regenerate from the cache only, compare

Relations: the 34 relations of docs/notes/2wiki-relation-map.json, each with
its matched Wikidata property ("has part" uses P527; see
docs/notes/ontology-decisions.md).

Entity types: every class named in a subject type constraint (Q21503250) or a
value type constraint (Q21510865) of those properties, read from the class
qualifier (P2308) of their property constraint statements (P2302), is assigned
by ENTITY_TYPES to exactly one entity type or by EXCLUDED_CLASSES to exactly
one exclusion reason. The script refuses to run if a constraint class is
unassigned, assigned twice, or if a rule names a class that no constraint
uses. A relation's domain (range) is the set of types its subject (value)
classes map to. Where the constraints give no type, MANUAL_ENDS sets it and
the output says so. Time-valued properties have range Date, an entity type
with no Wikidata classes (D6).

Definitions: a relation's definition is its English Wikidata description with
the notes addressed to Wikidata editors removed by EDITOR_NOTE (D7). The
verbatim description is kept as wikidata_description. The rule, in order:

1. Remove every parenthesized or bracketed group that matches EDITOR_NOTE:
   "(P1196)", "[for lyricist, use "lyrics by" (P676)]",
   "(not to be used for human beings)".
2. Split the rest into sentences at a period followed by a space and a
   capital letter or a quote, split each sentence into clauses at "; ", and
   drop every clause that matches. A sentence with no clause left is dropped.
3. Collapse whitespace, remove spaces before punctuation, and strip trailing
   spaces, commas, semicolons, and colons. If steps 1 and 2 removed anything,
   also strip a trailing period, as most descriptions end without one.

EDITOR_NOTE matches a Wikidata property ID (P123), the word "property", the
words "use", "used", or "preferred", or text starting with "see also" or "not
for" (all case-insensitive). These mark instructions to editors, cross
references to other properties, and usage guidance; none describes the
relation itself. If nothing would be left, the description is kept whole.

Validation: instance of (P31) for the entity QIDs in the study50
evidences_id (at most VALIDATION_CAP), each class followed up subclass of
(P279) for at most MAX_P279_DEPTH steps until it reaches a mapped class.

Outputs:
    ontology/ontology.json            the ontology
    ontology/derivation_report.json   validation and relation coverage

Wikidata responses are cached under data/raw/wikidata/ by
scripts/wikidata_cache.py. Standard library only.
"""

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

import wikidata_cache as wc

ROOT = Path(__file__).resolve().parent.parent
RELATION_MAP_PATH = ROOT / "docs" / "notes" / "2wiki-relation-map.json"
DEV_PATH = ROOT / "data" / "raw" / "2wiki" / "dev.json"
SUBSET_MANIFEST_PATH = ROOT / "data" / "subsets" / "manifest.json"
ONTOLOGY_DIR = ROOT / "ontology"
ONTOLOGY_PATH = ONTOLOGY_DIR / "ontology.json"
REPORT_PATH = ONTOLOGY_DIR / "derivation_report.json"

SUBJECT_TYPE_CONSTRAINT = "Q21503250"
VALUE_TYPE_CONSTRAINT = "Q21510865"
PROPERTY_CONSTRAINT = "P2302"
CONSTRAINT_CLASS = "P2308"
# D1: the relation map leaves "has part" unmatched; P527 is "has part(s)".
PID_OVERRIDES = {"has part": "P527"}
VALIDATION_SUBSET = "study50"
VALIDATION_CAP = 200
MAX_P279_DEPTH = 5
QID = re.compile(r"^Q\d+$")
DATE_TYPE = "Date"
EDITOR_NOTE = re.compile(
    r"\bP\d+\b|\bproperty\b|\b(?:use|used|preferred)\b|^\W*(?:see also|not for)\b",
    re.IGNORECASE,
)
BRACKETED = re.compile(r"\s*(?:\([^()]*\)|\[[^\[\]]*\])")
SENTENCE_END = re.compile(r"(?<=\.)\s+(?=[A-Z\"'])")

# Each rule: name, one-line definition, broader type (a listed type admits its
# narrower types), and the constraint classes it collapses, grouped by why.
ENTITY_TYPES = [
    {
        "name": "Human",
        "definition": "An individual person, living or historical.",
        "broader": None,
        "classes": {
            "humans and persons": ["Q5", "Q215627", "Q21070568", "Q20643955"],
            "classes of people defined by a role they hold": ["Q508719", "Q59755569", "Q60614352"],
        },
    },
    {
        "name": "Group",
        "definition": "Two or more people credited or acting together, such as a band, duo, couple, or team.",
        "broader": None,
        "classes": {
            "groups of people": ["Q16334295", "Q177634", "Q18204"],
            "families and couples": ["Q16979650", "Q14756018", "Q219160", "Q3046146", "Q14073567", "Q10648343"],
            "performing and production groups": [
                "Q215380", "Q2088357", "Q18510489", "Q2416217", "Q2393314", "Q15267437",
                "Q7247847", "Q84310035", "Q2985386", "Q24354647", "Q2013644", "Q12973014",
            ],
        },
    },
    {
        "name": "Organization",
        "definition": "A formally constituted body such as a company, agency, broadcaster, or society.",
        "broader": None,
        "classes": {
            "organizations": [
                "Q43229", "Q55097243", "Q4120211", "Q15911314", "Q3152824", "Q16519632",
                "Q2742167", "Q1306981",
            ],
            "companies and publishers": [
                "Q783794", "Q167037", "Q13235160", "Q2085381", "Q2516866", "Q7554349",
                "Q2608849", "Q18127", "Q11396960", "Q742421", "Q11812394", "Q5354754",
            ],
            "government bodies": ["Q327333", "Q2659904", "Q895526"],
            "broadcasters and news agencies": ["Q15265344", "Q2001305", "Q1474440", "Q14350", "Q1616075", "Q192283"],
        },
    },
    {
        "name": "Educational institution",
        "definition": "A school, college, university, or other organization that educates students.",
        "broader": "Organization",
        "classes": {
            "educational institutions": [
                "Q2385804", "Q23005223", "Q5341295", "Q20860083", "Q96086516", "Q4671277",
                "Q32053225", "Q233324",
            ],
        },
    },
    {
        "name": "Creative work",
        "definition": "A work of authorship or performance not covered by a narrower work type, such as a play or video game.",
        "broader": None,
        "classes": {
            "works in general": ["Q386724", "Q17489659", "Q7725310", "Q286583", "Q17538690", "Q2431196", "Q115668795"],
            "stage works and performances": ["Q25379", "Q43099500", "Q35140", "Q17538722", "Q5474871"],
            "games and interactive works": ["Q7889", "Q7058673", "Q116779426", "Q11410", "Q106046707"],
            "other works": ["Q4006", "Q97180164", "Q18593264", "Q35127", "Q49094714"],
        },
    },
    {
        "name": "Film",
        "definition": "A motion picture, a film series, or a dubbed version of a film.",
        "broader": "Creative work",
        "classes": {"films": ["Q11424", "Q24856", "Q26204053"]},
    },
    {
        "name": "Broadcast program",
        "definition": "A television, radio, or podcast program or series, or one of its seasons.",
        "broader": "Creative work",
        "classes": {"programs": ["Q15416", "Q14623351", "Q1555508", "Q2635894", "Q24634210", "Q10688145"]},
    },
    {
        "name": "Musical work",
        "definition": "A composition, song, opera, or musical release.",
        "broader": "Creative work",
        "classes": {
            "compositions and releases": [
                "Q2188189", "Q105543609", "Q24887304", "Q2031291", "Q108352496", "Q115473170", "Q58483083",
            ],
        },
    },
    {
        "name": "Written work",
        "definition": "A book, periodical, document, or other published text, including legal instruments.",
        "broader": "Creative work",
        "classes": {
            "texts and publications": [
                "Q47461344", "Q49848", "Q732577", "Q105420", "Q1711593", "Q8274", "Q1980247",
                "Q2122677", "Q3331189", "Q15938550", "Q2217301", "Q1348645", "Q106833", "Q122731938", "Q152416",
            ],
            "periodicals": ["Q1002697", "Q41298", "Q11032"],
            "lists": ["Q12139612", "Q80793969", "Q91828006", "Q106140535"],
            "legal instruments": ["Q49371", "Q131569", "Q321839", "Q1572600"],
        },
    },
    {
        "name": "Award",
        "definition": "A prize, honour, decoration, or award category given to a person, group, or work.",
        "broader": None,
        "classes": {
            "awards and honours": [
                "Q618779", "Q38033430", "Q131647", "Q193622", "Q1499804", "Q1788716", "Q11448906",
                "Q378427", "Q5257307", "Q56116950", "Q3320743", "Q1046088", "Q7302601", "Q16249975",
                "Q107655869", "Q657438",
            ],
        },
    },
    {
        "name": "Occupation",
        "definition": "A profession, job, position, or religious role a person holds.",
        "broader": None,
        "classes": {
            "occupations and positions": [
                "Q12737077", "Q28640", "Q192581", "Q4164871", "Q480319", "Q9363889", "Q1294787",
            ],
            "religious roles": ["Q63188808", "Q63188683", "Q108377574", "Q4504549"],
        },
    },
    {
        "name": "Cause of death",
        "definition": "A disease, injury, method, or event named as the cause of a death.",
        "broader": None,
        "classes": {
            "causes of death": [
                "Q1931388", "Q2057971", "Q2485083", "Q15169167", "Q171558", "Q124490", "Q650711",
                "Q1520311", "Q61915880", "Q191089",
            ],
        },
    },
    {
        "name": "Location",
        "definition": "A place not covered by a narrower place type, such as a region, river, or island.",
        "broader": None,
        "classes": {
            "places in general": ["Q2221906", "Q27096213", "Q17334923", "Q115095765", "Q618123", "Q62077203"],
            "regions": ["Q82794", "Q1620908", "Q3502482", "Q5107", "Q219858", "Q2583015"],
            "places at sea": ["Q55438959", "Q630013"],
        },
    },
    {
        "name": "Country",
        "definition": "A sovereign, historical, or dependent state or territory.",
        "broader": "Location",
        "classes": {
            "states": [
                "Q6256", "Q3624078", "Q7275", "Q3024240", "Q96196009", "Q1151405", "Q10711424",
                "Q48349", "Q170156", "Q43702", "Q148837", "Q133442", "Q1250464", "Q59281",
                "Q678116", "Q28171280", "Q1896989", "Q15304003",
            ],
            "dependent and contested territories": ["Q161243", "Q2577883", "Q15239622", "Q133156"],
        },
    },
    {
        # D5: one type for settlements and administrative areas; Wikidata files
        # many cities under administrative territorial entity.
        "name": "Settlement or region",
        "definition": "A city, town, village, or administrative area below the country level.",
        "broader": "Location",
        "classes": {
            "administrative units": [
                "Q56061", "Q19953632", "Q107390", "Q182547", "Q1048835", "Q253836", "Q5982983", "Q102496",
            ],
            "settlements": ["Q486972"],
        },
    },
    {
        "name": "Facility",
        "definition": "A building, structure, or site such as a hospital, cemetery, prison, or airport.",
        "broader": "Location",
        "classes": {
            "buildings and structures": [
                "Q811979", "Q41176", "Q13226383", "Q1220959", "Q16560", "Q1248784", "Q245016",
                "Q820477", "Q83405", "Q656720", "Q2800000",
            ],
            "medical and residential facilities": ["Q16917", "Q4260475", "Q837142", "Q67140121"],
            "religious houses": ["Q44613", "Q1128397"],
            "burial places": ["Q39614", "Q16859021", "Q6023295", "Q567603", "Q48634"],
            "places of detention": ["Q40357", "Q91165", "Q1785071", "Q88291", "Q55506436"],
        },
    },
    {
        "name": "Event",
        "definition": "Something that happens at a time, such as a battle, competition, ceremony, or campaign.",
        "broader": None,
        "classes": {
            "events": [
                "Q1190554", "Q1656682", "Q15275719", "Q16510064", "Q13406554", "Q4504495", "Q178561",
                "Q2401485", "Q6056746", "Q98216532", "Q1172486", "Q2334719", "Q504703",
            ],
        },
    },
    {
        # D6: the range of the time-valued relations. No constraint class maps
        # here; Date is set by the Wikidata datatype (time).
        "name": DATE_TYPE,
        "definition": "A calendar date, month, or year.",
        "broader": None,
        "classes": {},
    },
    {
        "name": "Product",
        "definition": "A manufactured or published product, model, brand, machine, or piece of software.",
        "broader": None,
        "classes": {
            "products and brands": [
                "Q2424752", "Q10929058", "Q811701", "Q28877", "Q1485500", "Q66661745", "Q16686448",
                "Q431289", "Q972011",
            ],
            "machines and software": ["Q11019", "Q35273", "Q11012", "Q7397", "Q62651817"],
        },
    },
]

# Constraint classes that collapse to no type, grouped by reason.
EXCLUDED_CLASSES = {
    "fiction and myth": {
        "reason": (
            "Fictional, mythical, legendary, and hypothetical classes. 2Wiki answers come from "
            "Wikipedia articles about real subjects; a fictional or mythical entity is still "
            "typed by what it is described as."
        ),
        "classes": [
            "Q95074", "Q3241972", "Q4271324", "Q178885", "Q24334299", "Q21070598", "Q13002315",
            "Q207174", "Q2135501", "Q21191150", "Q75855169", "Q64520857", "Q115537581",
            "Q14514600", "Q24334685", "Q15632617", "Q57662985", "Q2775969", "Q1145276",
            "Q3895768", "Q3238337", "Q14897293", "Q5446565", "Q14623646", "Q15690029",
            "Q60466213", "Q15306849", "Q124301146", "Q74574", "Q3542731", "Q30017383",
            "Q66481339", "Q6619719", "Q15711870", "Q15773317", "Q65209857", "Q1569167",
            "Q22988604", "Q20830276", "Q2239243", "Q24533670", "Q20203727", "Q17364638",
            "Q17305127", "Q47472256", "Q115580828", "Q21451536", "Q116680403", "Q87370199",
            "Q1055307", "Q60153785", "Q18670171", "Q15831596", "Q112265308", "Q64643615",
            "Q15619164", "Q340069", "Q502931", "Q1707847", "Q135106502", "Q33753", "Q18706315",
        ],
    },
    "animals and other organisms": {
        "reason": "Non-human organisms, breeds, and taxa; the 2Wiki relations hold between people, works, organizations, and places.",
        "classes": [
            "Q729", "Q7239", "Q10855152", "Q26401003", "Q57812559", "Q57812611", "Q622852",
            "Q228534", "Q146", "Q144", "Q726", "Q26843", "Q36341", "Q839769", "Q876500",
            "Q301676", "Q60198807", "Q4886", "Q16521", "Q38829", "Q38672", "Q611804",
            "Q16334298", "Q18347143", "Q284851",
        ],
    },
    "human remains and pre-birth cases": {
        "reason": "Edge cases of the human class that do not appear as 2Wiki answers.",
        "classes": ["Q2345820", "Q26513", "Q117463454", "Q3409626", "Q199414"],
    },
    "names and terms": {
        "reason": "Names and words rather than the things they name.",
        "classes": [
            "Q61002", "Q11415657", "Q16017119", "Q101352", "Q202444", "Q187931", "Q130989",
            "Q42298422", "Q1969448", "Q117009251", "Q217438",
        ],
    },
    "peoples and legal statuses": {
        "reason": (
            "Ethnic groups, nations, nationality, and citizenship. Country of citizenship "
            "points at a Country in 2Wiki; these classes name the status, not the place."
        ),
        "classes": ["Q41710", "Q2531956", "Q4533081", "Q7840353", "Q6266", "Q231002", "Q42138", "Q1072012"],
    },
    "culture, language, belief, and practice": {
        "reason": (
            "Abstract cultural kinds that appear only as subjects of country of origin or "
            "founded by; 2Wiki uses those relations for works and organizations."
        ),
        "classes": [
            "Q4113741", "Q17376908", "Q33384", "Q8192", "Q1778821", "Q2095", "Q19861951",
            "Q1039303", "Q82821", "Q251777", "Q59544", "Q264965", "Q2198855", "Q49773",
            "Q1826286", "Q9174", "Q71966963", "Q7257", "Q483394", "Q188451", "Q862597",
            "Q1824109", "Q60733114", "Q349", "Q31629", "Q384748", "Q327496", "Q1813494",
            "Q350453", "Q8187769", "Q24902509", "Q268592", "Q1047113", "Q60031086", "Q17737",
            "Q1151067", "Q151885", "Q1445650",
        ],
    },
    "generic, structural, and metaclasses": {
        "reason": (
            "Classes too general to be a type (agent, physical object, system), unions of "
            "listed types (person or organization), Wikimedia-internal classes, and classes "
            "of classes (ship type)."
        ),
        "classes": [
            "Q795052", "Q24229398", "Q106559804", "Q4406616", "Q223557", "Q121033050",
            "Q58778", "Q15893266", "Q17442446", "Q13406463", "Q2235308", "Q110295396",
            "Q112872396", "Q2668072", "Q170584", "Q1298668", "Q22222786", "Q2023606",
            "Q1371819", "Q2684591", "Q80071", "Q14659", "Q174923", "Q189977", "Q1046315",
        ],
    },
    "online accounts, services, and software artefacts": {
        "reason": "Accounts, channels, services, voice banks, and AI models; none is a 2Wiki answer type.",
        "classes": [
            "Q17558136", "Q102345381", "Q124030631", "Q72588", "Q141245227", "Q134612820",
            "Q550596", "Q117246174", "Q117349473", "Q584529", "Q179550",
        ],
    },
    "administrative records and schemes": {
        "reason": "Registers, certifications, licences, and survey methods.",
        "classes": ["Q1428914", "Q374814", "Q95107111", "Q814232", "Q54933017"],
    },
    "vessels and off-world places": {
        "reason": "Ships and astronomical places, listed as birth or detention places for rare cases.",
        "classes": ["Q11446", "Q16391167", "Q177597", "Q6999", "Q4130"],
    },
    "conditions and journeys": {
        "reason": "A condition or a journey, not a place, listed as a place of detention.",
        "classes": ["Q320994", "Q61927259"],
    },
}

# Ends the constraints leave empty, set by hand from dev examples.
MANUAL_ENDS = {
    ("award received", "domain"): (
        ["Group", "Human"],
        "P166 has no subject type constraint. Dev subjects are people and groups, e.g. "
        "'Steve Vai' and 'Slayer' (Grammy Award).",
    ),
    ("country", "domain"): (
        ["Location", "Organization"],
        "P17 has no subject type constraint. Dev subjects are places, facilities, and "
        "organizations, e.g. 'Cabixi River', 'Gillam Airport', 'Empire Kosher'.",
    ),
    ("spouse", "range"): (
        ["Human"],
        "P26 has no value type constraint. Dev objects are people, e.g. 'Stephen King'.",
    ),
    ("has part", "domain"): (
        ["Group"],
        "P527 has no type constraints. All 17 dev triples link a band to a member, e.g. "
        "'XYZ' has part 'Chris Squire'.",
    ),
    ("has part", "range"): (
        ["Human"],
        "As for the domain: every dev object is a band member.",
    ),
    ("inception", "domain"): (
        ["Organization"],
        "P571 has no type constraints. Dev subjects are organizations and schools, e.g. "
        "'Sigma Xi', 'Korn Ferry', 'Whitehorse Manor Junior School'.",
    ),
}


# ---------------------------------------------------------------- helpers


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def class_rules() -> tuple[dict[str, str], dict[str, str]]:
    """Return ({class: type name}, {class: exclusion key}); refuse duplicates."""
    to_type, to_excluded, seen = {}, {}, Counter()
    for t in ENTITY_TYPES:
        for qids in t["classes"].values():
            for q in qids:
                to_type[q] = t["name"]
                seen[q] += 1
    for key, group in EXCLUDED_CLASSES.items():
        for q in group["classes"]:
            to_excluded[q] = key
            seen[q] += 1
    dupes = sorted(q for q, n in seen.items() if n > 1)
    if dupes:
        raise SystemExit(f"Classes assigned more than once: {dupes}")
    return to_type, to_excluded


def definition_of(description: str) -> str:
    """The description without notes to Wikidata editors (D7; rule in the module docstring)."""
    text = BRACKETED.sub(lambda m: "" if EDITOR_NOTE.search(m.group()) else m.group(), description)
    sentences = ["; ".join(c for c in s.split("; ") if not EDITOR_NOTE.search(c))
                 for s in SENTENCE_END.split(text)]
    kept = " ".join(s for s in sentences if s)
    removed = kept != description
    text = re.sub(r"\s+([.,;:])", r"\1", re.sub(r"\s+", " ", kept)).strip().rstrip(" ,;:")
    if removed:
        text = text.removesuffix(".").rstrip(" ,;:")
    return text or description


def type_constraints(prop: dict) -> dict[str, list[str]]:
    """Classes of the non-deprecated subject and value type constraints of a property."""
    out = {"domain": set(), "range": set()}
    for claim in prop.get("claims", {}).get(PROPERTY_CONSTRAINT, []):
        kind = claim["mainsnak"].get("datavalue", {}).get("value", {}).get("id")
        if claim.get("rank") == "deprecated" or kind not in (SUBJECT_TYPE_CONSTRAINT, VALUE_TYPE_CONSTRAINT):
            continue
        end = "domain" if kind == SUBJECT_TYPE_CONSTRAINT else "range"
        for snak in claim.get("qualifiers", {}).get(CONSTRAINT_CLASS, []):
            if "datavalue" in snak:
                out[end].add(snak["datavalue"]["value"]["id"])
    return {k: sorted(v) for k, v in out.items()}


# ---------------------------------------------------------------- derivation


def load_relations() -> list[dict]:
    relation_map = json.loads(RELATION_MAP_PATH.read_text(encoding="utf-8"))
    relations = []
    for r in relation_map["relations"]:
        pid = PID_OVERRIDES.get(r["relation"], r["pid"])
        if pid is None:
            raise SystemExit(f"No property for relation {r['relation']!r}")
        relations.append({"relation": r["relation"], "pid": pid, "match": r["match"],
                          "variant": r["variant"]})
    return relations


def derive(offline: bool) -> tuple[dict, dict]:
    relations = load_relations()
    props = wc.get_entities([r["pid"] for r in relations], kind="entities", offline=offline)
    constraints = {r["relation"]: type_constraints(wc.entity(props[r["pid"]])) for r in relations}
    used = sorted({q for c in constraints.values() for qs in c.values() for q in qs})

    to_type, to_excluded = class_rules()
    ruled = set(to_type) | set(to_excluded)
    unassigned = sorted(set(used) - ruled)
    unused = sorted(ruled - set(used))
    if unassigned or unused:
        raise SystemExit(f"Class rules out of step with the constraints: "
                         f"unassigned {unassigned}, not used by any constraint {unused}")
    labels = wc.get_entities(used, kind="labels", offline=offline)

    def entry(q):
        return {"qid": q, "label": wc.label(labels[q])}

    entity_types = []
    for t in ENTITY_TYPES:
        entity_types.append({
            "name": t["name"],
            "definition": t["definition"],
            "broader": t["broader"],
            "wikidata_classes": [
                {"group": group, "classes": [entry(q) for q in sorted(qids)]}
                for group, qids in sorted(t["classes"].items())
            ],
        })
    type_names = {t["name"] for t in ENTITY_TYPES}

    relation_types = []
    for r in relations:
        prop = wc.entity(props[r["pid"]])
        is_date = prop.get("datatype") == "time"
        description = wc.description(props[r["pid"]])
        out = {
            "relation": r["relation"],
            "pid": r["pid"],
            "wikidata_label": wc.label(props[r["pid"]]),
            "wikidata_description": description,
            "definition": definition_of(description),
            "wikidata_datatype": prop.get("datatype"),
        }
        for end in ("domain", "range"):
            classes = constraints[r["relation"]][end]
            mapped = sorted({to_type[q] for q in classes if q in to_type})
            manual = MANUAL_ENDS.get((r["relation"], end))
            if end == "range" and is_date:
                if classes:
                    raise SystemExit(f"{r['relation']}: date property with value type classes")
                value, source, note = [DATE_TYPE], "datatype", "Wikidata datatype is time (D6)."
            elif mapped:
                if manual:
                    raise SystemExit(f"{r['relation']} {end}: manual end given but constraints map to {mapped}")
                value, source, note = mapped, "constraint", None
            elif manual:
                value, source, note = sorted(manual[0]), "manual", manual[1]
            else:
                raise SystemExit(f"{r['relation']} {end}: constraints map to no type and no manual end")
            if isinstance(value, list) and not set(value) <= type_names:
                raise SystemExit(f"{r['relation']} {end}: unknown types {value}")
            out[end] = value
            out[f"{end}_source"] = source
            out[f"{end}_note"] = note
            out[f"{end}_constraint_classes"] = {
                "total": len(classes),
                "mapped": sum(q in to_type for q in classes),
                "excluded": sum(q in to_excluded for q in classes),
            }
        relation_types.append(out)

    excluded = [
        {"reason_key": key, "reason": g["reason"],
         "classes": [entry(q) for q in sorted(g["classes"])]}
        for key, g in sorted(EXCLUDED_CLASSES.items())
    ]
    provenance = {
        "sources": {
            str(p.relative_to(ROOT)): sha256_of(p)
            for p in (RELATION_MAP_PATH, Path(__file__).resolve(), Path(wc.__file__).resolve())
        },
        "wikidata_endpoint": wc.WIKIDATA_API,
        "wikidata_lookup_dates": wc.fetched_dates(["entities", "labels"]),
        "wikidata_requests": {
            "properties": "wbgetentities props=labels|descriptions|claims languages=en",
            "constraint classes": "wbgetentities props=labels|descriptions languages=en",
        },
        "constraint_types": {"subject type": SUBJECT_TYPE_CONSTRAINT,
                             "value type": VALUE_TYPE_CONSTRAINT,
                             "class qualifier": CONSTRAINT_CLASS},
        "constraint_classes": len(used),
    }
    ontology = {
        "name": "2Wiki treatment ontology",
        "description": (
            "Entity types and relation types for ontology-guided extraction on "
            "2WikiMultiHopQA, derived from Wikidata property constraints (SCRUM-17). "
            "A listed type admits its narrower types. The ontology supplies types and "
            "relations only; it has no composition rules (D2)."
        ),
        "entity_types": sorted(entity_types, key=lambda t: t["name"]),
        "relation_types": sorted(relation_types, key=lambda r: r["relation"]),
        "excluded_constraint_classes": excluded,
        "provenance": provenance,
    }
    report = {
        "validation": validate(to_type, offline),
        "coverage": coverage({r["relation"] for r in relations}),
        "provenance": {
            "sources": {str(p.relative_to(ROOT)): sha256_of(p)
                        for p in (DEV_PATH, SUBSET_MANIFEST_PATH)},
            "wikidata_endpoint": wc.WIKIDATA_API,
            "wikidata_lookup_dates": wc.fetched_dates(["claims_P31", "claims_P279"]),
            "wikidata_requests": "wbgetclaims for P31 (entities) and P279 (their classes)",
        },
    }
    return ontology, report


# ---------------------------------------------------------------- checks


def load_dev() -> list[dict]:
    with DEV_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def subset_ids(name: str) -> list[str]:
    return json.loads(SUBSET_MANIFEST_PATH.read_text(encoding="utf-8"))["subsets"][name]["question_ids"]


def validate(to_type: dict[str, str], offline: bool) -> dict:
    """Type the study50 evidences_id entities through P31 and up to MAX_P279_DEPTH P279 steps."""
    wanted = set(subset_ids(VALIDATION_SUBSET))
    qids = sorted({x for r in load_dev() if r["_id"] in wanted
                   for s, _, o in r["evidences_id"] for x in (s, o) if QID.match(x)})
    capped = qids[:VALIDATION_CAP]
    p31 = wc.get_claims(capped, "P31", offline=offline)

    parents: dict[str, list[str]] = {}

    def types_of(start: list[str]) -> tuple[list[str], int | None]:
        """Types at the smallest P279 depth where any start class reaches a mapped class."""
        frontier, seen = list(start), set(start)
        for depth in range(MAX_P279_DEPTH + 1):
            hits = sorted({to_type[c] for c in frontier if c in to_type})
            if hits or not frontier:
                return hits, depth if hits else None
            missing = [c for c in frontier if c not in parents]
            for c, rec in wc.get_claims(missing, "P279", offline=offline).items():
                parents[c] = wc.claim_targets(rec, "P279")
            frontier = sorted({p for c in frontier for p in parents[c]} - seen)
            seen.update(frontier)
        return [], None

    entities = []
    for q in capped:
        classes = wc.claim_targets(p31[q], "P31")
        types, depth = types_of(classes)
        entities.append({"qid": q, "p31": classes, "types": types, "p279_depth": depth})
    covered = [e for e in entities if e["types"]]
    by_type = Counter(t for e in entities for t in e["types"])
    return {
        "subset": VALIDATION_SUBSET,
        "entity_qids": len(qids),
        "looked_up": len(capped),
        "cap": VALIDATION_CAP,
        "max_p279_depth": MAX_P279_DEPTH,
        "p279_lookups": len(parents),
        "covered": len(covered),
        "coverage": len(covered) / len(capped) if capped else None,
        "entities_by_type": dict(sorted(by_type.items())),
        "depth_counts": {str(k): v for k, v in sorted(Counter(e["p279_depth"] for e in covered).items())},
        "uncovered": [{"qid": e["qid"], "p31": e["p31"]} for e in entities if not e["types"]],
        "entities": entities,
    }


def coverage(relation_set: set[str]) -> dict:
    """Share of evidence triples whose relation is in the relation set."""
    dev = load_dev()
    wanted = set(subset_ids("study50"))
    out = {}
    for name, rows in (("study50", [r for r in dev if r["_id"] in wanted]), ("dev", dev)):
        counts = Counter(rel for r in rows for _, rel, _ in r["evidences"])
        total = sum(counts.values())
        covered = sum(n for rel, n in counts.items() if rel in relation_set)
        out[name] = {
            "questions": len(rows),
            "triples": total,
            "distinct_relations": len(counts),
            "covered_triples": covered,
            "coverage": covered / total if total else None,
            "uncovered_relations": {rel: n for rel, n in sorted(counts.items()) if rel not in relation_set},
            "relation_counts": dict(sorted(counts.items())),
        }
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true",
                        help="regenerate from the cache only and compare with the committed files")
    parser.add_argument("--offline", action="store_true",
                        help="write the outputs from the cache only; a cache miss is an error")
    args = parser.parse_args()
    try:
        ontology, report = derive(offline=args.check or args.offline)
    except wc.CacheMiss as e:
        raise SystemExit(f"Cache miss in offline mode: {e}")
    outputs = {ONTOLOGY_PATH: dump(ontology), REPORT_PATH: dump(report)}
    if args.check:
        stale = [p for p, text in outputs.items()
                 if not p.exists() or p.read_text(encoding="utf-8") != text]
        for p in stale:
            print(f"differs: {p.relative_to(ROOT)}")
        print("check failed" if stale else "check passed: outputs match a regeneration from the cache")
        return 1 if stale else 0
    ONTOLOGY_DIR.mkdir(exist_ok=True)
    for p, text in outputs.items():
        p.write_text(text, encoding="utf-8")
        print(f"Wrote {p.relative_to(ROOT)}")
    v, c = report["validation"], report["coverage"]
    print(f"{len(ontology['entity_types'])} entity types, {len(ontology['relation_types'])} relation types")
    print(f"validation: {v['covered']}/{v['looked_up']} entities typed ({100 * v['coverage']:.1f}%)")
    for name, cov in c.items():
        print(f"coverage {name}: {cov['covered_triples']}/{cov['triples']} triples "
              f"({100 * cov['coverage']:.1f}%), uncovered {cov['uncovered_relations']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
