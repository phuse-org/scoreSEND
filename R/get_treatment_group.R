## This code is for getting treatment group, recovery group and TK group

## -----------------------------------------------------------------------------
##   Date                     Programmer
## ----------   --------------------------------------------------------------
##   Feb-15-2024    Md Yousuf Ali (md.ali@fda.hhs.gov)


#' @title get treatment group
#' @param studies Optional; character or vector of study IDs. When \code{db_path} is used and NULL, taken from ID table. When \code{xpt_dir} is used and NULL, taken from \code{get_study_ids_from_xpt(xpt_dir)}.
#' @param db_path Optional when \code{xpt_dir} is set; path to SQLite database
#' @param xpt_dir Optional; root of nested XPT layout (\code{xpt_dir/APPID/STUDYID/*.xpt}). When set, \code{appid} per study is required (from \code{get_study_ids_from_xpt}).
#' @return list
#'
#' @examples
#' \dontrun{
#' get_treatment_group(studies = '12345678', db_path = 'path/to/sqllite/database.db')
#' get_treatment_group(studies = NULL, xpt_dir = '/path/to/xpt_root')
#' }
#' @export

get_treatment_group <- function(studies = NULL, db_path = NULL, xpt_dir = NULL) {
  list_return <- list()
  four <- c()
  use_xpt <- !is.null(xpt_dir)
  if (use_xpt) {
    if (is.null(studies)) {
      id_df <- get_study_ids_from_xpt(xpt_dir)
      if (nrow(id_df) == 0L) return(list_return)
      study_list <- id_df
    } else if (is.data.frame(studies) && all(c("APPID", "STUDYID") %in% names(studies))) {
      study_list <- studies
    } else {
      stop("When xpt_dir is set, pass studies = NULL (use all) or a data frame with APPID and STUDYID columns (e.g. from get_study_ids_from_xpt).")
    }
  } else {
    if (is.null(db_path)) stop("db_path is required when xpt_dir is not set.")
    con <- DBI::dbConnect(RSQLite::SQLite(), dbname = db_path)
    if (is.null(studies)) {
      id_df <- DBI::dbGetQuery(conn = con, statement = "SELECT * FROM ID")
      studies <- id_df[["STUDYID"]]
      study_list <- data.frame(APPID = id_df[["APPID"]], STUDYID = studies, stringsAsFactors = FALSE)
    } else {
      study_list <- data.frame(APPID = NA_character_, STUDYID = studies, stringsAsFactors = FALSE)
    }
  }

  for (i in seq_len(nrow(study_list))) {
    study <- study_list$STUDYID[i]
    appid_val <- study_list$APPID[i]
    print(study)
    if (use_xpt) {
      tx <- read_domain_for_study("tx", study, path_db = NULL, xpt_dir = xpt_dir, appid = appid_val)
      ts <- read_domain_for_study("ts", study, path_db = NULL, xpt_dir = xpt_dir, appid = appid_val)
      ds <- read_domain_for_study("ds", study, path_db = NULL, xpt_dir = xpt_dir, appid = appid_val)
      dm <- read_domain_for_study("dm", study, path_db = NULL, xpt_dir = xpt_dir, appid = appid_val)
      pc <- read_domain_for_study("pc", study, path_db = NULL, xpt_dir = xpt_dir, appid = appid_val)
      pooldef <- read_domain_for_study("pooldef", study, path_db = NULL, xpt_dir = xpt_dir, appid = appid_val)
      tx <- data.table::as.data.table(tx)
      ts <- data.table::as.data.table(ts)
      ds <- data.table::as.data.table(ds)
      dm <- data.table::as.data.table(dm)
      pc <- data.table::as.data.table(pc)
      pooldef <- data.table::as.data.table(pooldef)
    } else {
      tx <- DBI::dbGetQuery(conn = con, statement = "SELECT STUDYID,SETCD,TXPARMCD,TXVAL FROM TX WHERE STUDYID IN (:x)", params = list(x = study))
      tx <- data.table::as.data.table(tx)
      ts <- DBI::dbGetQuery(conn = con, statement = "SELECT STUDYID,TSPARMCD,TSVAL FROM TS WHERE STUDYID = (:x)", params = list(x = study))
      ts <- data.table::as.data.table(ts)
      ds <- DBI::dbGetQuery(conn = con, statement = "SELECT STUDYID, USUBJID, DSDECOD FROM DS WHERE STUDYID = (:x)", params = list(x = study))
      ds <- data.table::as.data.table(ds)
      dm <- DBI::dbGetQuery(conn = con, statement = "SELECT STUDYID, USUBJID, SETCD FROM DM WHERE STUDYID = (:x)", params = list(x = study))
      dm <- data.table::as.data.table(dm)
      pc <- DBI::dbGetQuery(conn = con, statement = "SELECT STUDYID, USUBJID, POOLID FROM PC WHERE STUDYID = (:x)", params = list(x = study))
      pc <- data.table::as.data.table(pc)
      pooldef <- DBI::dbGetQuery(conn = con, statement = "SELECT STUDYID, USUBJID, POOLID FROM POOLDEF WHERE STUDYID = (:x)", params = list(x = study))
      pooldef <- data.table::as.data.table(pooldef)
    }

    ## tabl <- c('tx','ts','ds','dm','pc','pooldef')

    number_of_setcd <- unique(dm[['SETCD']])
    print(number_of_setcd)
    st_species <- ts[TSPARMCD=='SPECIES'][, TSVAL]

    list_return[[study]][['species']] <- st_species

    list_return[[study]][['setcd']] <- number_of_setcd
    recv_group <- c()
    trtm_group <- c()
if(length(st_species)!= 0) {
    if(st_species =="RAT") {
      # see if tkdesc in txparmcd
      parmcd <- unique(tx[['TXPARMCD']])
      if('TKDESC' %in% parmcd){
        tkdesc_in_parmcd <- TRUE
      } else {

        tkdesc_in_parmcd <- FALSE
      }
      ## tkdesc_in_parmcd
      if(tkdesc_in_parmcd) {

        unq_tkdesc <- unique(tx[TXPARMCD=='TKDESC',TXVAL])
        if (length(unq_tkdesc) > 0) {
          if('TK' %in% unq_tkdesc) {
            tk_group <- unique(tx[TXPARMCD=='TKDESC' & TXVAL=='TK',  SETCD])
            ## print('tkin parmcd')
            ## print(tk)
          }
          not_tk <- number_of_setcd[which(!number_of_setcd %in% tk_group)]
        } else {
          not_tk <- number_of_setcd
        }
      } else {
        tk_group <- c()
        for(i in 1:length(number_of_setcd)){
          set_cd  <- number_of_setcd[i]
          subjid <- unique(dm[SETCD==set_cd, USUBJID])

          if(pc$USUBJID[1]!='') {
            uniq_pc_subj <- unique(pc$USUBJID)
            pc_sub <- 'not_empty'
          } else {
            uniq_pool <- unique(pc$POOLID)
            ## pooldef <- df_domain$pooldef
            pool_sub <- pooldef[POOLID %in% uniq_pool, USUBJID]
            pc_sub <- 'empty'
          }

          if(pc_sub=='not_empty'){
            if(any(subjid %in% uniq_pc_subj)){
              ## print(paste0(set_cd, ' : in TK'))
              tk_group <- c(tk_group, set_cd)
            }
          } else if (pc_sub=='empty'){
            if(any(subjid %in% pool_sub)){
              ## print(paste0(set_cd, ' : in TK and pool'))
              tk_group <- c(tk_group, set_cd)
            }
          }

        }
        not_tk <- number_of_setcd[which(!number_of_setcd %in% tk_group)]
      }
      ## number_of_setcd

      if(length(not_tk) > 0) {
        for (i in 1:length(not_tk)){
          set_cd <- not_tk[i]
          subjid <- unique(dm[SETCD==set_cd, USUBJID])
          dsdecod <- tolower(unique(ds[USUBJID %in% subjid, DSDECOD]))
          if(tolower("RECOVERY SACRIFICE") %in% dsdecod) {
            recv_group <- c(recv_group, set_cd)
          } else if (tolower("TERMINAL SACRIFICE") %in% dsdecod){
            trtm_group <- c(trtm_group, set_cd)
          }
        }
      }

      list_return[[study]][['TK_group']] <- tk_group
    } else {
      not_tk <- number_of_setcd
      for (i in 1:length(not_tk)){
        set_cd <- not_tk[i]
        subjid <- unique(dm[SETCD==set_cd, USUBJID])
        dsdecod <- tolower(unique(ds[USUBJID %in% subjid, DSDECOD]))
        if(tolower("RECOVERY SACRIFICE") %in% dsdecod) {
          ## print(paste0(set_cd, ' : in recovery'))
          recv_group <- c(recv_group, set_cd)
        } else if (tolower("TERMINAL SACRIFICE") %in% dsdecod){
          trtm_group <- c(trtm_group, set_cd)
        }
      }
    }
    }

    if( length(trtm_group) == 4) {

      four <- c(four,study)
      ## print(four)
    }

    print(trtm_group)
    list_return[[study]][['treatment_group']] <- trtm_group
    list_return[[study]][['recovery_group']] <- recv_group
  }

list_return[['four_trtm_group']] <- four
  list_return
}

