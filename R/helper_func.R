#!/usr/bin/env Rscript

# This code is for creating
# -----------------------------------------------------------------------------
# Date                     Programmer
#----------   --------------------------------------------------------------
# Feb-04-2025    Md Yousuf Ali (MdYousuf.Ali@fda.hhs.gov)


## conn <- DBI::dbConnect(RSQLite::SQLite(), db_path)
## query <- 'SELECT *  FROM ID'
## all_ids <- DBI::dbGetQuery(conn = conn, query)
## all_ids <- data.table::setDT(all_ids)

#' Get study ID and title mapping for UI (DB or XPT).
#' @param conn Database connection (used when xpt_dir is NULL).
#' @param ind Selected APPID(s) or identifier(s) to filter all_ids.
#' @param all_ids Data frame with at least APPID and STUDYID (e.g. from ID table or get_study_ids_from_xpt).
#' @param xpt_dir Optional; root of nested XPT layout. When set, STITLE is read from each xpt_dir/APPID/STUDYID/ts.xpt.
#' @noRd
get_studyid_title <- function(conn, ind, all_ids, xpt_dir = NULL) {
  data.table::setDT(all_ids)
  select_studyid <- all_ids[APPID %in% ind, ]
  studyid <- unique(select_studyid[, STUDYID])
  if (length(studyid) == 0L) return(structure(character(), names = character()))

  if (!is.null(xpt_dir)) {
    stitle_list <- lapply(seq_len(nrow(select_studyid)), function(k) {
      ts_df <- read_domain_for_study("ts", select_studyid$STUDYID[k], path_db = NULL, xpt_dir = xpt_dir, appid = select_studyid$APPID[k])
      if (nrow(ts_df) == 0L || !"TSPARMCD" %in% names(ts_df)) return(data.frame(STUDYID = select_studyid$STUDYID[k], TSVAL = NA_character_, stringsAsFactors = FALSE))
      strow <- ts_df[ts_df$TSPARMCD == "STITLE", c("STUDYID", "TSVAL")]
      if (nrow(strow) == 0L) strow <- data.frame(STUDYID = select_studyid$STUDYID[k], TSVAL = NA_character_, stringsAsFactors = FALSE)
      strow
    })
    STITLE <- do.call(rbind, stitle_list)
  } else {
    STITLE <- DBI::dbGetQuery(conn = conn,
      "SELECT STUDYID, TSVAL FROM TS WHERE TSPARMCD = \"STITLE\" and STUDYID in (:x)",
      params = list(x = studyid))
  }
  dbStudys <- merge(select_studyid, STITLE, by = "STUDYID")
  dbStudys[, `:=`(nm = paste0(APPID, "-", STUDYID, ": ", TSVAL))]
  st <- dbStudys$STUDYID
  names(st) <- dbStudys$nm
  st
}
