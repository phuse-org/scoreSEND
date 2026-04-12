test_that("dose_tier_label_from_index matches LD / MD / MD# rules", {
  dti <- scoreSEND:::dose_tier_label_from_index
  expect_equal(dti(1L, 2L), "vehicle")
  expect_equal(dti(2L, 2L), "HD")
  expect_equal(dti(1L, 1L), "Both")
  expect_equal(dti(1L, 3L), "vehicle")
  expect_equal(dti(2L, 3L), "LD")
  expect_equal(dti(3L, 3L), "HD")
  expect_equal(dti(2L, 4L), "LD")
  expect_equal(dti(3L, 4L), "MD")
  expect_equal(dti(4L, 4L), "HD")
  expect_equal(dti(2L, 5L), "LD")
  expect_equal(dti(3L, 5L), "MD1")
  expect_equal(dti(4L, 5L), "MD2")
  expect_equal(dti(5L, 5L), "HD")
  expect_equal(dti(5L, 6L), "MD3")
})

test_that("add_dose_ranking_column assigns tiers from TXVAL", {
  d <- data.frame(
    STUDYID = "S1",
    SETCD = c("a", "b", "c", "d"),
    TXVAL = c(0, 1, 5, 10),
    stringsAsFactors = FALSE
  )
  out <- scoreSEND:::add_dose_ranking_column(d)
  expect_equal(
    out$DOSE_RANKING,
    c("vehicle", "LD", "MD", "HD")
  )

  d5 <- data.frame(
    STUDYID = "S1",
    SETCD = letters[1:5],
    TXVAL = c(0, 1, 2, 3, 100),
    stringsAsFactors = FALSE
  )
  out5 <- scoreSEND:::add_dose_ranking_column(d5)
  expect_equal(
    out5$DOSE_RANKING,
    c("vehicle", "LD", "MD1", "MD2", "HD")
  )

  dna <- data.frame(
    STUDYID = "S1",
    SETCD = c("a", "b"),
    TXVAL = c(1, NA),
    stringsAsFactors = FALSE
  )
  outna <- scoreSEND:::add_dose_ranking_column(dna)
  # Single distinct non-NA dose => Both; NA TXVAL stays NA
  expect_equal(outna$DOSE_RANKING, c("Both", NA))

  d2 <- data.frame(
    STUDYID = "S1",
    SETCD = c("a", "b", "c"),
    TXVAL = c(0, 10, NA),
    stringsAsFactors = FALSE
  )
  out2 <- scoreSEND:::add_dose_ranking_column(d2)
  expect_equal(out2$DOSE_RANKING, c("vehicle", "HD", NA))
})

test_that("armcd_sort_key orders dose tiers for sorting", {
  ask <- scoreSEND:::armcd_sort_key
  labs <- c("vehicle", "Both", "LD", "MD", "MD1", "MD2", "HD")
  keys <- ask(labs)
  expect_true(all(diff(keys[1:7]) > 0))
  expect_equal(ask(NA_character_), Inf)
  expect_equal(ask(c("vehicle", "HD")), c(1, 1000))
  expect_true(ask("MD") < ask("MD1"))
  expect_true(ask("MD1") < ask("MD2"))
})
