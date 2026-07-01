-- booktabs.lua: Lua filter to improve pandoc table appearance
-- Applied as: --lua-filter=paper/booktabs.lua
--
-- Pandoc 3.x already generates \toprule/\midrule/\bottomrule (booktabs).
-- This filter adds:
--   - \small font for compact tables
--   - Tighter column spacing (\tabcolsep=3pt)
--   - Tighter row spacing (\arraystretch=1.08)
--   - Longtable centering via \LTleft=\fill\LTright=\fill
--
-- The actual alternating row colors (\rowcolor, \rowcolors) are added
-- by scripts/fix_tables.py during the two-pass build.

function Table(tbl)
  local before = pandoc.RawBlock('latex',
    '{\\small\\setlength{\\tabcolsep}{3pt}%\n' ..
    '\\renewcommand{\\arraystretch}{1.08}%\n' ..
    '\\LTleft=\\fill\\LTright=\\fill')
  local after = pandoc.RawBlock('latex', '}')
  return { before, tbl, after }
end
