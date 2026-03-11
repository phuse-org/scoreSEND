# sendSummarizer 
sendSummarizer is an R package that includes functions to calculate toxicity score
of a given repeat-dose toxicological study. Data can be read from a **SQLite database** or from **raw XPT files** in a nested directory layout: `xpt_dir/APPID/STUDYID/*.xpt` (one folder per application, one folder per study under each, with domain files such as `bw.xpt`, `dm.xpt`, etc. in each study folder).  

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

### for development
clone the repo and follow the instructions.  

```
setwd('send-summarizer')
devtools::load_all(".")
sendSummarizer::send_cross_study_app('path_database.db')

```


# More examples

## Using a SQLite database

```
path_db <- "C:/directory/send.db"
studyid <- '112344'

# app
send_cross_study_app(path_db)

# score
mi_score <- get_mi_score(studyid, path_db)
lb_score <- get_lb_score(studyid, path_db)
bw_score <- get_bw_score(studyid, path_db)
all_score <- get_all_score(studyid, path_db, domain = c('lb', 'bw', 'mi'))
compile <- get_compile_data(studyid, path_db)
```

## Using raw XPT files (nested layout)

Use a root directory with structure `xpt_dir/APPID/STUDYID/*.xpt` (e.g. `xpt_root/APP1/STUDY1/bw.xpt`, `dm.xpt`, ...).

```
xpt_root <- "C:/path/to/xpt_root"
appid <- "APP1"
studyid <- "STUDY1"

# list studies
get_study_ids_from_xpt(xpt_root)

# app (XPT mode)
sendSummarizer_app(xpt_dir = xpt_root)

# score from XPT
get_doses(studyid, xpt_dir = xpt_root, appid = appid)
get_compile_data(studyid, xpt_dir = xpt_root, appid = appid)
get_bw_score(studyid, xpt_dir = xpt_root, appid = appid)
get_all_score(studyid, xpt_dir = xpt_root, appid = appid, domain = c('lb', 'bw', 'mi'))
```
