# Internal helpers for reading SEND domains from SQLite or flat XPT directories.
# read_domain_for_study is not exported; used by get_doses, get_compile_data, etc.
# get_study_ids_from_xpt is exported to list study directories under a parent.

#' @importFrom haven read_xpt
#' @importFrom fs path
NULL

#' Read a single domain from SQLite or from a directory of XPT files (flat layout).
#'
#' When xpt_dir is set, it is the path to a directory that directly contains
#' domain files (e.g. bw.xpt, dm.xpt). studyid and appid are not used for path construction.
#' When path_db is set, studyid is required for the SQLite query.
#'
#' @param domain Character, lowercase domain name (e.g. "dm", "bw", "lb").
#' @param studyid Character or NULL; required for SQLite (WHERE STUDYID = ?); ignored when xpt_dir is set.
#' @param path_db Character or NULL; path to SQLite database (used when xpt_dir is NULL).
#' @param xpt_dir Character or NULL; path to a directory containing XPT files for one study (flat: xpt_dir/domain.xpt).
#' @return Data frame with domain data (uppercase column names for XPT).
#' @noRd
read_domain_for_study <- function(domain, studyid = NULL, path_db = NULL, xpt_dir = NULL) {
  domain <- tolower(domain)
  if (!is.null(xpt_dir)) {
    xpt_file <- fs::path(xpt_dir, paste0(domain, ".xpt"))
    if (!file.exists(as.character(xpt_file))) return(data.frame())
    out <- haven::read_xpt(xpt_file)
    if (nrow(out) == 0L) return(out)
    colnames(out) <- toupper(colnames(out))
    as.data.frame(out, stringsAsFactors = FALSE)
  } else {
    if (is.null(path_db)) stop("Either path_db or xpt_dir must be provided.")
    if (is.null(studyid)) stop("studyid is required when using path_db (SQLite).")
    studyid <- as.character(studyid)
    con <- DBI::dbConnect(RSQLite::SQLite(), dbname = path_db)
    on.exit(DBI::dbDisconnect(con), add = TRUE)
    dom <- toupper(domain)
    stat <- paste0("SELECT * FROM ", dom, " WHERE STUDYID = (:x)")
    DBI::dbGetQuery(con, statement = stat, params = list(x = studyid))
  }
}

#' List study directories under a parent path (flat XPT layout).
#'
#' Returns immediate subdirectories of parent_dir; each subdir is assumed to be
#' a study folder containing XPT files (e.g. bw.xpt, dm.xpt). Use to iterate over
#' multiple studies when parent_dir contains one subdir per study.
#'
#' @param parent_dir Character; path to a parent directory whose subdirs are study folders.
#' @return Data frame with column study_dir (full path to each study directory).
#' @export
get_study_ids_from_xpt <- function(parent_dir) {
  if (!dir.exists(parent_dir)) return(data.frame(study_dir = character(), stringsAsFactors = FALSE))
  subdirs <- list.dirs(parent_dir, full.names = TRUE, recursive = FALSE)
  subdirs <- subdirs[subdirs != ""]
  data.frame(study_dir = subdirs, stringsAsFactors = FALSE)
}
