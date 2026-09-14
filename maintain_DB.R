library(sendigR)
library(logr)
library(this.path)

setwd(dirname(this.path()))

# The database is created by the call of  initEnvironment with the parameter dbCreate = TRUE:
dbToken <- initEnvironment(dbType = 'sqlite', 
                           dbPath = 'sample_data/BioCelerate.db', 
                           dbCreate = FALSE)

# Add Study to Database
addStatus <- dbImportStudies(dbToken, 'maintenance_data/', 
                          # Print contiously the status for import each study:
                          verbose = TRUE)

# Delete Study from Database
deleteStatus <- dbDeleteStudies(dbToken, studyIdList = 'Study ID')

disconnectDB(dbToken)