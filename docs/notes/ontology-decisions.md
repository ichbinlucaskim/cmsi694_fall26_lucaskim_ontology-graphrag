# Ontology decisions (SCRUM-17)

The treatment condition's ontology is `ontology/ontology.json`, written by
`scripts/derive_ontology.py` from the Wikidata property constraints of the 34
2WikiMultiHopQA relations. Validation and coverage results are in
`ontology/derivation_report.json`. Both files are regenerated from the
Wikidata cache in `data/raw/wikidata/` (git-ignored) with:

```
python scripts/derive_ontology.py --check
```

The check makes no network calls and fails if either file differs from a
fresh regeneration. All Wikidata lookups were made on 2026-10-06 through
`https://www.wikidata.org/w/api.php` (`wbgetentities`, `wbgetclaims`). They
used the rate-limit handling of `scripts/inspect_2wiki.py`: a User-Agent
header, a 2 s pause after each request, and Retry-After on HTTP 429. Request
counts: 34 property records, 462 class labels, 85 P31 lookups, and 34 P279
lookups.

## Decisions

**D1. Relations come from the relation map.** The relation types are the 34
relations of `docs/notes/2wiki-relation-map.json` (SCRUM-13), each with its
matched Wikidata property. Two need a note:

- `founded by` uses **P112**. Its relation-map match is the `en-gb` label of
  P112 only; the English label is "founded by" in other variants, and no other
  property matched.
- `has part` uses **P527** ("has part(s)"). The relation map has no exact
  match. P527 was the closest search hit, and all 17 dev triples link a band to
  a member, which is P527's use.

Each relation's one-line definition is the property's English Wikidata
description, with notes to Wikidata editors removed (D7).

**D2. No composition rules.** The ontology has no rules for derived kinship
relations such as paternal grandfather or father-in-law. Inference questions
ask for them, but their evidence uses only base relations (`father`, `mother`,
`spouse`, `sibling`, `child`, ...; see `docs/notes/2wiki-inspection.md`). The
treatment supplies a list of entity types and relation types only, so that the
study changes one variable: whether extraction is guided by a schema.
Composition rules are a possible later extension.

**D3. Three country relations stay separate.** `country` (P17), `country of
origin` (P495), and `country of citizenship` (P27) are three relation types.
They are different properties with different subjects (places and
organizations, works, people), and 2Wiki uses them as different relations.

**D4. Dates are literal attributes.** Superseded by D6. `date of birth` (P569), `date of death`
(P570), `publication date` (P577), and `inception` (P571) have range
`literal:date` and are also listed under `literal_attributes`. No entity type
stands for a date. The decision follows the Wikidata datatype (`time`) of all
four properties. 2Wiki writes dates in many surface forms, and `evidences_id`
replaces them with `date_information`.

**D5. Settlements and administrative areas are one type.** Settlement or
region covers cities, towns, villages, and administrative areas below the
country level. An earlier version of this ontology had separate Settlement
and Administrative region types. They were merged for two reasons:

- The extraction model sees only type names and definitions, not Wikidata
  classes, so it cannot use Wikidata's distinctions between them.
- Wikidata files many cities under administrative territorial entity. In
  validation, Toronto, Reykjavík, New York, Los Angeles, and Ayutthaya all
  reached Administrative region, and none reached Settlement.

With two types, the same city could be typed both ways in different passages
and become two graph nodes. The merged type keeps every class of both old
types: the 8 administrative-unit classes and human settlement (Q486972).

**D6. Dates are entities of type Date (supersedes D4).** The ontology has
an entity type Date, "A calendar date, month, or year." The four time-valued
relations, `date of birth`, `date of death`, `inception`, and `publication
date`, have range Date instead of `literal:date`, and the
`literal_attributes` list is removed, as nothing else used it. Date has no
Wikidata constraint classes; the script sets it as the range of every property
whose Wikidata datatype is `time` (range source `datatype`).

Reason: a LightRAG graph has entities and relations but no attributes. With a
literal range, a date relation had no valid target: the prompt offered no
entity type for a date, so the model either typed the date `date`, `other`,
or `unknown`, outside the ontology, or did not extract the relation. Almost
none were extracted. In the ontology smoke10 graph, 3 of 354 relations carry a
date label (`date of birth` 2, `publication date` 1; see
`docs/results/ontology-vs-baseline-smoke10.md`), although `date of birth`,
`date of death`, and `publication date` are among the most frequent 2Wiki
evidence relations (see Relation coverage).

**D7. Definitions omit notes to Wikidata editors.** English Wikidata
property descriptions often add instructions for editors, such as "Use
'manner of death' (P1196) for broadest category", cross references to other
properties, and usage guidance. None of it describes the relation, and the
property IDs mean nothing to the extraction model. `definition_of` in
`scripts/derive_ontology.py` removes them by a fixed rule, documented in the
script docstring: it drops each bracketed group, `;`-separated clause, and
sentence that names a property ID (P123), the word "property", the words
"use", "used", or "preferred", or that starts with "see also" or "not for".
The verbatim description is kept in the ontology file as
`wikidata_description`. The rule changes 13 of the 34 definitions:

| Relation | Wikidata description (before) | Definition (after) |
|---|---|---|
| cause of death | underlying or immediate cause of death. Underlying cause (e.g. car accident, stomach cancer) preferred. Use 'manner of death' (P1196) for broadest category, e.g. natural causes, accident, homicide, suicide | underlying or immediate cause of death |
| child | subject has object as child. Do not use for stepchildren—use "relative" (P1038), qualified with "kinship to subject" (P1039) | subject has object as child |
| composer | person(s) who wrote the music [for lyricist, use "lyrics by" (P676)] | person(s) who wrote the music |
| country | sovereign state that this subject item is in (not to be used for human beings) | sovereign state that this subject item is in |
| creator | maker of this creative work or other object (where no more specific property exists) | maker of this creative work or other object |
| father | male parent of the subject. For stepfather, use "stepparent" (P3448) | male parent of the subject |
| has part | part of this subject; inverse property of "part of" (P361). See also "has parts of the class" (P2670). | part of this subject |
| inception | time when an entity begins to exist; for date of official opening use P1619 | time when an entity begins to exist |
| mother | female parent of the subject. For stepmother, use "stepparent" (P3448) | female parent of the subject |
| occupation | occupation of a person. See also "field of work" (Property:P101), "position held" (Property:P39). Not for groups of people. There, use "field of work" (Property:P101), "industry" (Property:P452), "members have occupation" (Property:P3989). | occupation of a person |
| producer | person(s) who produced the film, musical work, theatrical production, etc. (for film, this does not include executive producers, associate producers, etc.) [for production company, use P272, video games - use P178] | person(s) who produced the film, musical work, theatrical production, etc. (for film, this does not include executive producers, associate producers, etc.) |
| sibling | the subject and the object have at least one common parent (brother, sister, etc. including half-siblings); use "relative" (P1038) for siblings-in-law (brother-in-law, sister-in-law, etc.) and step-siblings (step-brothers, step-sisters, etc.) | the subject and the object have at least one common parent (brother, sister, etc. including half-siblings) |
| spouse | the subject has the object as their spouse (husband, wife, partner, etc.). Use "unmarried partner" (P451) for non-married companions | the subject has the object as their spouse (husband, wife, partner, etc.) |

The prompt change is in `docs/results/prompt-diff-baseline-vs-ontology.diff`.

## How the entity types were derived

1. For each of the 34 properties, the script reads its property constraint
   statements (P2302) of two kinds: subject type constraint (Q21503250) and
   value type constraint (Q21510865). For each, it takes the classes in the
   class qualifier (P2308), skipping deprecated statements. This gives 462
   distinct classes.
2. Rules in `ENTITY_TYPES` and `EXCLUDED_CLASSES` in the script assign every
   one of the 462 classes either to one entity type (265 classes) or to one
   exclusion reason (197 classes). The script refuses to run if a class is
   unassigned, assigned twice, or named by a rule but not used by any
   constraint.
3. A relation's domain is the set of types its subject classes map to; its
   range is the set for its value classes. Excluded classes contribute
   nothing.
4. Six relation ends have no type from the constraints. These are set by hand
   from dev examples and marked `"source": "manual"` with a note in the
   ontology file (see below).

The result has **19 entity types**, inside the required 10 to 30: 18 from the
constraint classes and Date, which has no constraint classes (D6).

Some types have a `broader` type: Country, Settlement or region, and Facility
are narrower than Location; Film, Broadcast program, Musical
work, and Written work are narrower than Creative work; and Educational
institution is narrower than Organization. A domain or range that lists a type
admits its narrower types. This keeps the type list short while letting a
constraint as general as "geographic location" (the range of `place of birth`)
be stated exactly.

### Entity types

"Constraint classes" counts the Wikidata classes collapsed into the type.
"Validation entities" counts study50 entities typed into it (see Validation;
one entity is counted under two types).

| Entity type | Broader | Definition | Constraint classes | Validation entities |
|---|---|---|---|---|
| Award |  | A prize, honour, decoration, or award category given to a person, group, or work. | 16 | 0 |
| Broadcast program | Creative work | A television, radio, or podcast program or series, or one of its seasons. | 6 | 0 |
| Cause of death |  | A disease, injury, method, or event named as the cause of a death. | 10 | 0 |
| Country | Location | A sovereign, historical, or dependent state or territory. | 22 | 4 |
| Creative work |  | A work of authorship or performance not covered by a narrower work type, such as a play or video game. | 22 | 0 |
| Date |  | A calendar date, month, or year. | 0 | 0 |
| Educational institution | Organization | A school, college, university, or other organization that educates students. | 8 | 1 |
| Event |  | Something that happens at a time, such as a battle, competition, ceremony, or campaign. | 13 | 0 |
| Facility | Location | A building, structure, or site such as a hospital, cemetery, prison, or airport. | 27 | 0 |
| Film | Creative work | A motion picture, a film series, or a dubbed version of a film. | 3 | 6 |
| Group |  | Two or more people credited or acting together, such as a band, duo, couple, or team. | 21 | 2 |
| Human |  | An individual person, living or historical. | 7 | 60 |
| Location |  | A place not covered by a narrower place type, such as a region, river, or island. | 14 | 3 |
| Musical work | Creative work | A composition, song, opera, or musical release. | 7 | 1 |
| Occupation |  | A profession, job, position, or religious role a person holds. | 11 | 0 |
| Organization |  | A formally constituted body such as a company, agency, broadcaster, or society. | 29 | 1 |
| Product |  | A manufactured or published product, model, brand, machine, or piece of software. | 14 | 0 |
| Settlement or region | Location | A city, town, village, or administrative area below the country level. | 9 | 7 |
| Written work | Creative work | A book, periodical, document, or other published text, including legal instruments. | 26 | 1 |

### Collapsing rules

Each type lists the constraint classes it collapses, grouped by the reason
they belong together. Class labels are the English Wikidata labels.

**Award**

- awards and honours: hall of fame (Q1046088), group of awards (Q107655869), science award (Q11448906), medal (Q131647), grade of an order (Q1499804), homage (Q16249975), military decoration (Q1788716), order (Q193622), title of honor (Q3320743), literary award (Q378427), class of award (Q38033430), prize (Q5257307), film award category (Q56116950), award (Q618779), Roman triumph (Q657438), recognition (Q7302601)

**Broadcast program** (narrower than Creative work)

- programs: season (Q10688145), radio series (Q14623351), television program (Q15416), radio program (Q1555508), podcast show (Q24634210), radio drama (Q2635894)

**Cause of death**

- causes of death: violence (Q124490), execution method (Q15169167), violent crime (Q1520311), accident (Q171558), old age (Q191089), cause of death (Q1931388), health problem (Q2057971), suicide method (Q2485083), obsolete medical term (Q61915880), combat (Q650711)

**Country** (narrower than Location)

- dependent and contested territories: colony (Q133156), disputed territory (Q15239622), dependent territory (Q161243), occupied territory (Q2577883)
- states: state with limited recognition (Q10711424), client state (Q1151405), realm (Q1250464), city-state (Q133442), polis (Q148837), country of the Kingdom of the Netherlands (Q15304003), confederation (Q170156), subject of international law (Q1896989), ancient civilization (Q28171280), historical country (Q3024240), sovereign state (Q3624078), federation (Q43702), empire (Q48349), provisional government (Q59281), country (Q6256), government-in-exile (Q678116), state (Q7275), former or current state (Q96196009)

**Creative work**

- games and interactive works: VR experience (Q106046707), game (Q11410), group of video games often treated as a singular game (Q116779426), video game series (Q7058673), video game (Q7889)
- other works: item of collection or exhibition (Q18593264), website (Q35127), map (Q4006), portfolio (Q49094714), digital artistic drawing (Q97180164)
- stage works and performances: performance work (Q17538722), play (Q25379), performance (Q35140), performing arts production (Q43099500), Jatra (Q5474871)
- works in general: audiovisual release (Q115668795), group of works (Q17489659), group of manifestations (Q17538690), audiovisual work (Q2431196), manifestation (Q286583), work (Q386724), series of creative works (Q7725310)

**Educational institution** (narrower than Organization)

- educational institutions: educational facility (Q20860083), division of an educational institution (Q23005223), seminary (Q233324), educational institution (Q2385804), training organization (Q32053225), academic institution (Q4671277), educational organization (Q5341295), former educational institution (Q96086516)

**Event**

- events: data breach (Q1172486), occurrence (Q1190554), sports competition (Q13406554), recurring event (Q15275719), sporting event (Q16510064), planned event (Q1656682), battle (Q178561), legal case (Q2334719), expedition (Q2401485), award ceremony (Q4504495), seminar (Q504703), campaign (Q6056746), recording session (Q98216532)

**Facility** (narrower than Location)

- buildings and structures: building of public administration (Q1220959), airport (Q1248784), facility (Q13226383), palace (Q16560), military base (Q245016), attraction (Q2800000), building (Q41176), workshop (Q656720), built structure (Q811979), mine (Q820477), factory (Q83405)
- burial places: cemetery, burial plot, or tomb (Q16859021), cemetery (Q39614), sarcophagus (Q48634), unmarked grave (Q567603), funerary structure (Q6023295)
- medical and residential facilities: hospital (Q16917), medical facility (Q4260475), residential facility (Q67140121), nursing home (Q837142)
- places of detention: fort (Q1785071), prison (Q40357), Xinjiang internment camps (Q55506436), citadel (Q88291), keep (Q91165)
- religious houses: convent (Q1128397), monastery (Q44613)

**Film** (narrower than Creative work)

- films: film (Q11424), film series (Q24856), film dubbing (Q26204053)

**Group**

- families and couples: duo (Q10648343), sibling duo (Q14073567), twins (Q14756018), group of siblings (Q16979650), couple (Q219160), married couple (Q3046146)
- groups of people: group of humans (Q16334295), community (Q177634), class (Q18204)
- performing and production groups: sports team (Q12973014), cast (Q15267437), comedy troupe (Q18510489), dōjin circle (Q2013644), musical ensemble (Q2088357), musical group (Q215380), dance troupe (Q2393314), theatre troupe (Q2416217), editorial team (Q24354647), editorial board (Q2985386), production team (Q7247847), record production team (Q84310035)

**Human**

- classes of people defined by a role they hold: alumnus (Q508719), special purpose artist (Q59755569), uncredited musical artist (Q60614352)
- humans and persons: human biblical figure (Q20643955), human whose existence is disputed (Q21070568), person (Q215627), human (Q5)

**Location**

- places at sea: at sea (Q55438959), burial at sea (Q630013)
- places in general: location (Q115095765), physical location (Q17334923), geographic location (Q2221906), geographic entity (Q27096213), geographical feature (Q618123), unknown location (Q62077203)
- regions: historical region (Q1620908), zone (Q219858), ghetto in Nazi-occupied Europe (Q2583015), cultural region (Q3502482), continent (Q5107), region (Q82794)

**Musical work** (narrower than Creative work)

- compositions and releases: musical work/composition (Q105543609), single release (Q108352496), group of musical works (Q115473170), musical release (Q2031291), musical work (Q2188189), instrumental composition (Q24887304), dramatico-musical work (Q58483083)

**Occupation**

- occupations and positions: occupation (Q12737077), artisan (Q1294787), job activity (Q192581), profession (Q28640), position (Q4164871), title of authority (Q480319), literary translator (Q9363889)
- religious roles: Islamic religious occupation (Q108377574), religious role (Q4504549), Christian religious occupation (Q63188683), Catholic vocation (Q63188808)

**Organization**

- broadcasters and news agencies: radio station (Q14350), radio channel (Q1474440), broadcaster (Q15265344), television station (Q1616075), news agency (Q192283), television channel (Q2001305)
- companies and publishers: production company (Q11396960), theatre company (Q11812394), manufacturer (Q13235160), corporation (Q167037), record label (Q18127), publishing house (Q2085381), publisher (Q2516866), imprint (Q2608849), talent agency (Q5354754), theatre company (Q742421), software publisher (Q7554349), company (Q783794)
- government bodies: government organization (Q2659904), government agency (Q327333), governing body (Q895526)
- organizations: penal military unit (Q1306981), association (Q15911314), scientific organization (Q16519632), religious community (Q2742167), cultural institution (Q3152824), regional organization (Q4120211), organization (Q43229), defunct organization (Q55097243)

**Product**

- machines and software: robot (Q11012), machine (Q11019), optical telescope (Q35273), software bundle (Q62651817), software (Q7397)
- products and brands: product model (Q10929058), tangible good (Q1485500), artificial object (Q16686448), product (Q2424752), good/s (Q28877), brand (Q431289), group of artificial physical objects (Q66661745), model series (Q811701), race car prototype (Q972011)

**Settlement or region** (narrower than Location)

- administrative units: parish (Q102496), political territorial entity (Q1048835), federated state (Q107390), Roman province (Q182547), former administrative territorial entity (Q19953632), judicial district (Q253836), administrative territorial entity (Q56061), jurisdiction (Q5982983)
- settlements: human settlement (Q486972)

**Written work** (narrower than Creative work)

- legal instruments: treaty (Q131569), proclamation (Q1572600), agreement (Q321839), legislation (Q49371)
- lists: checklist (Q106140535), list (Q12139612), ranked list (Q80793969), word list (Q91828006)
- periodicals: periodical (Q1002697), newspaper (Q11032), magazine (Q41298)
- texts and publications: anthology (Q105420), audiobook (Q106833), audiobook edition (Q122731938), instructional materials (Q1348645), samizdat (Q152416), publication by electronic means (Q15938550), edited volume (Q1711593), chapter (Q1980247), documentary edition (Q2122677), serial (Q2217301), version, edition or translation (Q3331189), written work (Q47461344), document (Q49848), publication (Q732577), manga (Q8274)

### Excluded constraint classes

These constraint classes map to no type. The ontology file lists the same
classes under `excluded_constraint_classes`.

**administrative records and schemes** (5 classes). Registers, certifications, licences, and survey methods.

business register (Q1428914), certification (Q374814), race result (Q54933017), survey methodology (Q814232), license scheme (Q95107111)

**animals and other organisms** (25 classes). Non-human organisms, breeds, and taxa; the 2Wiki relations hold between people, works, organizations, and places.

individual organism (Q10855152), dog (Q144), cat (Q146), group of living things (Q16334298), taxon (Q16521), Hominin fossil (Q18347143), working animal (Q228534), individual animal (Q26401003), Orcinus orca (Q26843), archaic human (Q284851), crab-eating macaque (Q301676), brown bear (Q36341), dog type (Q38672), breed (Q38829), cultivar (Q4886), captive animal (Q57812559), captive mammal (Q57812611), dressage horse (Q60198807), clonal colony (Q611804), domesticated animal (Q622852), organism (Q7239), horse (Q726), animal (Q729), Ursus arctos arctos (Q839769), western lowland gorilla (Q876500)

**conditions and journeys** (2 classes). A condition or a journey, not a place, listed as a place of detention.

house arrest (Q320994), Holocaust train journey (Q61927259)

**culture, language, belief, and practice** (38 classes). Abstract cultural kinds that appear only as subjects of country of origin or founded by; 2Wiki uses those relations for works and organizations.

food preparation technique (Q1039303), field of study (Q1047113), rule (Q1151067), holiday (Q1445650), concept (Q151885), languoid (Q17376908), theory (Q17737), cuisine (Q1778821), teaching method (Q1813494), song form (Q1824109), religious movement (Q1826286), music genre (Q188451), type of food or dish (Q19861951), food (Q2095), cultural movement (Q2198855), human activity (Q24902509), custom (Q251777), subculture (Q264965), industry (Q268592), type of sport (Q31629), hairstyle (Q327496), dialect (Q33384), sport (Q349), teaching methodology (Q350453), dance move (Q384748), language (Q4113741), genre (Q483394), social movement (Q49773), intangible cultural heritage (Q59544), branch of pseudoscience (Q60031086), music tradition (Q60733114), religion or world view (Q71966963), ideology (Q7257), economic activity (Q8187769), writing system (Q8192), tradition (Q82821), musical form (Q862597), religion (Q9174)

**fiction and myth** (62 classes). Fictional, mythical, legendary, and hypothetical classes. 2Wiki answers come from Wikipedia articles about real subjects; a fictional or mythical entity is still typed by what it is described as.

fictional technology (Q1055307), type of fictional character (Q112265308), fictional country (Q1145276), imaginary character (Q115537581), fictional analog of an occupation (Q115580828), fictional product model (Q116680403), fictional work (Q124301146), legendary figure (Q13002315), animal role (Q135106502), group of fictional characters (Q14514600), fictional organization (Q14623646), fictional entity (Q14897293), fictional creative work (Q15306849), abstract being (Q15619164), fictional human (Q15632617), fictional educational institution (Q15690029), video game character (Q1569167), animated character (Q15711870), television character (Q15773317), class of fictional entities (Q15831596), role (Q1707847), fictional profession (Q17305127), fictional religion (Q17364638), deity (Q178885), fictional vessel (Q18670171), hypothetical entity (Q18706315), mythical object (Q20203727), personification (Q207174), group of mythical characters (Q20830276), figure that may or may not be fictional (Q21070598), fictional group of siblings (Q21191150), animalisation (Q2135501), fictional office, position, or title (Q21451536), mythical creature (Q2239243), mythological Greek character (Q22988604), mythical animal (Q24334299), mythical entity (Q24334685), mythical humanoid race (Q24533670), fictional planet (Q2775969), fictional organism (Q30017383), mythical location (Q3238337), character (Q3241972), metamorphosis (Q33753), processional giant (Q340069), fictional animal character (Q3542731), fictional location (Q3895768), mythical character (Q4271324), fictional religious occupation (Q47472256), humanoid (Q502931), fictional company (Q5446565), country in a fiction work (Q57662985), fictional radio station (Q60153785), fictional award (Q60466213), fictional human formerly considered to be historical (Q64520857), prosopographical phantom (Q64643615), virtual character (Q65209857), fictional musical ensemble (Q6619719), fictional artificial intelligence (Q66481339), fictional book (Q74574), hypothetical person (Q75855169), fictional potion (Q87370199), character (Q95074)

**generic, structural, and metaclasses** (25 classes). Classes too general to be a type (agent, physical object, system), unions of listed types (person or organization), Wikimedia-internal classes, and classes of classes (ship type).

level (Q1046315), person or organization (Q106559804), type of musical instrument (Q110295396), type of educational institution (Q112872396), Item (Q121033050), science project (Q1298668), Wikimedia list article (Q13406463), plan (Q1371819), coat of arms (Q14659), former entity (Q15893266), project (Q170584), Wikimedia internal item (Q17442446), optical illusion (Q174923), family tree (Q189977), education program (Q2023606), government program (Q22222786), ship type (Q2235308), physical object (Q223557), agent (Q24229398), collection (Q2668072), statement (Q2684591), concrete object (Q4406616), system (Q58778), individual (Q795052), symbol (Q80071)

**human remains and pre-birth cases** (5 classes). Edge cases of the human class that do not appear as 2Wiki answers.

miscarried child (Q117463454), bog body (Q199414), stillborn child (Q2345820), human fetus (Q26513), human head (Q3409626)

**names and terms** (11 classes). Names and words rather than the things they name.

family name (Q101352), professional name (Q11415657), character sequence (Q117009251), neologism (Q130989), collective pseudonym (Q16017119), phrase (Q187931), term (Q1969448), given name (Q202444), demonym (Q217438), slang term (Q42298422), pseudonym (Q61002)

**online accounts, services, and software artefacts** (11 classes). Accounts, channels, services, voice banks, and AI models; none is a 2Wiki answer type.

social media account (Q102345381), generative artificial intelligence (Q117246174), artificial intelligence model (Q117349473), telematics service (Q124030631), voice bank (Q134612820), unspecified voicebank (Q141245227), YouTube channel (Q17558136), software bug (Q179550), Vocaloid (Q550596), humanoid robot (Q584529), content delivery network (Q72588)

**peoples and legal statuses** (8 classes). Ethnic groups, nations, nationality, and citizenship. Country of citizenship points at a Country in 2Wiki; these classes name the status, not the place.

internationality (Q1072012), nationality (Q231002), ethnic minority group (Q2531956), ethnic group (Q41710), citizenship (Q42138), ethnolinguistic group (Q4533081), nation (Q6266), federally recognized Native American tribe in the United States (Q7840353)

**vessels and off-world places** (5 classes). Ships and astronomical places, listed as birth or detention places for rare cases.

ship (Q11446), vessel (Q16391167), naval vessel (Q177597), orbit (Q4130), astronomical object (Q6999)

## Relation types

"Source" says where each end comes from:

- `constraint`: Wikidata type constraints.
- `datatype`: the time datatype, for date ranges (D6).
- `manual`: set by hand; see below.

The domains and ranges keep everything the constraints allow, so some are
wide. For example, `employer` admits 11 types, because Wikidata allows a
television program or a university as an employer.

| Relation | Property | Domain | Range | Source |
|---|---|---|---|---|
| award received | P166 award received | Group, Human | Award, Occupation | manual / constraint |
| cause of death | P509 cause of death | Human | Cause of death | constraint |
| child | P40 child | Group, Human | Group, Human | constraint |
| composer | P86 composer | Creative work, Musical work | Group, Human | constraint |
| country | P17 country | Location, Organization | Country, Location, Settlement or region | manual / constraint |
| country of citizenship | P27 country of citizenship | Group, Human | Country, Settlement or region | constraint |
| country of origin | P495 country of origin | Creative work, Event, Group, Product, Written work | Country, Location, Organization, Settlement or region | constraint |
| creator | P170 creator | Creative work, Event, Facility, Product, Written work | Group, Human, Occupation, Organization, Product | constraint |
| date of birth | P569 date of birth | Human | Date | constraint / datatype |
| date of death | P570 date of death | Group, Human | Date | constraint / datatype |
| director | P57 director | Broadcast program, Creative work, Film, Musical work, Written work | Group, Human | constraint |
| doctoral advisor | P184 doctoral advisor | Human | Human | constraint |
| editor | P98 editor | Creative work, Group, Organization, Written work | Human, Organization | constraint |
| educated at | P69 educated at | Group, Human | Educational institution, Event, Facility, Organization | constraint |
| employer | P108 employer | Group, Human | Broadcast program, Creative work, Educational institution, Event, Facility, Group, Human, Organization, Product, Settlement or region, Written work | constraint |
| father | P22 father | Group, Human | Human | constraint |
| founded by | P112 founder | Award, Creative work, Event, Facility, Group, Location, Occupation, Organization, Product, Written work | Group, Human, Organization | constraint |
| has part | P527 has part(s) | Group | Human | manual |
| inception | P571 inception | Organization | Date | manual / datatype |
| manufacturer | P176 manufacturer | Event, Musical work, Product | Facility, Human, Occupation, Organization | constraint |
| mother | P25 mother | Human | Human | constraint |
| occupation | P106 occupation | Group, Human, Product | Occupation | constraint |
| performer | P175 performer | Creative work, Event, Human | Group, Human, Organization | constraint |
| place of birth | P19 place of birth | Group, Human | Facility, Location | constraint |
| place of burial | P119 place of burial | Group, Human | Country, Facility, Location | constraint |
| place of death | P20 place of death | Group, Human | Educational institution, Event, Facility, Location | constraint |
| place of detention | P2632 place of detention | Event, Group, Human | Facility, Location, Organization, Settlement or region | constraint |
| presenter | P371 presenter | Creative work, Event, Organization | Human | constraint |
| producer | P162 producer | Creative work | Group, Human, Organization | constraint |
| publication date | P577 publication date | Creative work, Event, Musical work, Product, Written work | Date | constraint / datatype |
| publisher | P123 publisher | Creative work, Musical work, Product, Written work | Award, Creative work, Educational institution, Organization, Product, Settlement or region, Written work | constraint |
| sibling | P3373 sibling | Group, Human | Group, Human | constraint |
| spouse | P26 spouse | Human | Human | constraint / manual |
| student of | P1066 student of | Group, Human | Group, Human | constraint |

### Ends set by hand

| Relation | End | Types | Reason |
|---|---|---|---|
| award received | domain | Group, Human | P166 has no subject type constraint. Dev subjects are people and groups, e.g. 'Steve Vai' and 'Slayer' (Grammy Award). |
| country | domain | Location, Organization | P17 has no subject type constraint. Dev subjects are places, facilities, and organizations, e.g. 'Cabixi River', 'Gillam Airport', 'Empire Kosher'. |
| spouse | range | Human | P26 has no value type constraint. Dev objects are people, e.g. 'Stephen King'. |
| has part | domain | Group | P527 has no type constraints. All 17 dev triples link a band to a member, e.g. 'XYZ' has part 'Chris Squire'. |
| has part | range | Human | As for the domain: every dev object is a band member. |
| inception | domain | Organization | P571 has no type constraints. Dev subjects are organizations and schools, e.g. 'Sigma Xi', 'Korn Ferry', 'Whitehorse Manor Junior School'. |

## Validation

This check is for information only; it was not used to tune the type set.
Method:

1. Take every entity QID (subjects and objects, not `date_information`) in the
   `evidences_id` of the study50 questions: 85 QIDs from the 29 questions that
   have `evidences_id`. The cap of 200 lookups was not reached.
2. Look up each entity's instance of (P31).
3. Follow each P31 class up subclass of (P279), at most 5 steps, until it
   reaches a class mapped to a type. The type at the smallest number of steps
   wins; ties keep all types.

**Result: 85 of 85 entities (100.0%) fall into a type in the set.** That is
above the 80 percent threshold, so the type set was not changed.

- 74 entities matched at their P31 class directly, 10 after one P279 step, and
  1 after two.
- By type: Human 60, Settlement or region 7, Film 6, Country 4, Location 3,
  Group 2, Educational institution 1, Organization 1, Musical work 1, Written
  work 1.
- One university matched Educational institution and Organization at the same
  step and is counted under both.

Observations:

- **Cities fall into Settlement or region.** Toronto, Reykjavík, New York,
  Los Angeles, and Ayutthaya reach it after one step, through classes such as
  "big city" or "municipality", whose Wikidata superclasses include
  administrative territorial entity. Paris reaches Location. Before the merge
  (D5), these five cities reached Administrative region and none reached
  Settlement.
- **The sample is small and mostly people.** Comparison and
  bridge_comparison questions have `evidences_id` only for country relations
  (`docs/notes/2wiki-inspection.md`), so 21 of the 50 study50 questions
  contribute no entities. Of the 85 entities, 60 are humans.

## Relation coverage (AC2)

Coverage is the share of evidence triples (`evidences` in
`data/raw/2wiki/dev.json`) whose relation label is a relation type in the
ontology. For study50, the question IDs come from
`data/subsets/manifest.json`.

| Scope | Questions | Evidence triples | Distinct relations | Covered triples | Coverage | Uncovered |
|---|---|---|---|---|---|---|
| study50 | 50 | 126 | 18 | 126 | 100.0% | none |
| dev | 12,576 | 31,120 | 34 | 31,120 | 100.0% | none |

| Relation | study50 triples | dev triples |
|---|---|---|
| director | 28 | 7,592 |
| date of birth | 20 | 4,976 |
| father | 16 | 3,203 |
| date of death | 16 | 2,551 |
| publication date | 10 | 2,184 |
| country of citizenship | 1 | 2,146 |
| place of birth | 5 | 1,648 |
| spouse | 8 | 1,198 |
| mother | 8 | 1,156 |
| place of death | 2 | 1,015 |
| country of origin | 4 | 754 |
| country | 2 | 657 |
| performer | 1 | 426 |
| composer | 0 | 262 |
| educated at | 1 | 249 |
| place of burial | 1 | 156 |
| employer | 0 | 148 |
| inception | 0 | 143 |
| award received | 0 | 125 |
| child | 1 | 107 |
| sibling | 1 | 106 |
| cause of death | 0 | 78 |
| founded by | 0 | 78 |
| producer | 0 | 42 |
| publisher | 0 | 34 |
| occupation | 0 | 19 |
| creator | 0 | 18 |
| has part | 0 | 17 |
| editor | 1 | 12 |
| presenter | 0 | 6 |
| place of detention | 0 | 5 |
| student of | 0 | 5 |
| manufacturer | 0 | 3 |
| doctoral advisor | 0 | 1 |

**Uncovered relations: none,** in study50 or in the full dev set.

## Not determined from the data

- **Domains and ranges for the six hand-set ends.** The Wikidata constraints
  give no type for them; the choices rest on dev examples.
- **Which classes are noise.** Wikidata constraints list everything that
  editors allow, including fictional and animal cases. Excluding them is a
  judgment that 2Wiki entities are real-world Wikipedia subjects. The
  validation sample, 85 entities, is consistent with this but too small to
  confirm it for all 12,576 dev questions.
- **Whether finer or coarser types would help extraction.** The 18 types
  from constraint classes follow from those classes and the 10 to 30 bound,
  and Date was added for the date relations (D6); SCRUM-17 does not test
  alternatives.
- **Kinship composition (D2).** Whether adding composition rules would help
  inference questions is left for a later story.
