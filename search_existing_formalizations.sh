#!/bin/bash

echo "=== SEARCHING FOR EXISTING FORMALIZATIONS ==="
echo ""
echo "1. Checking Mathlib for relevant theories..."
echo ""

# Search for Ruelle-Perron-Frobenius transfer operators
cd lean/.lake/packages/mathlib/Mathlib
echo "Searching for 'Transfer' or 'transfer' in Analysis..."
grep -r "def.transfer\|def Transfer\|class.*Transfer" Analysis/ 2>/dev/null | head -5

echo ""
echo "Searching for 'Ruelle' or 'Perron'..."
grep -r "Ruelle\|Perron" . 2>/dev/null | head -5

echo ""
echo "Searching for 'dynamical' or 'Dynamical'..."
grep -r "dynamical\|Dynamical" . 2>/dev/null | grep "\.lean:" | head -5

echo ""
echo "Searching for 'ergodic' or 'Ergodic'..."
grep -r "ergodic.*theory\|Ergodic.*Theory" . 2>/dev/null | grep "\.lean:" | head -5

echo ""
echo "2. Checking for continued fractions..."
grep -r "continued.*fraction\|Continued.*Fraction" NumberTheory/ 2>/dev/null | grep "\.lean:" | head -10

echo ""
echo "3. Checking for zeta function connections..."
grep -r "transfer.*zeta\|zeta.*transfer" NumberTheory/ 2>/dev/null | head -5

echo ""
echo "=== END OF MATHLIB SEARCH ==="
