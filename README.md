# scoreSEND
R Package implementing best practices for scoring/normalizing SEND data for ingestion by ML models.

# This package was derived from sendSummarizer.
scoreSEND is an R package that includes functions to calculate toxicity score
of a given repeat-dose toxicological study. Data can be read from a **SQLite database** or from **raw XPT files**. For XPT, provide the path to a directory that directly contains the domain files (e.g. `study_folder/bw.xpt`, `dm.xpt`, `lb.xpt`) for one study; all files in that directory are treated as one study.  

- paper
- [paper link](https://academic.oup.com/toxsci/article/200/2/277/7690167?login=true) 

- Poster
- [poster](https://www.lexjansen.com/css-us/2022/POS_PP23.pdf)  



# Installation

```
# Install from GitHub
install.packages("devtools")
devtools::install_github('phuse-org/scoreSEND')
```

### For development

Clone the repo, then load the package:

```
setwd('scoreSEND')
devtools::load_all(".")
```


# More examples

## Using raw XPT files (recommended workflow)

Use a directory that directly contains the XPT domain files for one study (e.g. `bw.xpt`, `dm.xpt`, `lb.xpt` in that folder). For multiple studies under a parent folder, list subdirectories with `list.files(..., full.names = TRUE)` or `get_study_ids_from_xpt(parent_dir)$study_dir`, then loop.

Typical workflow (same pattern as `test_script.R`): compile once per study, pass that table into each scorer, and optionally call `get_all_score` for all domains at once.

```
devtools::load_all()

Domains <- c("bw", "lb", "mi")
study_dirs <- list.files("sample_data", full.names = TRUE)
# or: study_dirs <- get_study_ids_from_xpt("sample_data")$study_dir

for (study_dir in study_dirs) {
  Doses <- get_doses(xpt_dir = study_dir)
  treatmentGroups <- get_treatment_group(xpt_dir = study_dir)
  Compiled_Data <- get_compile_data(xpt_dir = study_dir)

  BWscores <- get_bw_score(
    xpt_dir = study_dir,
    master_CompileData = Compiled_Data,
    score_in_list_format = FALSE
  )
  BWscoresList <- get_bw_score(
    xpt_dir = study_dir,
    master_CompileData = Compiled_Data,
    score_in_list_format = TRUE
  )

  LBscores <- get_lb_score(
    xpt_dir = study_dir,
    master_CompileData = Compiled_Data,
    score_in_list_format = FALSE
  )
  LBscoresList <- get_lb_score(
    xpt_dir = study_dir,
    master_CompileData = Compiled_Data,
    score_in_list_format = TRUE
  )

  MIscores <- get_mi_score(
    xpt_dir = study_dir,
    master_CompileData = Compiled_Data,
    score_in_list_format = FALSE
  )
  MIscoresList <- get_mi_score(
    xpt_dir = study_dir,
    master_CompileData = Compiled_Data,
    score_in_list_format = TRUE
  )

  Scores <- get_all_score(
    xpt_dir = study_dir,
    domain = Domains,
    score_in_list_format = FALSE
  )
  scoresList <- get_all_score(
    xpt_dir = study_dir,
    domain = Domains,
    score_in_list_format = TRUE
  )
}
```

For details on how each score is calculated and how to use their arguments, see **Scoring functions** below.

## Using a SQLite database

```
path_db <- "C:/directory/send.db"
studyid <- "112344"

compile <- get_compile_data(studyid, path_db)
get_treatment_group(studies = studyid, db_path = path_db)

mi_score <- get_mi_score(studyid, path_db, master_CompileData = compile)
lb_score <- get_lb_score(studyid, path_db, master_CompileData = compile)
bw_score <- get_bw_score(studyid, path_db, master_CompileData = compile)
all_score <- get_all_score(studyid, path_db, domain = c("lb", "bw", "mi"))
```


## get_treatment_group

**get_treatment_group** classifies **SETCD** cohorts using **DS** disposition (**DSDECOD**). For each non-TK set, if any subject has that disposition, the set is labeled:

- **RECOVERY SACRIFICE** → `recovery_group`
- **INTERIM SACRIFICE** → `interim_group`
- **TERMINAL SACRIFICE** → `treatment_group`

If a set has more than one disposition type across animals, classification follows a single branch: **recovery** first, then **interim**, then **terminal**.

By default, **get_compile_data** keeps only subjects whose **SETCD** is in **`treatment_group`** (terminal-sacrifice cohorts). That means **recovery** and **interim** sets are excluded unless you set **`terminal_setcds_only = FALSE`** (all non-TK DM subjects; no terminal SETCD restriction). You can still call **get_treatment_group** directly to inspect `recovery_group`, `interim_group`, and related labels.

**TK identification** (rats): **get_treatment_group** may label TK SETCDs via TX `TKDESC` when present, otherwise via PC/pooldef. Separately, **get_compile_data** removes TK **subjects** using PP pool IDs joined to pooldef (see compile steps below). These are related but not identical mechanisms.

For each study, the returned list includes:

| Element | Meaning |
|---------|---------|
| `species` | Species from TS |
| `setcd` | All SETCD values in DM |
| `treatment_group` | SETCDs classified as **TERMINAL SACRIFICE** (non-TK sets only) |
| `recovery_group` | SETCDs classified as **RECOVERY SACRIFICE** |
| `interim_group` | SETCDs classified as **INTERIM SACRIFICE** |
| `TK_group` | (Rats only, when TK can be inferred) SETCDs classified as toxicokinetic |
| `four_trtm_group` | (Top-level list entry) Study IDs with exactly four terminal treatment groups |


# Scoring functions

The package provides three main scoring functions: **get_bw_score** (body weight), **get_lb_score** (laboratory / clinical chemistry), and **get_mi_score** (microscopic findings). All three use the same data-source options (SQLite or XPT directory), can accept precomputed compile data via `master_CompileData`, and control return shape with `score_in_list_format` (long vs wide). **get_all_score** runs the requested domains and returns a list of those results.


## get_compile_data and compile data

**get_compile_data** builds the subject-level table ("compile data") that the scoring functions use to decide which subjects to score and which arm (ARMCD) each subject belongs to.

### What get_compile_data returns

A data frame with one row per subject and columns **STUDYID**, **USUBJID**, **Species**, **SEX**, **ARMCD**, **SETCD**. **TK** animals are excluded on rat studies when inferred from PP/pooldef. With the default **`terminal_setcds_only = TRUE`**, only **SETCD** values in **`treatment_group`** from **get_treatment_group** are kept (terminal-sacrifice cohorts; recovery and interim excluded). **ARMCD** is derived from ordered TRTDOS dose (vehicle, LD, MD or MD1/MD2/…, HD, or Both). Each subject has a single ARMCD label used by the score functions.

### How get_compile_data works

**fake_study = TRUE (SENDsanitizer-style studies)**

- **Data**: DM and TS only (from SQLite or XPT).
- **Processing**: Normalize "Control" to "vehicle"; keep all treatment arms in DM (no filter to vehicle/HD). Add Species from TS. `terminal_setcds_only` is ignored.
- **Output**: One row per subject; ARMCD comes from the DM ARM column (all arms present).

**fake_study = FALSE (main path)**

- **Data**: DM, TS, TX, BW, pooldef, PP (from SQLite or XPT). The **DS** domain is not read here; cohort phase is applied via **`get_treatment_group`** when **`terminal_setcds_only`** is TRUE.
- **Steps** (in order):
  1. **Build CompileData** from DM (STUDYID, Species, USUBJID, SEX, ARMCD, SETCD).
  2. **Remove TK animals** (rat studies only): Exclude USUBJIDs that appear in pooldef for pools listed in PP (TK pools).
  3. **Terminal SETCD filter** (default **`terminal_setcds_only = TRUE`**): Keep only subjects whose **SETCD** is in **`treatment_group`** from **get_treatment_group** (recovery / interim / terminal precedence among non-TK sets; only terminal SETCDs retained). Use **`terminal_setcds_only = FALSE`** to skip this step (all non-TK DM subjects; recovery and interim included if present in DM).
  4. **Dose ranking**: Use TX (TXPARMCD == "TRTDOS") to get one dose value per (STUDYID, SETCD). Per study, sort distinct dose values and assign **ARMCD** = "vehicle" (lowest), "HD" (highest), "Both" (single distinct level), "LD" / "MD" / "MD1" / "MD2" / … for intermediate levels (see package implementation). Inner-join this to the cleaned subject list so every remaining subject gets exactly one ARMCD.
- **Output**: One row per subject; columns STUDYID, USUBJID, Species, SEX, ARMCD, SETCD.

**Arguments**: `studyid` and `path_db` are required when using SQLite; omit them when using `xpt_dir`. `xpt_dir` is the path to a directory containing XPT files for one study (e.g. dm.xpt, ts.xpt, tx.xpt). `fake_study`: if TRUE, use the simplified DM+TS path and keep all arms; if FALSE, use the full path with TX/PP/pooldef and dose ranking. **`terminal_setcds_only`**: if TRUE (default), apply the terminal **`treatment_group`** SETCD filter after TK removal; if FALSE, omit it. **`get_doses`** accepts the same parameter and stays aligned with compile data.

### How the scoring functions use compile data

- **Who gets scored**: Each scoring function restricts to subjects whose USUBJID is in the compile data. With default compile settings, that means non-TK subjects whose SETCD is in **`treatment_group`** (when **`terminal_setcds_only`** is TRUE), each with an ARMCD.
- **ARMCD usage**: **get_bw_score** and **get_lb_score** use ARMCD == "vehicle" to compute mean and SD for z-scores; scores are then computed for all subjects (all arms) in the compile data. **get_mi_score** uses ARMCD (and STUDYID, USUBJID, SETCD, etc.) for merging and for incidence-by-arm logic; scores are produced for all subjects in the compile data.
- **master_CompileData**:
  - **get_lb_score** and **get_mi_score**: if you pass a precomputed frame, they skip calling `get_compile_data` again.
  - **get_bw_score**: if you pass a frame, it is used to restrict USUBJIDs when selecting initial and final body weights, but **get_bw_score always calls `get_compile_data` again** before merging ARMCD/SETCD/SEX for the z-score step. Passing compile data still aligns the subject filter with your compile call when defaults match; it does not fully avoid recomputation for BW.
- **terminal_setcds_only**: Available on `get_compile_data`, `get_doses`, each scorer, and `get_all_score`. On scorers / `get_all_score`, it is passed through only when that function builds compile data itself (i.e. when `master_CompileData` is `NULL`, and for BW also on its second compile call).


## get_bw_score

### How the BW score is calculated

- **Data**: BW domain is read; the day column is unified as VISITDY, else BWNOMDY, else BWDY. Only subjects present in compile data (per TK removal and optional terminal **SETCD** filter) are scored.
- **Initial weight** (per subject): The first record with VISITDY == 1; if none, the record with VISITDY &lt; 0 closest to zero; if none, the single record in 1 &lt; VISITDY ≤ 5 with minimum VISITDY; if the only records are VISITDY &gt; 5, initial weight is set to 0.
- **Final weight** (per subject): The record with BWTESTCD == "TERMBW" if present; otherwise, among records with VISITDY &gt; 5, the row with maximum VISITDY.
- **Metric**: `finalbodyweight = |BWSTRESN - BWSTRESN_Init|`.
- **Z-score**: Within each STUDYID, mean and standard deviation are computed from subjects with ARMCD == "vehicle". For all subjects (all treatment arms), `BWZSCORE = (finalbodyweight - mean_vehicle) / sd_vehicle`. The score is **signed** (no absolute value). Vehicle is used only as the reference; scores are produced for every subject.
- **Output**: One score per subject (endpoint is "BW"). No study-level summary table is returned.

### Arguments and return value

| Argument | Description |
|----------|-------------|
| `studyid` | Study identifier. Required when using SQLite; optional when `xpt_dir` is set. |
| `path_db` | Path to the SQLite database. Required for SQLite; omit when using `xpt_dir`. |
| `xpt_dir` | Path to a directory containing XPT files for one study (e.g. `bw.xpt`, `dm.xpt`). When set, `studyid` and `path_db` are not needed for reading data. |
| `fake_study` | If TRUE, compile data is built for SENDsanitizer-style studies (all arms kept). Default FALSE. |
| `master_CompileData` | Optional precomputed compile data. Used to restrict USUBJIDs for weight selection; compile data is still recomputed before the ARMCD merge (see above). |
| `terminal_setcds_only` | Passed to `get_compile_data` when compile data is built; default TRUE. |
| `score_in_list_format` | If FALSE (default), long format: STUDYID, USUBJID, ARMCD, SETCD, endpoint, score, SEX. If TRUE, wide format: USUBJID, STUDYID, BWSTRESN, BWSTRESN_Init, ARMCD, SETCD, SEX, finalbodyweight, BWZSCORE. |


## get_lb_score

### How the LB score is calculated

- **Data**: LB domain; day column is unified as VISITDY, else LBNOMDY, else LBDY. Only records with VISITDY ≥ 1 are used. LBSPEC and LBTESTCD are combined (e.g. "SERUM | ALT"). Only liver-related tests are kept: SERUM, PLASMA, or WHOLE BLOOD for ALT, AST, ALP, GGT, BILI, and ALB. Subjects are restricted to compile data (same TK and terminal **SETCD** rules as **get_compile_data**).
- **Per-subject, per-test**: For each of the six tests, one value per subject is taken: the record with maximum VISITDY per (USUBJID, LBTESTCD).
- **Z-score**: Within each STUDYID, for each test, mean and standard deviation are computed from subjects with ARMCD == "vehicle". For all subjects, `*_zscore = (LBSTRESN - mean_vehicle_*) / sd_vehicle_*`, then the **absolute value** is taken (unlike BW, which keeps a signed z-score).
- **Study-level**: For each test, the average of that test's z-scores over all subjects in the study is computed; then the average is capped to 0–3: if avg ≥ 3 then 3, else if ≥ 2 then 2, else if ≥ 1 then 1, else 0. Study-level averages use all subjects (all arms), not only high dose.
- **Output**: The function returns per-subject data: either long (one row per subject per test) or wide (one row per subject with columns alt_zscore, ast_zscore, alp_zscore, ggt_zscore, bili_zscore, alb_zscore). Study-level scores are computed internally but not returned.

### Arguments and return value

| Argument | Description |
|----------|-------------|
| `studyid` | Study identifier. Required for SQLite; optional when `xpt_dir` is set. |
| `path_db` | Path to the SQLite database. Required for SQLite; omit when using `xpt_dir`. |
| `xpt_dir` | Path to a directory containing XPT files for one study (e.g. `lb.xpt`, `dm.xpt`). |
| `fake_study` | If TRUE, compile data for SENDsanitizer-style studies. Default FALSE. |
| `master_CompileData` | Optional precomputed compile data; if provided, `get_compile_data` is not called again. |
| `terminal_setcds_only` | Passed to `get_compile_data` when compile data is built; default TRUE. |
| `score_in_list_format` | If FALSE (default), long format: STUDYID, USUBJID, ARMCD, SETCD, endpoint, score, SEX. If TRUE, wide format: STUDYID, USUBJID, ARMCD, SETCD, alt_zscore, ast_zscore, alp_zscore, ggt_zscore, bili_zscore, alb_zscore. |


## get_mi_score

### How the MI score is calculated

- **Data**: MI domain; only records with MISPEC containing "LIVER" (case-insensitive) are used. MISEV is normalized to a 0–5 numeric scale (e.g. MINIMAL→1, MILD→2, MODERATE→3, MARKED→4, SEVERE→5; "n OF 4" and "n OF 5" mapped accordingly). Some MISTRESC values are merged (e.g. "CELL DEBRIS" → "CELLULAR DEBRIS", infiltration variants → "Infiltrate"). Subjects are restricted to compile data (same TK and terminal **SETCD** rules as **get_compile_data**).
- **Per-subject, per-finding**: A wide table is built: first six columns are STUDYID, USUBJID, ARMCD, etc.; columns 7 onward are one per finding. Raw severity is transformed: 5→5, &gt;3→3, 3→2, &gt;0→1, else 0.
- **Incidence override** (by study, sex, and arm):
  1. Incidence = proportion of subjects in that arm/sex with the finding.
  2. Subtract the vehicle-arm incidence for the same finding (floor at 0).
  3. Map the adjusted incidence to a score: ≥ 0.75 → 5, ≥ 0.50 → 3, ≥ 0.25 → 2, ≥ 0.10 → 1, else 0.
  4. Raise a subject's finding score only if the current score is **greater than 0** and **less than** the incidence-derived value. Subjects scored 0 for a finding are not raised by incidence alone.
- **Per-subject summary**: `highest_score` is the row-wise maximum of the finding columns (columns 7 to end).
- **Study-level**: The study-level MI score is the mean of `highest_score` over all subjects in the study (all arms). It is computed internally; the returned data are per-subject.
- **Output**: Long (one row per subject per finding) or wide (one row per subject, first 6 columns plus one column per MISTRESC with severity score, plus `highest_score`).

### Arguments and return value

| Argument | Description |
|----------|-------------|
| `studyid` | Study identifier. Required for SQLite; optional when `xpt_dir` is set. |
| `path_db` | Path to the SQLite database. Required for SQLite; omit when using `xpt_dir`. |
| `xpt_dir` | Path to a directory containing XPT files for one study (e.g. `mi.xpt`, `dm.xpt`). |
| `fake_study` | If TRUE, compile data for SENDsanitizer-style studies. Default FALSE. |
| `master_CompileData` | Optional precomputed compile data; if provided, `get_compile_data` is not called again. |
| `terminal_setcds_only` | Passed to `get_compile_data` when compile data is built; default TRUE. |
| `score_in_list_format` | If FALSE (default), long format: STUDYID, USUBJID, ARMCD, SETCD, SEX, endpoint, score. If TRUE, wide format: first 6 columns plus one column per finding and `highest_score`. |


## Common arguments and usage

- **Data source**: Use either (`studyid` + `path_db`) for SQLite or `xpt_dir` for a single-study directory of XPT files. Do not mix; when using `xpt_dir`, `studyid` can be omitted for the score functions.
- **Compile data**: All three functions use compile data (from `get_compile_data`) to restrict subjects (TK removal; optional terminal **`treatment_group`** SETCDs when **`terminal_setcds_only`** is TRUE) and to get ARMCD (vehicle / HD / Both or dose labels). Prefer calling `get_compile_data` once and passing the result as `master_CompileData` (as in the XPT example above). **LB** and **MI** then skip recomputation; **BW** still recomputes compile data before the ARMCD merge. For how compile data is built, see **get_compile_data and compile data** above.
- **terminal_setcds_only**: Default TRUE on compile, doses, scorers, and `get_all_score`. Controls whether recovery/interim SETCDs are excluded from the scored cohort.
- **Reference for z-scores**: BW and LB use ARMCD == "vehicle" for mean and standard deviation; scores are then computed for all subjects (all treatment arms). BW keeps a **signed** z-score; LB takes **`abs()`**. MI does not use a vehicle z-score; it uses severity and incidence rules (with vehicle incidence subtracted before the override thresholds).
- **Return format**: For all three functions, `score_in_list_format` controls whether the return is long (one row per subject per endpoint) or wide (one row per subject, endpoints as columns). The default is long. `get_all_score` returns a list with `studyid_res` plus one element per requested domain.
