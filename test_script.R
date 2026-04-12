rm(list = ls())

setwd(dirname(this.path::this.path()))

devtools::load_all()

study_dir <- "sample_data/35449"

get_doses(xpt_dir = study_dir)
get_compile_data(xpt_dir = study_dir)
get_bw_score(xpt_dir = study_dir)
get_all_score(xpt_dir = study_dir, domain = c('lb', 'bw', 'mi'))
get_treatment_group(xpt_dir = study_dir)
