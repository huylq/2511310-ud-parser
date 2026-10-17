# Mapping VTB labels to UD_DEPREL

VTB commit: `3c971fd1c5d03561e00b267d3d0057b81a9bea84`.

Inventory of every label observed in train/dev/test before projection.
Take the part before the first colon; every target label is checked against
the interface's UD_DEPREL. A label absent from VTB is not invalid merely
because it is unobserved if the interface still permits it.

| VTB label | Output label | Train | Dev | Test | Total |
|---|---|---:|---:|---:|---:|
| `acl` | `acl` | 94 | 67 | 85 | 246 |
| `acl:relcl` | `acl` | 1 | 20 | 2 | 23 |
| `acl:subj` | `acl` | 344 | 853 | 142 | 1339 |
| `acl:tmod` | `acl` | 63 | 122 | 51 | 236 |
| `acl:tonp` | `acl` | 31 | 51 | 15 | 97 |
| `advcl` | `advcl` | 282 | 373 | 211 | 866 |
| `advcl:objective` | `advcl` | 130 | 112 | 64 | 306 |
| `advmod` | `advmod` | 1094 | 1342 | 752 | 3188 |
| `advmod:adj` | `advmod` | 127 | 306 | 153 | 586 |
| `advmod:dir` | `advmod` | 8 | 1 | 9 | 18 |
| `advmod:neg` | `advmod` | 243 | 266 | 182 | 691 |
| `amod` | `amod` | 457 | 434 | 235 | 1126 |
| `appos` | `appos` | 59 | 104 | 27 | 190 |
| `appos:nmod` | `appos` | 36 | 111 | 26 | 173 |
| `aux` | `aux` | 136 | 191 | 86 | 413 |
| `aux:pass` | `aux` | 139 | 182 | 45 | 366 |
| `case` | `case` | 1121 | 1460 | 565 | 3146 |
| `cc` | `cc` | 407 | 407 | 224 | 1038 |
| `ccomp` | `ccomp` | 201 | 250 | 107 | 558 |
| `clf` | `clf` | 85 | 118 | 47 | 250 |
| `clf:det` | `clf` | 348 | 336 | 203 | 887 |
| `compound` | `compound` | 520 | 1288 | 154 | 1962 |
| `compound:adj` | `compound` | 2 | 20 | 1 | 23 |
| `compound:amod` | `compound` | 7 | 74 | 17 | 98 |
| `compound:apr` | `compound` | 1 | 0 | 1 | 2 |
| `compound:atov` | `compound` | 14 | 10 | 4 | 28 |
| `compound:dir` | `compound` | 98 | 144 | 35 | 277 |
| `compound:pron` | `compound` | 5 | 23 | 18 | 46 |
| `compound:prt` | `compound` | 32 | 22 | 35 | 89 |
| `compound:redup` | `compound` | 3 | 0 | 1 | 4 |
| `compound:svc` | `compound` | 129 | 292 | 90 | 511 |
| `compound:verbnoun` | `compound` | 7 | 31 | 26 | 64 |
| `compound:vmod` | `compound` | 274 | 298 | 149 | 721 |
| `compound:z` | `compound` | 11 | 5 | 1 | 17 |
| `conj` | `conj` | 745 | 1259 | 468 | 2472 |
| `cop` | `cop` | 194 | 185 | 102 | 481 |
| `csubj` | `csubj` | 42 | 48 | 20 | 110 |
| `csubj:asubj` | `csubj` | 7 | 7 | 6 | 20 |
| `csubj:pass` | `csubj` | 9 | 1 | 0 | 10 |
| `csubj:vsubj` | `csubj` | 18 | 25 | 13 | 56 |
| `dep` | `dep` | 3 | 1 | 3 | 7 |
| `det` | `det` | 320 | 543 | 189 | 1052 |
| `det:pmod` | `det` | 316 | 254 | 189 | 759 |
| `discourse` | `discourse` | 145 | 150 | 134 | 429 |
| `dislocated` | `dislocated` | 10 | 18 | 9 | 37 |
| `expl` | `expl` | 0 | 4 | 0 | 4 |
| `fixed` | `fixed` | 6 | 18 | 8 | 32 |
| `flat` | `flat` | 3 | 3 | 10 | 16 |
| `flat:date` | `flat` | 48 | 65 | 9 | 122 |
| `flat:foreign` | `flat` | 0 | 7 | 0 | 7 |
| `flat:name` | `flat` | 6 | 0 | 2 | 8 |
| `flat:number` | `flat` | 23 | 100 | 9 | 132 |
| `flat:redup` | `flat` | 3 | 0 | 0 | 3 |
| `flat:time` | `flat` | 13 | 6 | 2 | 21 |
| `iobj` | `iobj` | 17 | 6 | 11 | 34 |
| `list` | `list` | 21 | 24 | 0 | 45 |
| `mark` | `mark` | 299 | 512 | 294 | 1105 |
| `mark:pcomp` | `mark` | 76 | 106 | 39 | 221 |
| `nmod` | `nmod` | 740 | 1304 | 461 | 2505 |
| `nmod:poss` | `nmod` | 233 | 253 | 101 | 587 |
| `nsubj` | `nsubj` | 1577 | 1519 | 958 | 4054 |
| `nsubj:nn` | `nsubj` | 4 | 104 | 14 | 122 |
| `nsubj:pass` | `nsubj` | 93 | 103 | 32 | 228 |
| `nsubj:xsubj` | `nsubj` | 5 | 0 | 5 | 10 |
| `nummod` | `nummod` | 533 | 636 | 238 | 1407 |
| `nummod:det` | `nummod` | 0 | 71 | 0 | 71 |
| `obj` | `obj` | 1660 | 1835 | 867 | 4362 |
| `obl` | `obl` | 501 | 460 | 259 | 1220 |
| `obl:about` | `obl` | 33 | 27 | 15 | 75 |
| `obl:adj` | `obl` | 8 | 111 | 17 | 136 |
| `obl:adv` | `obl` | 0 | 3 | 1 | 4 |
| `obl:agent` | `obl` | 21 | 52 | 3 | 76 |
| `obl:comp` | `obl` | 146 | 555 | 163 | 864 |
| `obl:iobj` | `obl` | 48 | 52 | 27 | 127 |
| `obl:tmod` | `obl` | 379 | 552 | 207 | 1138 |
| `obl:with` | `obl` | 69 | 72 | 49 | 190 |
| `parataxis` | `parataxis` | 220 | 182 | 128 | 530 |
| `punct` | `punct` | 2931 | 3517 | 1703 | 8151 |
| `root` | `root` | 1400 | 1123 | 800 | 3323 |
| `vocative` | `vocative` | 6 | 6 | 2 | 14 |
| `xcomp` | `xcomp` | 710 | 917 | 329 | 1956 |
| `xcomp:adj` | `xcomp` | 64 | 36 | 31 | 131 |
| `xcomp:dir` | `xcomp` | 0 | 17 | 0 | 17 |
| `xcomp:vcomp` | `xcomp` | 1 | 0 | 2 | 3 |

Projection adds within-word `dep` arcs; those added arcs are not included
in the source-label counts. Base-label model predictions are not expanded
back into VTB subtypes when producing output.
