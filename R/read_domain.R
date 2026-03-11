# Internal helpers for reading SEND domains from SQLite or nested XPT directories.
# read_domain_for_study is not exported; used by get_doses, get_compile_data, etc.
# get_study_ids_from_xpt is exported for use by apps.

#' @importFrom haven read_xpt
#' @importFrom fs path
NULL

#' Read a single domain for one study from SQLite or XPT (nested layout).
#'
#' @param domain Character, lowercase domain name (e.g. "dm", "bw", "lb").
#' @param studyid Character, study identifier.
#' @param path_db Character or NULL; path to SQLite database (used when xpt_dir is NULL).
#' @param xpt_dir Character or NULL; root of nested XPT layout (xpt_dir/APPID/STUDYID/*.xpt).
#' @param appid Character or NULL; required when xpt_dir is set (application ID folder name).
#' @return Data frame with domain data (uppercase column names for XPT).
#' @noRd
read_domain_for_study <- function(domain, studyid, path_db = NULL, xpt_dir = NULL, appid = NULL) {
  domain <- tolower(domain)
  studyid <- as.character(studyid)
  if (!is.null(xpt_dir)) {
    if (is.null(appid)) stop("appid is required when xpt_dir is set (nested layout: xpt_dir/APPID/STUDYID/*.xpt).")
    study_dir <- file.path(xpt_dir, appid, studyid)
    xpt_file <- fs::path(study_dir, paste0(domain, ".xpt"))
    if (!file.exists(as.character(xpt_file))) return(data.frame())
    out <- haven::read_xpt(xpt_file)
    if (nrow(out) == 0L) return(out)
    colnames(out) <- toupper(colnames(out))
    as.data.frame(out, stringsAsFactors = FALSE)
  } else {
    if (is.null(path_db)) stop("Either path_db or (xpt_dir and appid) must be provided.")
    con <- DBI::dbConnect(RSQLite::SQLite(), dbname = path_db)
    on.exit(DBI::dbDisconnect(con), add = TRUE)
    dom <- toupper(domain)
    stat <- paste0("SELECT * FROM ", dom, " WHERE STUDYID = (:x)")
    DBI::dbGetQuery(con, statement = stat, params = list(x = studyid))
  }
}

#' Get study list from nested XPT directory structure.
#'
#' Scans xpt_dir for APPID subdirectories, then each APPID for STUDYID subdirectories.
#' Returns a data frame with columns APPID and STUDYID (same shape as ID table).
#'
#' @param xpt_dir Character; root path (xpt_dir/APPID/STUDYID/*.xpt).
#' @return Data frame with columns APPID, STUDYID (one row per study).
#' @export
get_study_ids_from_xpt <- function(xpt_dir) {
  if (!dir.exists(xpt_dir)) return(data.frame(APPID = character(), STUDYID = character(), stringsAsFactors = FALSE))
  app_dirs <- list.dirs(xpt_dir, full.names = FALSE, recursive = FALSE)
  app_dirs <- app_dirs[app_dirs != ""]
  out <- data.frame(APPID = character(), STUDYID = character(), stringsAsFactors = FALSE)
  for (ad in app_dirs) {
    study_dirs <- list.dirs(file.path(xpt_dir, ad), full.names = FALSE, recursive = FALSE)
    study_dirs <- study_dirs[study_dirs != ""]
    for (sd in study_dirs) {
      out <- rbind(out, data.frame(APPID = ad, STUDYID = sd, stringsAsFactors = FALSE))
    }
  }
  out
}
