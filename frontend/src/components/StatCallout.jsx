export default function StatCallout() {
  return (
    <section className="stat-callout">
      <div className="stat-callout-inner">
        <div className="stat-big">73%</div>
        <div className="stat-caption">of sites still fire tracking requests after a user clicks “Reject All.”</div>
        <p className="stat-sub">
          The banner records consent as refused — then loads Meta, Microsoft and analytics trackers anyway.
          It’s the single most-cited cookie violation under GDPR, and almost no one is checking for it.
        </p>
      </div>
    </section>
  )
}
