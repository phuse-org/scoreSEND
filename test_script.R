# Make sure handles interim sacrifices and recovery sacrifices properly and ensure documentation reflects this logic
# Double check BW Scoring
# add argument to calculate scores within SEX
# add argument to filter by organ system (or not)
# add argument to calculate LB as change from baseline (if baseline data is present) -- perhaps make this the default
# Update xpt_dir functionality to enable reading from multiple datasets


rm(list = ls())

setwd(dirname(this.path::this.path()))

devtools::load_all()

Domains <- c('bw', 'lb', 'mi')

study_dirs <- list.files('sample_data', full.names = T)

# study_dir <- "sample_data/35449"
for (study_dir in study_dirs[1:3]) {
  print(study_dir)
  
  Files <- list.files(study_dir)
  for (File in Files) {
    Domain <- toupper(unlist(strsplit(File, '.', fixed = T))[1])
    assign(Domain, haven::read_xpt(paste0(study_dir, '/', File)))
  }
  
  Doses <- get_doses(xpt_dir = study_dir)
  treatmentGroups <- get_treatment_group(xpt_dir = study_dir)
  print(treatmentGroups)
  
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
  
  Scores <- get_all_score(xpt_dir = study_dir, domain = Domains, score_in_list_format = F)
  scoresList <- get_all_score(xpt_dir = study_dir, domain = Domains, score_in_list_format = T)
  
  if (study_dir == study_dirs[1]) {
    Scores_all <- Scores[Domains]
    scoresList_all <- scoresList[Domains]
  }
  
  for (Domain in Domains) {
    Scores_all[[Domain]] <- rbind(Scores_all[[Domain]], Scores[[Domain]])
  }
}