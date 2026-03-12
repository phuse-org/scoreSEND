# sendSummarizer 
sendSummarizer is an R package that includes functions to calculate toxicity score
of a given repeat-dose toxicological study. Data can be read from a **SQLite database** or from **raw XPT files**. For XPT, provide the path to a directory that directly contains the domain files (e.g. `study_folder/bw.xpt`, `dm.xpt`, `lb.xpt`) for one study; all files in that directory are treated as one study.  

- paper
- [paper link](https://academic.oup.com/toxsci/article/200/2/277/7690167?login=true) 

- Poster
- [poster](https://www.lexjansen.com/css-us/2022/POS_PP23.pdf)  



# Installation

```
# Install from GitHub
install.packages("devtools")
devtools::install_github('phuse-org/send-summarizer')
```

### For development

Clone the repo, then load the package:

```
setwd('send-summarizer')
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

To list multiple study directories under a parent folder, use `get_study_ids_from_xpt(parent_dir)`; it returns a data frame with a `study_dir` column (full path to each subdirectory). You can then loop over those paths and call the scoring functions with `xpt_dir = each_study_dir`.
