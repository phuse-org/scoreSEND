rm(list = ls())

setwd(dirname(this.path::this.path()))

devtools::load_all()

study_dir <- "sample_data/35449"

# Doses <- get_doses(xpt_dir = study_dir)
# treatmentGroups <- get_treatment_group(xpt_dir = study_dir)

Compiled_Data <- get_compile_data(xpt_dir = study_dir)

BWscores <- get_bw_score(xpt_dir = study_dir, 
                         master_CompileData = Compiled_Data,
                         score_in_list_format = F)
BWscoresList <- get_bw_score(xpt_dir = study_dir, 
                         master_CompileData = Compiled_Data,
                         score_in_list_format = T)

LBscores <- get_lb_score(xpt_dir = study_dir, 
                         master_CompileData = Compiled_Data,
                         score_in_list_format = F)
LBscoresList <- get_lb_score(xpt_dir = study_dir, 
                         master_CompileData = Compiled_Data,
                         score_in_list_format = T)

MIscores <- get_mi_score(xpt_dir = study_dir, 
                         master_CompileData = Compiled_Data,
                         score_in_list_format = F)
MIscoresList <- get_mi_score(xpt_dir = study_dir, 
                         master_CompileData = Compiled_Data,
                         score_in_list_format = T)

Scores <- get_all_score(xpt_dir = study_dir, domain = c('lb', 'bw', 'mi'))


