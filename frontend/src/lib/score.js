// Compliance score (0–100) + letter grade from a scan result.
// Any undeclared tracker firing after "Reject All" is a violation, so a clean
// site scores 100 (A) and score drops sharply with each undeclared tracker.
const clamp = (n, lo, hi) => Math.max(lo, Math.min(hi, n))

export function scoreFromResult(data = {}) {
  const undeclared = (data.undeclared || []).length
  const needsReview = (data.needs_review || []).length
  const scan = data.scan || {}

  let score
  if (undeclared === 0) {
    score = needsReview > 0 ? 88 : 100
  } else {
    score = clamp(74 - (undeclared - 1) * 7 - needsReview * 2 - (scan.clicked_reject === false ? 8 : 0), 5, 74)
  }

  const grade =
    score >= 90 ? 'A' :
    score >= 80 ? 'B' :
    score >= 65 ? 'C' :
    score >= 50 ? 'D' : 'F'

  const label =
    undeclared === 0 ? 'Compliant' :
    score >= 65 ? 'At risk' : 'Serious violations'

  return { score, grade, label, undeclared }
}

export function gradeColor(grade) {
  if (grade === 'A' || grade === 'B') return 'var(--emerald)'
  if (grade === 'C') return 'var(--yellow)'
  return 'var(--rose)'
}
