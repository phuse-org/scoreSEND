# scoreSEND

Python package implementing best practices for scoring/normalizing SEND data for ingestion by ML models.

This package was derived from sendSummarizer. scoreSEND provides functions to calculate toxicity scores for a given repeat-dose toxicological study. Data can be read from a **SQLite database** or from **raw XPT files**. For XPT, provide the path to a directory that directly contains the domain files (e.g. `study_folder/bw.xpt`, `dm.xpt`, `lb.xpt`) for one study; all files in that directory are treated as one study.

- Paper: [link](https://academic.oup.com/toxsci/article/200/2/277/7690167?login=true)
- Poster: [link](https://www.lexjansen.com/css-us/2022/POS_PP23.pdf)

## Installation

```bash
pip install scoreSEND
```

Or from source:

```bash
git clone https://github.com/phuse-org/scoreSEND.git
cd scoreSEND
pip install -e .
```

### Dependencies

- pandas, numpy, pyreadstat (for XPT read). See `pyproject.toml`.

## Examples

### Using a SQLite database

```python
import scoreSEND

path_db = "C:/directory/send.db"
studyid = "112344"

compile_df = scoreSEND.get_compile_data(studyid=studyid, path_db=path_db)
bw_score = scoreSEND.get_bw_score(studyid=studyid, path_db=path_db)
lb_score = scoreSEND.get_lb_score(studyid=studyid, path_db=path_db)
mi_score = scoreSEND.get_mi_score(studyid=studyid, path_db=path_db)
all_score = scoreSEND.get_all_score(studyid=studyid, path_db=path_db, domain=["lb", "bw", "mi"])
scoreSEND.get_doses(studyid=studyid, path_db=path_db)
scoreSEND.get_treatment_group(db_path=path_db)
```

### Using raw XPT files (flat layout)

Use a directory that directly contains the XPT domain files for one study (e.g. `bw.xpt`, `dm.xpt`, `lb.xpt` in that folder).

```python
import scoreSEND

study_dir = "C:/path/to/study_folder"

scoreSEND.get_doses(xpt_dir=study_dir)
scoreSEND.get_compile_data(xpt_dir=study_dir)
scoreSEND.get_bw_score(xpt_dir=study_dir)
scoreSEND.get_all_score(xpt_dir=study_dir, domain=["lb", "bw", "mi"])
scoreSEND.get_treatment_group(xpt_dir=study_dir)
```

To list multiple study directories under a parent folder, use `get_study_ids_from_xpt(parent_dir)`; it returns a DataFrame with a `study_dir` column. Loop over those paths and call the scoring functions with `xpt_dir=each_study_dir`.

## Scoring functions

The package provides **get_bw_score** (body weight), **get_lb_score** (laboratory / clinical chemistry), and **get_mi_score** (microscopic findings). All three use the same data-source options (SQLite or XPT directory), can accept precomputed compile data via `master_CompileData`, and control return shape with `score_in_list_format` (long vs wide).

### get_compile_data and compile data

**get_compile_data** builds the subject-level table ("compile data") that the scoring functions use: which subjects to score and which arm (ARMCD) each subject belongs to.

- **Returns**: DataFrame with STUDYID, USUBJID, Species, SEX, ARMCD, SETCD. Recovery and (when applicable) TK animals are excluded. All treatment arms are included (vehicle, HD, intermediate). Pass this as `master_CompileData` to score functions to avoid recomputing.

**fake_study = True**: DM and TS only; "Control" normalized to "vehicle"; all arms kept. **fake_study = False**: Full path with DS, TX, PP, pooldef; recovery and TK removed; dose ranking assigns ARMCD (vehicle / HD / Intermediate / Both).

### get_bw_score

Body weight z-score: initial and final weight per subject; z-score using vehicle mean/SD; scores for all subjects. Returns long (STUDYID, USUBJID, endpoint, score, SEX) or wide when `score_in_list_format=True`.

### get_lb_score

Liver lab z-scores (ALT, AST, ALP, GGT, BILI, ALB); vehicle mean/SD; all subjects. Returns long (per subject per test) or wide (one row per subject, columns alt_zscore, ast_zscore, etc.) when `score_in_list_format=True`.

### get_mi_score

Liver microscopic findings: severity normalized 0–5; per-subject highest_score; study-level mean over all subjects. Returns long (per subject per finding) or wide when `score_in_list_format=True`.

### Common arguments

- **Data source**: Use either `studyid` + `path_db` (SQLite) or `xpt_dir` (single-study XPT directory).
- **master_CompileData**: Optional DataFrame from `get_compile_data`; if provided, compile data is not recomputed.
- **score_in_list_format**: If False (default), return long format; if True, return wide format.
