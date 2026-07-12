export default function Problem() {
  return (
    <section className="section" id="problem">
      <div className="problem-inner">
        <div>
          <span className="section-label">The problem</span>
          <h2 className="h2">
            Most cookie banners exist to <em>look</em> compliant, not to <em>be</em>.
          </h2>
          <p className="problem-body" style={{ marginTop: '1.75rem' }}>
            Under Article 7, consent must be <u>freely given and unambiguous.</u> Firing trackers
            after “Reject All” breaks that.
          </p>
          <p className="problem-body" style={{ marginTop: '1rem' }}>
            It’s a direct violation — up to <span className="rose">4% of global turnover</span> under
            Article 83.
          </p>
        </div>

        <div className="problem-aside">
          <div className="pa-row"><span className="pa-k">Legal basis</span><span className="pa-v">Article 7</span></div>
          <div className="pa-row"><span className="pa-k">Max penalty · Art. 83</span><span className="pa-v rose">4% turnover</span></div>
          <div className="pa-row"><span className="pa-k">Also governed by</span><span className="pa-v">ePrivacy 2002/58</span></div>
          <div className="pa-row"><span className="pa-k">“Reject All” means</span><span className="pa-v">Zero trackers</span></div>
        </div>
      </div>
    </section>
  )
}
