# Duplicate sample, smoke10 (SCRUM-21)

Written by `scripts/graph_metrics.py`. 20 of the 10 baseline and 18 ontology duplicate clusters were drawn without replacement with `random.Random(694)`, and one flagged pair was drawn from each with the same generator. Drawing clusters first keeps a large cluster from filling the sample: the largest has 7 entities and would contribute 21 of the 50 flagged pairs to a uniform draw. A pair is two entities in the same duplicate cluster; the reason is the rule that linked them (see the script docstring).

Fill in the last column with y if both names refer to the same real-world entity in the source paragraphs, n otherwise. Precision = y / (y + n).

| # | Graph | Entity A | Entity B | Reason | Same entity? (y/n) |
|---|---|---|---|---|---|
| 1 | baseline | Athenry, County Galway, Ireland | County Galway | containment |  |
| 2 | baseline | Cabin by the Lake | Return to Cabin by the Lake | containment |  |
| 3 | baseline | Joystick | Joystick (song) | normalized match |  |
| 4 | baseline | La Hora de los Hornos | La hora de los hornos (The Hour of the Furnaces) | normalized match |  |
| 5 | baseline | Siemowit III | Siemowit III of Masovia | containment |  |
| 6 | baseline | Sir William Burke, younger son of Ulick Burke, 3rd Earl of Clanricarde | Ulick Burke, 3rd Earl of Clanricarde | containment |  |
| 7 | baseline | The Presidents of the United States of America | United States | containment |  |
| 8 | ontology | Abd Manaf | Hashim ibn' Abd Manaf | containment |  |
| 9 | ontology | Cabin by the Lake | Return to Cabin by the Lake | containment |  |
| 10 | ontology | Dazz Band | The Dazz Band | normalized match |  |
| 11 | ontology | Earl of St. Albans | Ulick MacRichard Burke, 1st Marquess of Clanricarde, 5th Earl of Clanricarde, 2nd Earl of St Albans | containment |  |
| 12 | ontology | Fakhruddin Shaheed | Syedi Fakhruddin Shaheed | containment |  |
| 13 | ontology | Frances Walsingham and Richard Burke, Earl of Clanricarde | Richard Burke, Earl of Clanricarde | containment |  |
| 14 | ontology | King Maha Chakkraphat | Maha Chakkraphat | containment |  |
| 15 | ontology | King Władysław II Jagiełło of Poland | Władysław II Jagiełło | containment |  |
| 16 | ontology | Place of Origin | place of origin | normalized match |  |
| 17 | ontology | Siemowit III | Siemowit III of Masovia | containment |  |
| 18 | ontology | Sir Philip Sidney | Sir Philip Sidney and Robert Devereaux, Earl of Essex | containment |  |
| 19 | ontology | Syedna Mohammad Burhanuddin | Syedna Taher Saifuddin bin Syedna Mohammad Burhanuddin | containment |  |
| 20 | ontology | The Time | Time | normalized match |  |

Precision: _ / 20
