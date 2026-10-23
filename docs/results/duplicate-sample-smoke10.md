# Duplicate sample, smoke10 (SCRUM-21)

Written by `scripts/graph_metrics.py`. 20 of the 10 baseline and 18 ontology duplicate clusters were drawn without replacement with `random.Random(694)`, and one flagged pair was drawn from each with the same generator. Drawing clusters first keeps a large cluster from filling the sample: the largest has 7 entities and would contribute 21 of the 50 flagged pairs to a uniform draw. A pair is two entities in the same duplicate cluster; the reason is the rule that linked them (see the script docstring).

Pairs 1-2, 4-10, and 12-19 were labeled from the entity names; pairs 3, 11, and 20 were decided by Lucas from the source sentences. All labels were reviewed by Lucas.

y means both names refer to the same real-world entity in the source paragraphs; n means they do not. Precision = y / (y + n).

| # | Graph | Entity A | Entity B | Reason | Same entity? (y/n) | Why |
|---|---|---|---|---|---|---|
| 1 | baseline | Athenry, County Galway, Ireland | County Galway | containment | n | A town and the county that contains it. |
| 2 | baseline | Cabin by the Lake | Return to Cabin by the Lake | containment | n | A film and its sequel. |
| 3 | baseline | Joystick | Joystick (song) | normalized match | y | The same 1983 Dazz Band song, named in the band's paragraph and in the song's own paragraph. |
| 4 | baseline | La Hora de los Hornos | La hora de los hornos (The Hour of the Furnaces) | normalized match | y | The same film; the second name adds the English title. |
| 5 | baseline | Siemowit III | Siemowit III of Masovia | containment | y | The same duke, with and without his territorial name. |
| 6 | baseline | Sir William Burke, younger son of Ulick Burke, 3rd Earl of Clanricarde | Ulick Burke, 3rd Earl of Clanricarde | containment | n | A son and his father: "younger son of" names the father inside the son's entity. |
| 7 | baseline | The Presidents of the United States of America | United States | containment | n | A band whose name contains a country name, and the country. |
| 8 | ontology | Abd Manaf | Hashim ibn' Abd Manaf | containment | n | A father and his son: "ibn" names the father inside the son's name. |
| 9 | ontology | Cabin by the Lake | Return to Cabin by the Lake | containment | n | A film and its sequel. |
| 10 | ontology | Dazz Band | The Dazz Band | normalized match | y | The same band, with and without "The". |
| 11 | ontology | Earl of St. Albans | Ulick MacRichard Burke, 1st Marquess of Clanricarde, 5th Earl of Clanricarde, 2nd Earl of St Albans | containment | n | A title and a person who later held it; the title node comes from his father's paragraph. |
| 12 | ontology | Fakhruddin Shaheed | Syedi Fakhruddin Shaheed | containment | y | The same person, with and without the honorific "Syedi". |
| 13 | ontology | Frances Walsingham and Richard Burke, Earl of Clanricarde | Richard Burke, Earl of Clanricarde | containment | n | Two people joined with "and" into one entity, and one of the two. |
| 14 | ontology | King Maha Chakkraphat | Maha Chakkraphat | containment | y | The same king, with and without "King". |
| 15 | ontology | King Władysław II Jagiełło of Poland | Władysław II Jagiełło | containment | y | The same king, with and without "King" and "of Poland". |
| 16 | ontology | Place of Origin | place of origin | normalized match | n | A relation label turned into an entity, not a named thing. |
| 17 | ontology | Siemowit III | Siemowit III of Masovia | containment | y | The same duke, with and without his territorial name. |
| 18 | ontology | Sir Philip Sidney | Sir Philip Sidney and Robert Devereaux, Earl of Essex | containment | n | Two people joined with "and" into one entity, and one of the two. |
| 19 | ontology | Syedna Mohammad Burhanuddin | Syedna Taher Saifuddin bin Syedna Mohammad Burhanuddin | containment | n | A father and his son: "bin" names the father inside the son's name. |
| 20 | ontology | The Time | Time | normalized match | n | The band The Time (Paul Peterson paragraph) and Time magazine (Björk paragraph). |

## Precision

| Graph | Same entity (y) | Pairs | Precision |
|---|---|---|---|
| baseline | 3 | 7 | 3/7 (42.9%) |
| ontology | 5 | 13 | 5/13 (38.5%) |
| both | 8 | 20 | 8/20 (40.0%) |
