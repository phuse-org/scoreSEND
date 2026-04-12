#' Map sorted dose-level index to ARMCD-style tier label
#'
#' Distinct dose values per study are sorted ascending; \code{i} is the 1-based
#' index in that sorted vector. Rules: \code{n == 1} → \code{Both}; \code{n == 2}
#' → \code{vehicle}, \code{HD}; \code{n == 3} → \code{vehicle}, \code{LD},
#' \code{HD}; \code{n == 4} → \code{vehicle}, \code{LD}, \code{MD}, \code{HD};
#' \code{n >= 5} → \code{vehicle}, \code{LD}, \code{MD1} … \code{MD(n-3)},
#' \code{HD}.
#'
#' @param i Integer index (1 = lowest dose).
#' @param n Integer count of distinct non-NA dose values in the study.
#' @return Single character label.
#' @noRd
dose_tier_label_from_index <- function(i, n) {
  i <- as.integer(i)
  n <- as.integer(n)
  if (n == 1L) return("Both")
  if (i == 1L) return("vehicle")
  if (i == n) return("HD")
  if (n == 3L && i == 2L) return("LD")
  if (n == 4L) {
    if (i == 2L) return("LD")
    if (i == 3L) return("MD")
  }
  if (n >= 5L) {
    if (i == 2L) return("LD")
    if (i >= 3L && i < n) return(paste0("MD", i - 2L))
  }
  stop("Invalid dose tier index: i=", i, ", n=", n, call. = FALSE)
}

#' Numeric order for sorting rows by dose tier (vehicle, LD, MD, MD#, HD)
#'
#' Aligns with \code{dose_tier_label_from_index}. Unknown labels get rank 500;
#' \code{NA} sorts last (\code{Inf}).
#'
#' @param armcd Character vector of \code{ARMCD} values.
#' @return Numeric vector of the same length (larger = higher dose for known tiers).
#' @noRd
armcd_sort_key <- function(armcd) {
  if (length(armcd) == 0L) {
    return(numeric())
  }
  vapply(armcd, function(a) {
    if (length(a) != 1L || is.na(a)) {
      return(Inf)
    }
    a <- as.character(a)
    if (a == "vehicle") {
      return(1)
    }
    if (a == "Both") {
      return(1.5)
    }
    if (a == "LD") {
      return(2)
    }
    if (a == "MD") {
      return(3)
    }
    if (a == "HD") {
      return(1000)
    }
    if (grepl("^MD[0-9]+$", a)) {
      return(3 + as.numeric(sub("^MD", "", a)))
    }
    500
  }, numeric(1), USE.NAMES = FALSE)
}

#' Add DOSE_RANKING column from per-arm TXVAL
#'
#' One row per \code{(STUDYID, SETCD)} with numeric \code{TXVAL}. Rows with
#' \code{NA} \code{TXVAL} get \code{NA} in \code{DOSE_RANKING}. Studies with no
#' non-NA \code{TXVAL} get \code{NA} for all rows.
#'
#' @param dose_ranking Data frame with \code{STUDYID}, \code{SETCD}, \code{TXVAL}.
#' @return Same data frame with \code{DOSE_RANKING} column added.
#' @noRd
assign_dose_ranking_for_study_txval <- function(txval) {
  vals <- sort(unique(stats::na.omit(txval)))
  n <- length(vals)
  if (n == 0L) {
    return(rep(NA_character_, length(txval)))
  }
  idx <- match(txval, vals)
  vapply(seq_along(idx), function(k) {
    i <- idx[k]
    if (is.na(i)) return(NA_character_)
    dose_tier_label_from_index(i, n)
  }, character(1), USE.NAMES = FALSE)
}

#' @noRd
add_dose_ranking_column <- function(dose_ranking) {
  dose_ranking %>%
    dplyr::group_by(.data$STUDYID) %>%
    dplyr::mutate(DOSE_RANKING = assign_dose_ranking_for_study_txval(.data$TXVAL)) %>%
    dplyr::ungroup()
}
