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

## Using a SQLite database

```
path_db <- "C:/directory/send.db"
studyid <- '112344'

mi_score <- get_mi_score(studyid, path_db)
lb_score <- get_lb_score(studyid, path_db)
bw_score <- get_bw_score(studyid, path_db)
all_score <- get_all_score(studyid, path_db, domain = c('lb', 'bw', 'mi'))
compile <- get_compile_data(studyid, path_db)
get_treatment_group(db_path = path_db)
```

## Using raw XPT files (flat layout)

Use a directory that directly contains the XPT domain files for one study (e.g. `bw.xpt`, `dm.xpt`, `lb.xpt` in that folder).

```
study_dir <- "C:/path/to/study_folder"

get_doses(xpt_dir = study_dir)
get_compile_data(xpt_dir = study_dir)
get_bw_score(xpt_dir = study_dir)
get_all_score(xpt_dir = study_dir, domain = c('lb', 'bw', 'mi'))
get_treatment_group(xpt_dir = study_dir)
```

To list multiple study directories under a parent folder, use `get_study_ids_from_xpt(parent_dir)`; it returns a data frame with a `study_dir` column (full path to each subdirectory). You can then loop over those paths and call the scoring functions with `xpt_dir = each_study_dir`. For details on how each score is calculated and how to use their arguments, see **Scoring functions** below.


## get_treatment_group

**get_treatment_group** classifies **SETCD** cohorts (non-TK sets) using **DS** disposition (**DSDECOD**). By default, **get_compile_data** keeps only subjects in **`treatment_group`** (terminal-sacrifice sets); set **`terminal_setcds_only = FALSE`** to include all **non-TK** DM subjects with no terminal **SETCD** restriction (wider cohort). You can still call **get_treatment_group** directly for labels (`recovery_group`, **`interim_group`**, etc.).

For each study, the returned list includes:

| Element | Meaning |
|---------|---------|
| `species` | Species from TS |
| `setcd` | All SETCD values in DM |
| `treatment_group` | SETCDs where any subject has **TERMINAL SACRIFICE** (non-TK sets only) |
| `recovery_group` | SETCDs where any subject has **RECOVERY SACRIFICE** |
| `interim_group` | SETCDs where any subject has **INTERIM SACRIFICE** |
| `TK_group` | (Rats only, when TK can be inferred) SETCDs classified as toxicokinetic |
| `four_trtm_group` | (Top-level list entry) Study IDs with exactly four terminal treatment groups |

If a set has more than one disposition type across animals, classification follows a single branch: **recovery** first, then **interim**, then **terminal**.


# Scoring functions

The package provides three main scoring functions: **get_bw_score** (body weight), **get_lb_score** (laboratory / clinical chemistry), and **get_mi_score** (microscopic findings). All three use the same data-source options (SQLite or XPT directory), can accept precomputed compile data via `master_CompileData`, and control return shape with `score_in_list_format` (long vs wide).


## get_compile_data and compile data

**get_compile_data** builds the subject-level table ("compile data") that the scoring functions use to decide which subjects to score and which arm (ARMCD) each subject belongs to.

### What get_compile_data returns

A data frame with one row per subject and columns **STUDYID**, **USUBJID**, **Species**, **SEX**, **ARMCD**, **SETCD**. **TK** animals are excluded on rat studies when inferred from PP/pooldef. With the default **`terminal_setcds_only = TRUE`**, only **SETCD** values in **`treatment_group`** from **get_treatment_group** are kept (terminal-sacrifice cohorts). **ARMCD** is derived from ordered TRTDOS dose (vehicle, LD, MD or MD1/MD2/…, HD, or Both). Each subject has a single ARMCD label used by the score functions.

### How get_compile_data works

**fake_study = TRUE (SENDsanitizer-style studies)**

- **Data**: DM and TS only (from SQLite or XPT).
- **Processing**: Normalize "Control" to "vehicle"; keep all treatment arms in DM (no filter to vehicle/HD). Add Species from TS.
- **Output**: One row per subject; ARMCD comes from the DM ARM column (all arms present).

**fake_study = FALSE (main path)**

- **Data**: DM, TS, TX, BW, pooldef, PP (from SQLite or XPT). The **DS** domain is not read here; cohort phase is applied via **`get_treatment_group`** when **`terminal_setcds_only`** is TRUE.
- **Steps** (in order):
  1. **Build CompileData** from DM (STUDYID, Species, USUBJID, SEX, ARMCD, SETCD).
  2. **Remove TK animals** (rat studies only): Exclude USUBJIDs that appear in pooldef for pools listed in PP (TK pools).
  3. **Terminal SETCD filter** (default **`terminal_setcds_only = TRUE`**): Keep only subjects whose **SETCD** is in **`treatment_group`** from **get_treatment_group** (same rules as disposition classification there: recovery / interim / terminal precedence among non-TK sets). Use **`terminal_setcds_only = FALSE`** to skip this step (all non-TK DM subjects; no terminal **SETCD** restriction).
  4. **Dose ranking**: Use TX (TXPARMCD == "TRTDOS") to get one dose value per (STUDYID, SETCD). Per study, sort distinct dose values and assign **ARMCD** = "vehicle" (lowest), "HD" (highest), "Both" (single distinct level), "LD" / "MD" / "MD1" / "MD2" / … for intermediate levels (see package implementation). Inner-join this to the cleaned subject list so every remaining subject gets exactly one ARMCD.
- **Output**: One row per subject; columns STUDYID, USUBJID, Species, SEX, ARMCD, SETCD.

**Arguments**: `studyid` and `path_db` are required when using SQLite; omit them when using `xpt_dir`. `xpt_dir` is the path to a directory containing XPT files for one study (e.g. dm.xpt, ts.xpt, tx.xpt). `fake_study`: if TRUE, use the simplified DM+TS path and keep all arms; if FALSE, use the full path with TX/PP/pooldef and dose ranking. **`terminal_setcds_only`**: if TRUE (default), apply the terminal **`treatment_group`** SETCD filter after TK removal; if FALSE, omit it. **`get_doses`** accepts the same parameter and stays aligned with compile data.

### How the scoring functions use compile data

- **Who gets scored**: Each scoring function restricts to subjects whose USUBJID is in the compile data. With default compile settings, that means non-TK subjects whose SETCD is in **`treatment_group`** (when **`terminal_setcds_only`** is TRUE), each with an ARMCD.
- **ARMCD usage**: **get_bw_score** and **get_lb_score** use ARMCD == "vehicle" to compute mean and SD for z-scores; scores are then computed for all subjects (all arms) in the compile data. **get_mi_score** uses ARMCD (and STUDYID, USUBJID, SETCD, etc.) for merging and for incidence-by-arm logic; scores are produced for all subjects in the compile data.
- **master_CompileData**: If you call **get_compile_data** once and pass the result as **master_CompileData** into **get_bw_score**, **get_lb_score**, or **get_mi_score**, each score function skips calling get_compile_data again. This avoids recomputing compile data when running multiple score functions for the same study.


## get_bw_score

### How the BW score is calculated

- **Data**: BW domain is read; the day column is unified as VISITDY, else BWNOMDY, else BWDY. Only subjects present in compile data (per TK removal and optional terminal **SETCD** filter) are scored.
- **Initial weight** (per subject): The first record with VISITDY == 1; if none, the record with VISITDY &lt; 0 closest to zero; if none, the single record in 1 &lt; VISITDY ≤ 5 with minimum VISITDY; if the only records are VISITDY &gt; 5, initial weight is set to 0.
- **Final weight** (per subject): The record with BWTESTCD == "TERMBW" if present; otherwise, among records with VISITDY &gt; 5, the row with maximum VISITDY.
- **Metric**: `finalbodyweight = |BWSTRESN - BWSTRESN_Init|`.
- **Z-score**: Within each STUDYID, mean and standard deviation are computed from subjects with ARMCD == "vehicle". For all subjects (all treatment arms), `BWZSCORE = (finalbodyweight - mean_vehicle) / sd_vehicle`. Vehicle is used only as the reference; scores are produced for every subject.
- **Output**: One score per subject (endpoint is "BW"). No study-level summary table is returned.

### Arguments and return value

| Argument | Description |
|----------|-------------|
| `studyid` | Study identifier. Required when using SQLite; optional when `xpt_dir` is set. |
| `path_db` | Path to the SQLite database. Required for SQLite; omit when using `xpt_dir`. |
| `xpt_dir` | Path to a directory containing XPT files for one study (e.g. `bw.xpt`, `dm.xpt`). When set, `studyid` and `path_db` are not needed for reading data. |
| `fake_study` | If TRUE, compile data is built for SENDsanitizer-style studies (all arms kept). Default FALSE. |
| `master_CompileData` | Optional precomputed compile data frame. If provided, compile data is not recomputed (saves time when calling multiple score functions). |
| `score_in_list_format` | If FALSE (default), returns a long-format data frame with columns STUDYID, USUBJID, endpoint, score, SEX. If TRUE, returns the full wide table (e.g. BWZSCORE, finalbodyweight, etc.). |


## get_lb_score

### How the LB score is calculated

- **Data**: LB domain; day column is unified as VISITDY, else LBNOMDY, else LBDY. Only records with VISITDY ≥ 1 are used. LBSPEC and LBTESTCD are combined (e.g. "SERUM | ALT"). Only liver-related tests are kept: SERUM, PLASMA, or WHOLE BLOOD for ALT, AST, ALP, GGT, BILI, and ALB. Subjects are restricted to compile data (same TK and terminal **SETCD** rules as **get_compile_data**).
- **Per-subject, per-test**: For each of the six tests, one value per subject is taken: the record with maximum VISITDY per (USUBJID, LBTESTCD).
- **Z-score**: Within each STUDYID, for each test, mean and standard deviation are computed from subjects with ARMCD == "vehicle". For all subjects, `*_zscore = (LBSTRESN - mean_vehicle_*) / sd_vehicle_*`, then the absolute value is taken.
- **Study-level**: For each test, the average of that test's z-scores over all subjects in the study is computed; then the average is capped to 0–3: if avg ≥ 3 then 3, else if ≥ 2 then 2, else if ≥ 1 then 1, else 0. Study-level averages use all subjects (all arms), not only high dose.
- **Output**: The function returns per-subject data: either long (one row per subject per test) or wide (one row per subject with columns alt_zscore, ast_zscore, alp_zscore, ggt_zscore, bili_zscore, alb_zscore). Study-level scores are used internally but the primary return is per-subject.

### Arguments and return value

| Argument | Description |
|----------|-------------|
| `studyid` | Study identifier. Required for SQLite; optional when `xpt_dir` is set. |
| `path_db` | Path to the SQLite database. Required for SQLite; omit when using `xpt_dir`. |
| `xpt_dir` | Path to a directory containing XPT files for one study (e.g. `lb.xpt`, `dm.xpt`). |
| `fake_study` | If TRUE, compile data for SENDsanitizer-style studies. Default FALSE. |
| `master_CompileData` | Optional precomputed compile data; avoids recomputing when calling multiple score functions. |
| `score_in_list_format` | If FALSE (default), returns long format (STUDYID, USUBJID, endpoint, score). If TRUE, returns wide format (STUDYID, USUBJID, ARMCD, alt_zscore, ast_zscore, alp_zscore, ggt_zscore, bili_zscore, alb_zscore). |


## get_mi_score

### How the MI score is calculated

- **Data**: MI domain; only records with MISPEC containing "LIVER" (case-insensitive) are used. MISEV is normalized to a 0–5 numeric scale (e.g. MINIMAL→1, MILD→2, MODERATE→3, MARKED→4, SEVERE→5; "n OF 4" and "n OF 5" mapped accordingly). Some MISTRESC values are merged (e.g. "CELL DEBRIS" → "CELLULAR DEBRIS", infiltration variants → "Infiltrate"). Subjects are restricted to compile data (same TK and terminal **SETCD** rules as **get_compile_data**).
- **Per-subject, per-finding**: A wide table is built: first six columns are STUDYID, USUBJID, ARMCD, etc.; columns 7 onward are one per finding. Raw severity is transformed: 5→5, &gt;3→3, 3→2, &gt;0→1, else 0. Then an **incidence override** is applied: by study, sex, and arm, incidence (proportion of subjects with that finding) is computed; if incidence ≥ 75% the score is set to 5, ≥ 50% to 3, ≥ 25% to 2, ≥ 10% to 1. If a subject's severity for that finding is less than this incidence-derived value, it is raised to that value.
- **Per-subject summary**: `highest_score` is the row-wise maximum of the finding columns (columns 7 to end).
- **Study-level**: The study-level MI score is the mean of `highest_score` over all subjects in the study (all arms).
- **Output**: Long (one row per subject per finding: STUDYID, USUBJID, endpoint, score) or wide (one row per subject, first 6 columns plus one column per MISTRESC with severity score). The study-level value is used internally; the returned data are per-subject.

### Arguments and return value

| Argument | Description |
|----------|-------------|
| `studyid` | Study identifier. Required for SQLite; optional when `xpt_dir` is set. |
| `path_db` | Path to the SQLite database. Required for SQLite; omit when using `xpt_dir`. |
| `xpt_dir` | Path to a directory containing XPT files for one study (e.g. `mi.xpt`, `dm.xpt`). |
| `fake_study` | If TRUE, compile data for SENDsanitizer-style studies. Default FALSE. |
| `master_CompileData` | Optional precomputed compile data; avoids recomputing when calling multiple score functions. |
| `score_in_list_format` | If FALSE (default), returns long format (STUDYID, USUBJID, endpoint, score). If TRUE, returns wide format (first 6 columns plus one column per finding). |


## Common arguments and usage

- **Data source**: Use either (`studyid` + `path_db`) for SQLite or `xpt_dir` for a single-study directory of XPT files. Do not mix; when using `xpt_dir`, `studyid` can be omitted for the score functions.
- **Compile data**: All three functions use compile data (from `get_compile_data`) to restrict subjects (TK removal; optional terminal **`treatment_group`** SETCDs when **`terminal_setcds_only`** is TRUE) and to get ARMCD (vehicle / HD / Both or dose labels). If you call `get_compile_data` once and pass the result as `master_CompileData` into each score function, compile data is not recomputed. For how compile data is built and how it is used by the score functions, see **get_compile_data and compile data** above.
- **Reference for z-scores**: BW and LB use ARMCD == "vehicle" for mean and standard deviation; scores are then computed for all subjects (all treatment arms). MI does not use a vehicle z-score; it uses severity and incidence rules.
- **Return format**: For all three functions, `score_in_list_format` controls whether the return is long (one row per subject per endpoint) or wide (one row per subject, endpoints as columns). The default is long.
