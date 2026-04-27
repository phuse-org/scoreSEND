#' @title Subject-level dose tiers after TK and optional terminal SETCD filtering
#' @description Returns one row per subject after TK cleaning (and optional terminal \code{SETCD} filter). The \code{ARMCD}
#'   column encodes dose tier from TRTDOS: \code{vehicle} (lowest), \code{HD}
#'   (highest), \code{LD}, plain \code{MD} when there are four distinct dose levels,
#'   \code{MD1}, \code{MD2}, \ldots{} when there are five or more, and \code{Both}
#'   when there is a single distinct dose level.
#' @param studyid Optional when \code{xpt_dir} is set; required for SQLite. Study identifier.
#' @param path_db Optional when \code{xpt_dir} is set; path of SQLite database.
#' @param xpt_dir Optional; path to a directory containing XPT files for one study (flat: xpt_dir/bw.xpt, dm.xpt, etc.).
#' @param terminal_setcds_only If \code{TRUE} (default), after TK cleaning, keep only subjects whose \code{SETCD} is in \code{treatment_group} from \code{\link{get_treatment_group}}. If \code{FALSE}, all non-TK DM subjects (no SETCD filter). Same as \code{\link{get_compile_data}}.
#' @return Data frame with columns including \code{STUDYID}, \code{USUBJID}, \code{Species},
#'   \code{SEX}, \code{ARMCD} (dose tier), and \code{SETCD}.
#'
#' @examples
#' \dontrun{
#' get_doses(studyid='1234123', path_db='path/to/database.db')
#' get_doses(xpt_dir='/path/to/study_folder')
#' }
#' @export

get_doses <- function(studyid = NULL, path_db = NULL, xpt_dir = NULL,
                        terminal_setcds_only = TRUE) {
  use_xpt <- !is.null(xpt_dir)
  if (use_xpt) {
    bw <- read_domain_for_study("bw", studyid = NULL, path_db = path_db, xpt_dir = xpt_dir)
    dm <- read_domain_for_study("dm", studyid = NULL, path_db = path_db, xpt_dir = xpt_dir)
    ts <- read_domain_for_study("ts", studyid = NULL, path_db = path_db, xpt_dir = xpt_dir)
    tx <- read_domain_for_study("tx", studyid = NULL, path_db = path_db, xpt_dir = xpt_dir)
    pooldef <- read_domain_for_study("pooldef", studyid = NULL, path_db = path_db, xpt_dir = xpt_dir)
    pp <- read_domain_for_study("pp", studyid = NULL, path_db = path_db, xpt_dir = xpt_dir)
  } else {
    if (is.null(studyid)) stop("studyid is required when xpt_dir is not set (SQLite).")
    studyid <- as.character(studyid)
    if (is.null(path_db)) stop("path_db is required when xpt_dir is not set.")
    path <- path_db
    con <- DBI::dbConnect(RSQLite::SQLite(), dbname = path)
    con_db <- function(domain) {
      dom <- toupper(domain)
      stat <- paste0("SELECT * FROM ", dom, " WHERE STUDYID = (:x)")
      DBI::dbGetQuery(con, statement = stat, params = list(x = studyid))
    }
    bw <- con_db("bw")
    dm <- con_db("dm")
    ts <- con_db("ts")
    tx <- con_db("tx")
    pooldef <- con_db("pooldef")
    pp <- con_db("pp")
  }


    #..Creation of compilation data...(Compilation of DM Data).........
    # Step-1 :: # CompileData is basically the compilation of DM data
    CompileData <- data.frame(STUDYID = NA, Species = NA,
                              USUBJID = NA, SEX = NA, ARMCD = NA, SETCD = NA)

    #Pull all of the relevant DM Data
    Species <- ts$TSVAL[which(ts$TSPARMCD == "SPECIES")]
    TRTName <- ts$TSVAL[which(ts$TSPARMCD == "TRT")]
    Duration <-ts$TSVAL[which(ts$TSPARMCD == "DOSDUR")]

    # Convert duration to days
    if (any(grepl("W",Duration)) ==TRUE){
      days <- as.numeric(gsub("\\D","",Duration))*7
    } else if (any(grepl("M",Duration)) == TRUE){
      days <- as.numeric(gsub("\\D","",Duration))*7*30
    } else {
      days <- as.numeric(gsub("\\D","",Duration))
    }
    Duration <- paste0(days,"D")

    # Make StudyID
    STUDYID <- unique(ts$STUDYID)

    # CREATE DM DATA
    DMData <- data.frame(STUDYID = rep(STUDYID, length(dm$USUBJID)),
                         Species = rep(Species, length(dm$USUBJID)),
                         USUBJID = dm$USUBJID,
                         SEX = dm$SEX,
                         ARMCD = dm$ARMCD,
                         SETCD = dm$SETCD)

    #Add to CompileData
    CompileData <- rbind(CompileData, DMData)

    # Remove NAs from the first line
    CompileData <- stats::na.omit(CompileData)

    # Create a copy of CompileData which will not
  # changes with changing the CompileData
    CompileData_copy <- data.frame(CompileData)


    # Step-2 :: # REMOVE THE TK ANIMALS IF SPECIES IS RAT from "CompileData"
    # Initialize an empty data frame to store the results
    tK_animals_df <- data.frame(PP_PoolID = character(), STUDYID = character(),
                                USUBJID = character(), POOLID = character(),
                                stringsAsFactors = FALSE)

    # Initialize a data frame to keep track of studies with no POOLID
    no_poolid_studies <- data.frame(STUDYID = character(),
                                    stringsAsFactors = FALSE)

    # check for the species [# Check if the current study is a rat]
  # [{# Convert Species to lowercase for case-insensitive comparison}]

    Species_lower <- tolower(Species)

    if ("rat" %in% Species_lower) {
      # Create TK individuals for "Rat" studies [# Retrieve unique
      # pool IDs (TKPools) from pp table]
      TKPools <- unique(pp$POOLID)

      # Check if TKPools is not empty
      if (length(TKPools) > 0) {
# For each pool ID in TKPools, retrieve corresponding rows from pooldef table
        for (pool_id in TKPools) {
          pooldef_data <- pooldef[pooldef$POOLID == pool_id, ]

          # Create a temporary data frame if pooldef_data is not empty
          if (nrow(pooldef_data) > 0) {
            temp_df <- data.frame(PP_PoolID = pool_id,
                                  STUDYID = pooldef_data$STUDYID,
                                  USUBJID = pooldef_data$USUBJID,
                                  POOLID = pooldef_data$POOLID,
                                  stringsAsFactors = FALSE)

            # Append the temporary data frame to the results data frame
            tK_animals_df <- rbind(tK_animals_df, temp_df)
          }
        }
      } else {
        # Retrieve STUDYID for the current study
        current_study_id <- bw$STUDYID[1]

        # Add study to no_poolid_studies dataframe
        no_poolid_studies <- rbind(no_poolid_studies,
                                   data.frame(STUDYID = current_study_id,
                                              stringsAsFactors = FALSE))
      }

    } else {
      # Create a empty data frame named "tK_animals_df"
      tK_animals_df <- data.frame(PP_PoolID = character(),
                                  STUDYID = character(),
                                  USUBJID = character(),
                                  POOLID = character(),
                                  stringsAsFactors = FALSE)
    }


    # Subtract "TK_animals_df" data from "CompileData"
 cleaned_CompileData <- CompileData[
   !(CompileData$USUBJID %in% tK_animals_df$USUBJID),]

    # Step-3 (optional): terminal-sacrifice SETCDs via get_treatment_group
    if (isTRUE(terminal_setcds_only)) {
      study_key <- if (use_xpt) basename(xpt_dir) else studyid
      tg <- get_treatment_group(studies = studyid, db_path = path_db, xpt_dir = xpt_dir)
      terminal_setcds <- tg[[study_key]][["treatment_group"]]
      if (is.null(terminal_setcds)) terminal_setcds <- character(0)
      terminal_setcds <- as.character(terminal_setcds)
      if (length(terminal_setcds) == 0L) {
        warning("get_doses: treatment_group is empty; no subjects retained when terminal_setcds_only = TRUE.",
                call. = FALSE)
      }
      cleaned_CompileData <- cleaned_CompileData %>%
        dplyr::filter(as.character(SETCD) %in% terminal_setcds)
    }

    # tx table  filter by TXPARMCD
  cleaned_CompileData_filtered_tx <- tx %>%
    dplyr::filter(TXPARMCD == "TRTDOS")

    # Step 1:  Create a unified separator pattern
    clean_pattern <- ";|\\||-|/|:|,"

    # Split and expand the TXVAL column
  clean_tx_expanded <- cleaned_CompileData_filtered_tx %>%
    dplyr::mutate(
             is_split = stringr::str_detect(TXVAL,
                                            clean_pattern),
             TXVAL = strsplit(as.character(TXVAL),
                              clean_pattern)
           ) %>%
    tidyr::unnest(TXVAL) %>%
    dplyr::mutate(
             TXVAL = as.numeric(TXVAL)
           ) %>%
    dplyr::select(-is_split)

    # One row per (STUDYID, SETCD) with one dose value per arm; all arms kept for join
    dose_ranking <- clean_tx_expanded %>%
      dplyr::group_by(STUDYID, SETCD) %>%
      dplyr::summarise(TXVAL = min(TXVAL, na.rm = TRUE), .groups = "drop")
    dose_ranking$TXVAL[is.infinite(dose_ranking$TXVAL)] <- NA_real_

    # Assign vehicle / LD / MD / MD# / HD / Both from ordered distinct TXVAL
    DOSE_RANKED_selected_rows <- add_dose_ranking_column(dose_ranking)

    #Merging "DOSE_RANKED_selected_rows" and "cleaned_CompileData" data framed
    dose_rank_comp_data <- dplyr::inner_join(cleaned_CompileData,
                                             DOSE_RANKED_selected_rows,
                                             by = c("STUDYID", "SETCD"))

    # rename the Data frame
    master_CompileData1 <- dose_rank_comp_data [,c("STUDYID",
                                                   "USUBJID",
                                                   "Species",
                                                   "SEX",
                                                   "DOSE_RANKING",
                                                   "SETCD")]

    # Rename the "DOSE_RANKING" column to ARMCD
    # Rename "DOSE_RANKING" to "ARMCD" in master_CompileData
    master_CompileData <- master_CompileData1 %>%
      dplyr::rename(ARMCD = DOSE_RANKING)

  master_CompileData
}
