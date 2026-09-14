library(sendigR)
library(logr)
library(this.path)

setwd(dirname(this.path()))

# The database is created by the call of  initEnvironment with the parameter dbCreate = TRUE:
dbToken <- initEnvironment(dbType = 'sqlite', 
                           dbPath = 'sample_data/BioCelerate.db', 
                           dbCreate = TRUE)

# The tables must be created before any study can be imported
dbCreateSchema(dbToken)

status <- dbImportStudies(dbToken, 'sample_data/', 
                          # Print contiously the status for import each study:
                          verbose = TRUE,
                          # sand save the status in a log file:
                          logFilePath = 'sample_data/')

# Create a set of indexes to increase query performance for the data extraction functions
# - they may be created before of after import of data
dbCreateteIndexes(dbToken)

disconnectDB(dbToken)